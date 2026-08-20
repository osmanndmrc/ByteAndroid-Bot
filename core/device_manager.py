"""
Device Manager module for managing screen state, boot status, and OS responsiveness.
"""

import time
from typing import TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from adb.adb_manager import ADBManager

from core.exceptions import DeviceBootError, DeviceFreezeError, DeviceError


class DeviceManager:
    """Manages low-level Android device lifecycle, screen power state, and freeze detection."""

    def __init__(self, adb_manager: "ADBManager"):
        self.adb = adb_manager

    def wait_for_boot(self, timeout_seconds: int = 120, poll_interval: int = 5) -> bool:
        """Blocks until Android OS finishes boot sequence."""
        logger.info("Waiting for Android OS boot completion...")
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            if self.adb.is_device_connected() and self.adb.is_android_booted():
                logger.success("Android OS boot completed.")
                return True
            time.sleep(poll_interval)

        raise DeviceBootError(f"Android device failed to boot within {timeout_seconds} seconds.")

    def is_screen_on(self) -> bool:
        """Checks if screen display is turned on."""
        try:
            output = self.adb.run_shell("dumpsys power")
            if "mHoldingDisplaySuspendBlocker=true" in output or "Display Power: state=ON" in output:
                return True
            output_display = self.adb.run_shell("dumpsys display")
            return "mScreenState=ON" in output_display or "state=ON" in output_display
        except Exception as e:
            logger.warning(f"Error checking screen state: {e}")
            return False

    def wake_screen(self) -> None:
        """Wakes device screen if turned off."""
        logger.info("Waking device screen...")
        try:
            if not self.is_screen_on():
                # Send KEYEVENT_WAKEUP (224) or KEYEVENT_POWER (26)
                self.adb.run_shell("input keyevent 224")
                time.sleep(1)
                if not self.is_screen_on():
                    self.adb.run_shell("input keyevent 26")
                    time.sleep(1)
            logger.info("Screen is awake.")
        except Exception as e:
            raise DeviceError("Failed to wake device screen", original_exception=e)

    def unlock_screen(self) -> None:
        """Unlocks screen keyguard if locked."""
        logger.info("Unlocking screen keyguard...")
        try:
            self.wake_screen()
            # Send KEYEVENT_MENU (82) or swipe up
            self.adb.run_shell("input keyevent 82")
            time.sleep(0.5)
            # Swipe up from bottom center to top center as fallback for lock screens
            self.adb.run_shell("input swipe 500 1500 500 500 300")
            time.sleep(1)
        except Exception as e:
            raise DeviceError("Failed to unlock screen", original_exception=e)

    def keep_screen_awake(self) -> None:
        """Configures system settings to prevent screen timeout while plugged in."""
        logger.info("Setting system configuration to keep screen awake...")
        try:
            # 7 = BATTERY_PLUGGED_AC | BATTERY_PLUGGED_USB | BATTERY_PLUGGED_WIRELESS
            self.adb.run_shell("settings put global stay_on_while_plugged_in 7")
        except Exception as e:
            logger.warning(f"Failed to set stay_on_while_plugged_in setting: {e}")

    def detect_freeze(self, timeout_seconds: int = 10) -> bool:
        """Detects if Android UI layer is frozen by attempting a UI hierarchy dump."""
        try:
            u2_dev = self.adb.get_u2_device()
            # Requesting hierarchy with strict internal timeout
            start_time = time.time()
            xml = u2_dev.dump_hierarchy()
            duration = time.time() - start_time
            if not xml or duration > timeout_seconds:
                logger.warning(f"UI dump returned in {duration:.2f}s (timeout was {timeout_seconds}s)")
                return True
            return False
        except Exception as e:
            logger.error(f"UI freeze detected during hierarchy dump: {e}")
            return True
