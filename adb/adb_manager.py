"""
ADB Manager for ReDroid Android container communication and uiautomator2 integration.
"""

import subprocess
import time
from typing import Optional, List
from loguru import logger
import uiautomator2 as u2

from config.config_loader import ADBConfig
from core.exceptions import (
    ADBConnectionError,
    ADBCommandError,
    ADBTimeoutError,
    ADBError,
)


class ADBManager:
    """Manages low-level ADB connections, command execution, and uiautomator2 bindings."""

    def __init__(self, config: ADBConfig):
        self.config = config
        self.target = f"{self.config.host}:{self.config.port}"
        self._u2_device: Optional[u2.Device] = None

    def connect(self) -> bool:
        """Connects ADB client to the ReDroid instance."""
        logger.info(f"Connecting to ADB target: {self.target}")
        try:
            output = self.run_global_cmd(["connect", self.target], timeout=self.config.connect_timeout_seconds)
            if "connected to" in output.lower() or "already connected" in output.lower():
                logger.success(f"Successfully connected to ADB target: {self.target}")
                return True
            else:
                logger.warning(f"ADB connect returned unexpected response: {output}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to ADB target {self.target}: {e}")
            raise ADBConnectionError(f"Could not connect to {self.target}", original_exception=e)

    def disconnect(self) -> None:
        """Disconnects ADB target."""
        logger.info(f"Disconnecting ADB target: {self.target}")
        try:
            self.run_global_cmd(["disconnect", self.target], timeout=10)
        except Exception as e:
            logger.warning(f"Ignored error during ADB disconnect: {e}")
        finally:
            self._u2_device = None

    def restart_adb_server(self) -> bool:
        """Kills and restarts local ADB server daemon."""
        logger.warning("Restarting ADB server daemon...")
        try:
            self.disconnect()
            self.run_global_cmd(["kill-server"], timeout=10)
            time.sleep(2)
            self.run_global_cmd(["start-server"], timeout=10)
            time.sleep(2)
            return self.connect()
        except Exception as e:
            logger.error(f"Failed to restart ADB server: {e}")
            raise ADBConnectionError("Failed to restart ADB server", original_exception=e)

    def run_global_cmd(self, args: List[str], timeout: Optional[int] = None) -> str:
        """Runs a global ADB command (without -s flag)."""
        cmd = ["adb"] + args
        return self._execute(cmd, timeout or self.config.command_timeout_seconds)

    def run_cmd(self, args: List[str], timeout: Optional[int] = None) -> str:
        """Runs an ADB command targeted at the current device."""
        cmd = ["adb", "-s", self.target] + args
        return self._execute(cmd, timeout or self.config.command_timeout_seconds)

    def run_shell(self, command: str, timeout: Optional[int] = None) -> str:
        """Runs an ADB shell command on the target device."""
        return self.run_cmd(["shell", command], timeout=timeout)

    def _execute(self, cmd: List[str], timeout: int) -> str:
        """Executes a subprocess command safely with timeout handling."""
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                check=False,
            )
            if result.returncode != 0:
                err_msg = result.stderr.strip() or result.stdout.strip()
                raise ADBCommandError(f"Command {' '.join(cmd)} failed (code {result.returncode}): {err_msg}")
            return result.stdout.strip()
        except subprocess.TimeoutExpired as e:
            raise ADBTimeoutError(f"Command {' '.join(cmd)} timed out after {timeout}s", original_exception=e)
        except Exception as e:
            if isinstance(e, ADBError):
                raise
            raise ADBCommandError(f"Execution error for {' '.join(cmd)}", original_exception=e)

    def is_device_connected(self) -> bool:
        """Checks if device is listed as 'device' in `adb devices`."""
        try:
            output = self.run_global_cmd(["devices"])
            for line in output.splitlines():
                if self.target in line and "device" in line and "offline" not in line:
                    return True
            return False
        except Exception:
            return False

    def is_android_booted(self) -> bool:
        """Checks sys.boot_completed property via ADB shell."""
        try:
            output = self.run_shell("getprop sys.boot_completed")
            return output.strip() == "1"
        except Exception:
            return False

    def start_app(self, package_name: str, activity_name: Optional[str] = None) -> None:
        """Starts an Android app via intent package/activity or monkey fallback."""
        logger.info(f"Starting app package: {package_name}")
        if activity_name:
            target = f"{package_name}/{activity_name}"
            self.run_shell(f"am start -n {target}")
        else:
            self.run_shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")

    def force_stop_app(self, package_name: str) -> None:
        """Force stops an Android app package."""
        logger.info(f"Force stopping package: {package_name}")
        self.run_shell(f"am force-stop {package_name}")

    def install_apk(self, apk_path: str) -> None:
        """Installs an APK on the target device."""
        logger.info(f"Installing APK from path: {apk_path}")
        self.run_cmd(["install", "-r", apk_path])

    def get_u2_device(self, force_reconnect: bool = False) -> u2.Device:
        """Returns or initializes uiautomator2 Device instance."""
        if self._u2_device is None or force_reconnect:
            if not self.is_device_connected():
                self.connect()
            logger.info(f"Initializing uiautomator2 connection to: {self.target}")
            try:
                self._u2_device = u2.connect(self.target)
                # Set default click post delay to avoid racing clicks
                self._u2_device.click_post_delay = 0.5
            except Exception as e:
                logger.error(f"Failed to connect uiautomator2: {e}")
                raise ADBConnectionError("uiautomator2 connection failed", original_exception=e)
        return self._u2_device
