"""
Main SnapBot Application Orchestrator and Lifecycle Manager.
"""

import time
import signal
from pathlib import Path
from typing import Optional
from loguru import logger

from config.config_loader import ConfigLoader, AppConfig
from utils.logger import setup_logger
from utils.screenshot import ScreenshotManager
from database.db import DatabaseManager
from database.repository import BotRepository
from adb.adb_manager import ADBManager
from core.device_manager import DeviceManager
from snapchat.controller import SnapchatController
from watchdog.recovery import RecoveryManager
from watchdog.watchdog import WatchdogEngine
from scheduler.tasks import SnapTaskExecutor
from scheduler.job_scheduler import JobScheduler


class SnapBot:
    """Main application orchestrator tying together ADB, Device, Snapchat, Watchdog, Database, and Scheduler."""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config: AppConfig = ConfigLoader.load(config_path)
        setup_logger(self.config.logging)

        logger.info("Initializing SnapBot Automation System...")

        # Initialize persistence & repository
        self.db_manager = DatabaseManager(self.config.database)
        self.repository = BotRepository(self.db_manager)

        # Initialize ADB & Device layer
        self.adb_manager = ADBManager(self.config.adb)
        self.device_manager = DeviceManager(self.adb_manager)
        self.screenshot_manager = ScreenshotManager(self.adb_manager, self.config.screenshot)

        # Initialize Snapchat controller & Watchdog
        self.snapchat_controller = SnapchatController(
            self.adb_manager, self.config.snapchat, self.screenshot_manager
        )
        self.recovery_manager = RecoveryManager(
            self.config, self.adb_manager, self.device_manager, self.repository
        )
        self.watchdog_engine = WatchdogEngine(
            self.config,
            self.adb_manager,
            self.device_manager,
            self.snapchat_controller,
            self.recovery_manager,
            self.db_manager,
        )

        # Initialize Scheduler & Task Executor
        self.task_executor = SnapTaskExecutor(
            self.config,
            self.snapchat_controller,
            self.device_manager,
            self.watchdog_engine,
            self.repository,
            self.screenshot_manager,
        )
        self.job_scheduler = JobScheduler(self.config, self.task_executor)

        self._running = False

    def start(self) -> None:
        """Starts the main SnapBot daemon loop."""
        logger.info("Starting SnapBot service...")
        self._running = True

        # Perform initial ADB connection
        try:
            self.adb_manager.connect()
        except Exception as e:
            logger.warning(f"Initial ADB connection failed: {e}. Triggering watchdog recovery...")
            self.watchdog_engine.run_diagnostics_and_recover()

        # Start job scheduler
        self.job_scheduler.start()

        logger.success("SnapBot running in background. Monitoring schedule...")

    def trigger_immediate_run(self) -> bool:
        """Triggers an immediate manual snap workflow execution."""
        logger.info("Triggering immediate manual Snap workflow run...")
        return self.task_executor.run_snap_workflow()

    def run_forever(self) -> None:
        """Blocks main thread and keeps application alive."""
        self.start()
        try:
            while self._running:
                # Periodic watchdog check every check_interval_seconds
                time.sleep(self.config.watchdog.check_interval_seconds)
                self.watchdog_engine.run_diagnostics_and_recover()
                self.screenshot_manager.cleanup_old_screenshots()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Termination signal received.")
        finally:
            self.stop()

    def stop(self) -> None:
        """Gracefully stops SnapBot background services."""
        logger.info("Stopping SnapBot service...")
        self._running = False
        self.job_scheduler.shutdown()
        self.adb_manager.disconnect()
        logger.success("SnapBot service stopped gracefully.")
