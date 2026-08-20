"""
Multi-tier Recovery Escalation Matrix module for self-healing operations.
"""

import subprocess
import time
from typing import Optional
from loguru import logger
import docker

from config.config_loader import AppConfig
from adb.adb_manager import ADBManager
from core.device_manager import DeviceManager
from database.repository import BotRepository
from database.models import RestartRecord
from core.exceptions import RecoveryEscalationMaxedError


class RecoveryManager:
    """Handles multi-level recovery escalations (Tiers 1-5) when components or health checks fail."""

    def __init__(self, config: AppConfig, adb_manager: ADBManager, device_manager: DeviceManager, repository: BotRepository):
        self.config = config
        self.adb = adb_manager
        self.device = device_manager
        self.repo = repository

    def recover(self, target_tier: int, reason: str) -> bool:
        """Executes recovery action for the specified tier level (1 to 5)."""
        max_allowed_tier = self.config.watchdog.max_tier
        if target_tier > max_allowed_tier:
            msg = f"Requested recovery tier {target_tier} exceeds maximum configured tier {max_allowed_tier}."
            logger.error(msg)
            raise RecoveryEscalationMaxedError(msg)

        logger.warning(f"--- INITIATING RECOVERY TIER {target_tier} (Reason: {reason}) ---")
        record = RestartRecord(tier_level=target_tier, reason=reason)
        restart_id = self.repo.record_restart(record)

        success = False
        try:
            if target_tier == 1:
                success = self._tier1_restart_snapchat()
            elif target_tier == 2:
                success = self._tier2_reconnect_adb()
            elif target_tier == 3:
                success = self._tier3_restart_redroid_container()
            elif target_tier == 4:
                success = self._tier4_restart_docker_service()
            elif target_tier == 5:
                success = self._tier5_reboot_host()
            else:
                logger.error(f"Unknown recovery tier requested: {target_tier}")

            self.repo.update_restart_status(restart_id, success)
            if success:
                logger.success(f"--- RECOVERY TIER {target_tier} SUCCEEDED ---")
            else:
                logger.error(f"--- RECOVERY TIER {target_tier} FAILED ---")
            return success
        except Exception as e:
            logger.error(f"Exception during Tier {target_tier} recovery execution: {e}")
            self.repo.update_restart_status(restart_id, False)
            return False

    def _tier1_restart_snapchat(self) -> bool:
        """Tier 1: Force stop Snapchat app and relaunch."""
        logger.info("Executing Tier 1 Recovery: Force stopping Snapchat and waking screen...")
        try:
            self.adb.force_stop_app(self.config.snapchat.package_name)
            time.sleep(2)
            self.device.wake_screen()
            self.device.unlock_screen()
            self.adb.start_app(self.config.snapchat.package_name, self.config.snapchat.activity_name)
            time.sleep(5)
            return True
        except Exception as e:
            logger.error(f"Tier 1 recovery failed: {e}")
            return False

    def _tier2_reconnect_adb(self) -> bool:
        """Tier 2: Reset ADB server and reconnect."""
        logger.info("Executing Tier 2 Recovery: Resetting ADB server daemon and reconnecting...")
        try:
            connected = self.adb.restart_adb_server()
            if connected:
                self.device.wait_for_boot(timeout_seconds=30)
                self.device.wake_screen()
                self.device.unlock_screen()
                return True
            return False
        except Exception as e:
            logger.error(f"Tier 2 recovery failed: {e}")
            return False

    def _tier3_restart_redroid_container(self) -> bool:
        """Tier 3: Restart ReDroid Docker container."""
        container_name = self.config.redroid.container_name
        logger.info(f"Executing Tier 3 Recovery: Restarting Docker container '{container_name}'...")
        try:
            client = docker.DockerClient(base_url=self.config.redroid.docker_socket)
            container = client.containers.get(container_name)
            container.restart(timeout=15)
            logger.info("Container restart command issued. Waiting for boot...")
            time.sleep(10)
            self.adb.connect()
            return self.device.wait_for_boot(timeout_seconds=90)
        except Exception as e:
            logger.warning(f"Docker SDK restart failed: {e}. Trying CLI fallback...")
            try:
                res = subprocess.run(["docker", "restart", container_name], capture_output=True, text=True, timeout=30)
                if res.returncode == 0:
                    time.sleep(10)
                    self.adb.connect()
                    return self.device.wait_for_boot(timeout_seconds=90)
            except Exception as ex:
                logger.error(f"CLI fallback Docker restart failed: {ex}")
            return False

    def _tier4_restart_docker_service(self) -> bool:
        """Tier 4: Restart Docker service engine on Linux host."""
        service_name = self.config.redroid.docker_service_name
        logger.info(f"Executing Tier 4 Recovery: Restarting Docker engine service '{service_name}'...")
        try:
            res = subprocess.run(["sudo", "systemctl", "restart", service_name], capture_output=True, text=True, timeout=45)
            if res.returncode == 0:
                time.sleep(15)
                # After docker daemon restarts, restart container if needed
                return self._tier3_restart_redroid_container()
            logger.error(f"systemctl restart docker failed: {res.stderr}")
            return False
        except Exception as e:
            logger.error(f"Tier 4 recovery failed: {e}")
            return False

    def _tier5_reboot_host(self) -> bool:
        """Tier 5: Last resort host OS reboot."""
        if not self.config.watchdog.enable_host_reboot:
            logger.error("Tier 5 Host Reboot requested but 'enable_host_reboot' is disabled in config.")
            return False

        logger.critical("--- EXECUTING TIER 5 LAST RESORT REBOOT: REBOOTING LINUX HOST ---")
        try:
            subprocess.run(["sudo", "shutdown", "-r", "now"], check=False)
            return True
        except Exception as e:
            logger.critical(f"Tier 5 host reboot command failed: {e}")
            return False
