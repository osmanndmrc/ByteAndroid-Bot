"""
Watchdog Engine for continuous background health monitoring and escalation triggers.
"""

import time
from typing import Tuple
from loguru import logger

from config.config_loader import AppConfig
from adb.adb_manager import ADBManager
from core.device_manager import DeviceManager
from snapchat.controller import SnapchatController
from watchdog.recovery import RecoveryManager
from database.db import DatabaseManager


class WatchdogEngine:
    """Monitors system health continuously and executes self-healing escalation on failure."""

    def __init__(
        self,
        config: AppConfig,
        adb_manager: ADBManager,
        device_manager: DeviceManager,
        snapchat_controller: SnapchatController,
        recovery_manager: RecoveryManager,
        db_manager: DatabaseManager,
    ):
        self.config = config
        self.adb = adb_manager
        self.device = device_manager
        self.snapchat = snapchat_controller
        self.recovery = recovery_manager
        self.db = db_manager

    def check_health(self) -> Tuple[bool, str, int]:
        """
        Runs comprehensive health checks across all layers.
        Returns: (is_healthy, failure_reason, recommended_recovery_tier)
        """
        # 1. Database accessibility check
        try:
            with self.db.get_connection() as conn:
                conn.execute("SELECT 1")
        except Exception as e:
            return False, f"Database inaccessible: {e}", 1

        # 2. ADB connection check
        if not self.adb.is_device_connected():
            return False, "ADB device disconnected or offline", 2

        # 3. Android OS boot check
        if not self.adb.is_android_booted():
            return False, "Android OS boot incomplete or crashed", 2

        # 4. Device UI freeze check
        if self.device.detect_freeze(timeout_seconds=5):
            return False, "Android UI system freeze detected", 3

        # 5. Snapchat process & activity check
        if not self.snapchat.health_check():
            return False, "Snapchat application process dead or unhealthy", 1

        return True, "All systems healthy", 0

    def run_diagnostics_and_recover(self) -> bool:
        """Evaluates health and attempts escalating recovery tiers until healthy or max tier reached."""
        is_healthy, reason, suggested_tier = self.check_health()
        if is_healthy:
            return True

        logger.warning(f"Watchdog health check failed: {reason}")
        current_tier = suggested_tier
        max_tier = self.config.watchdog.max_tier

        while current_tier <= max_tier:
            recovered = self.recovery.recover(current_tier, reason=f"Watchdog: {reason}")
            if recovered:
                time.sleep(3)
                healthy, new_reason, _ = self.check_health()
                if healthy:
                    logger.success(f"System fully recovered at Tier {current_tier}.")
                    return True
            current_tier += 1

        logger.critical("Watchdog exhausted all recovery tiers without restoring health!")
        return False
