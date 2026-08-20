"""
Camera Handler module for Snapchat shutter operations and black photo capture.
"""

import time
from typing import List, Dict, Any
from loguru import logger
import uiautomator2 as u2
from adb.adb_manager import ADBManager
from snapchat.ui_selectors import SnapchatSelectors
from core.exceptions import SnapchatCameraError, ElementNotFoundError


class CameraHandler:
    """Manages Snapchat camera shutter interactions and frame validation."""

    def __init__(self, adb_manager: ADBManager, timeout_seconds: int = 10):
        self.adb = adb_manager
        self.timeout_seconds = timeout_seconds

    def _find_element(self, selectors: List[Dict[str, Any]], timeout: float = 5.0) -> Any:
        """Finds element using list of fallback selector strategies."""
        u2_dev = self.adb.get_u2_device()
        start = time.time()
        while time.time() - start < timeout:
            for selector in selectors:
                try:
                    elem = u2_dev(**selector)
                    if elem.exists:
                        return elem
                except Exception:
                    continue
            time.sleep(0.5)
        raise ElementNotFoundError(f"None of the selectors were found: {selectors}")

    def is_camera_ready(self) -> bool:
        """Verifies if Snapchat camera view and shutter button are active."""
        try:
            elem = self._find_element(SnapchatSelectors.CAMERA_SHUTTER, timeout=3.0)
            return elem is not None and elem.exists
        except Exception:
            return False

    def take_black_photo(self) -> None:
        """Takes a photo on Snapchat camera screen."""
        logger.info("Executing snap photo capture...")
        try:
            shutter = self._find_element(SnapchatSelectors.CAMERA_SHUTTER, timeout=self.timeout_seconds)
            shutter.click()
            logger.success("Shutter button clicked successfully.")
            time.sleep(2)  # Wait for post-capture preview transition
        except ElementNotFoundError as e:
            logger.warning("Shutter element not found via selectors. Attempting screen-center tap fallback...")
            # Fallback coordinate click for camera shutter if selector fails in ReDroid display
            u2_dev = self.adb.get_u2_device()
            width, height = u2_dev.window_size()
            # Shutter is usually bottom-center
            shutter_x = int(width * 0.5)
            shutter_y = int(height * 0.85)
            u2_dev.click(shutter_x, shutter_y)
            time.sleep(2)
        except Exception as e:
            raise SnapchatCameraError("Failed to capture photo on Snapchat camera view", original_exception=e)
