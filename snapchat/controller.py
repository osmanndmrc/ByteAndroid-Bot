"""
Snapchat Controller module exposing clean high-level methods for automation workflows.
"""

import time
from typing import List, Optional, Dict, Any
from loguru import logger
import uiautomator2 as u2

from config.config_loader import SnapchatConfig
from adb.adb_manager import ADBManager
from snapchat.camera_handler import CameraHandler
from snapchat.ui_selectors import SnapchatSelectors
from utils.screenshot import ScreenshotManager
from core.exceptions import (
    SnapchatError,
    SnapchatLaunchError,
    SnapchatRecipientError,
    SnapchatSendError,
    SnapchatVerificationError,
    ElementNotFoundError,
)


class SnapchatController:
    """High-level automation controller for Snapchat operations."""

    def __init__(self, adb_manager: ADBManager, config: SnapchatConfig, screenshot_manager: Optional[ScreenshotManager] = None):
        self.adb = adb_manager
        self.config = config
        self.screenshot_mgr = screenshot_manager
        self.camera_handler = CameraHandler(adb_manager, timeout_seconds=config.element_timeout_seconds)

    def _find_element(self, selectors: List[Dict[str, Any]], timeout: float = 5.0) -> Any:
        """Finds UI element using multi-strategy selectors."""
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
        raise ElementNotFoundError(f"Selectors not found: {selectors}")

    def open(self) -> None:
        """Launches Snapchat app and waits for initial screen readiness."""
        logger.info("Opening Snapchat application...")
        try:
            self.adb.force_stop_app(self.config.package_name)
            time.sleep(1)
            self.adb.start_app(self.config.package_name, self.config.activity_name)

            # Wait for camera or main landing screen readiness
            start = time.time()
            ready = False
            while time.time() - start < self.config.launch_timeout_seconds:
                if self.camera_handler.is_camera_ready():
                    ready = True
                    break
                time.sleep(1)

            if not ready:
                logger.warning("Snapchat launch timeout reached. Attempting to ensure camera focus...")
                self.go_to_camera()

            logger.success("Snapchat launched successfully.")
        except Exception as e:
            if self.screenshot_mgr:
                self.screenshot_mgr.capture("launch_failed")
            raise SnapchatLaunchError("Failed to launch Snapchat app", original_exception=e)

    def health_check(self) -> bool:
        """Verifies if Snapchat is alive, installed, and in a valid responsive state."""
        logger.info("Performing Snapchat health check...")
        try:
            output = self.adb.run_shell(f"pidof {self.config.package_name}")
            if not output.strip():
                logger.warning("Snapchat process PID not found.")
                return False

            u2_dev = self.adb.get_u2_device()
            current_app = u2_dev.app_current()
            if current_app.get("package") != self.config.package_name:
                logger.warning(f"Active app package is {current_app.get('package')}, expected {self.config.package_name}")
                return False

            return True
        except Exception as e:
            logger.error(f"Snapchat health check failed: {e}")
            return False

    def go_to_camera(self) -> None:
        """Navigates back to the main camera view if currently in sub-screens."""
        logger.info("Navigating to camera tab view...")
        try:
            u2_dev = self.adb.get_u2_device()
            # Press Back key 2-3 times if on sub-screens
            for _ in range(3):
                if self.camera_handler.is_camera_ready():
                    return
                u2_dev.press("back")
                time.sleep(0.8)

            # Try clicking camera tab selector
            try:
                cam_tab = self._find_element(SnapchatSelectors.CAMERA_TAB, timeout=2.0)
                cam_tab.click()
            except ElementNotFoundError:
                pass
        except Exception as e:
            logger.warning(f"Error navigating to camera view: {e}")

    def take_black_photo(self) -> None:
        """Takes photo using camera handler."""
        self.camera_handler.take_black_photo()

    def press_next(self) -> None:
        """Presses Next / Send-To button after photo capture."""
        logger.info("Pressing Next / Send-To button...")
        try:
            elem = self._find_element(SnapchatSelectors.NEXT_BUTTON, timeout=self.config.element_timeout_seconds)
            elem.click()
            logger.success("Next button pressed.")
            time.sleep(1.5)
        except ElementNotFoundError:
            logger.warning("Next button selector not found. Using fallback coordinates...")
            u2_dev = self.adb.get_u2_device()
            w, h = u2_dev.window_size()
            # Next button is typically bottom-right on post-capture preview
            u2_dev.click(int(w * 0.88), int(h * 0.92))
            time.sleep(1.5)
        except Exception as e:
            if self.screenshot_mgr:
                self.screenshot_mgr.capture("press_next_failed")
            raise SnapchatSendError("Failed to press Next button after capture", original_exception=e)

    def select_recipients(self, recipients: List[str]) -> None:
        """Selects target recipients in send-to screen."""
        logger.info(f"Selecting recipients: {recipients}")
        if not recipients:
            raise SnapchatRecipientError("Recipients list is empty.")

        u2_dev = self.adb.get_u2_device()
        selected_count = 0

        for recipient in recipients:
            try:
                # Try finding recipient directly on screen
                elem = u2_dev(text=recipient)
                if not elem.exists:
                    elem = u2_dev(description=recipient)

                if elem.exists:
                    elem.click()
                    selected_count += 1
                    logger.info(f"Selected recipient directly: {recipient}")
                    time.sleep(0.5)
                else:
                    # Search for recipient using search input
                    logger.info(f"Searching for recipient: {recipient}")
                    search_input = self._find_element(SnapchatSelectors.SEARCH_INPUT, timeout=3.0)
                    search_input.click()
                    time.sleep(0.5)
                    u2_dev.send_keys(recipient)
                    time.sleep(1.5)

                    # Click matching search result item
                    res_elem = u2_dev(text=recipient)
                    if not res_elem.exists:
                        res_elem = u2_dev(textContains=recipient)

                    if res_elem.exists:
                        res_elem.click()
                        selected_count += 1
                        logger.info(f"Selected recipient from search results: {recipient}")
                        time.sleep(0.5)
                    else:
                        logger.warning(f"Could not find recipient in search results: {recipient}")
            except Exception as e:
                logger.error(f"Error selecting recipient '{recipient}': {e}")

        if selected_count == 0:
            if self.screenshot_mgr:
                self.screenshot_mgr.capture("recipient_selection_failed")
            raise SnapchatRecipientError(f"Failed to select any recipients from list: {recipients}")

    def send(self) -> None:
        """Presses final Send delivery button."""
        logger.info("Executing final snap delivery send...")
        try:
            send_btn = self._find_element(SnapchatSelectors.FINAL_SEND_BUTTON, timeout=self.config.element_timeout_seconds)
            send_btn.click()
            logger.success("Final send button clicked.")
            time.sleep(2)
        except ElementNotFoundError:
            logger.warning("Final send button selector not found. Attempting bottom-right tap fallback...")
            u2_dev = self.adb.get_u2_device()
            w, h = u2_dev.window_size()
            u2_dev.click(int(w * 0.90), int(h * 0.95))
            time.sleep(2)
        except Exception as e:
            if self.screenshot_mgr:
                self.screenshot_mgr.capture("send_failed")
            raise SnapchatSendError("Failed to trigger final send button", original_exception=e)

    def verify_send(self) -> bool:
        """Verifies snap send succeeded by checking return to main screen or confirmation toast."""
        logger.info("Verifying snap send delivery status...")
        try:
            start = time.time()
            while time.time() - start < 10:
                # If we returned to camera view or camera shutter is present, send succeeded
                if self.camera_handler.is_camera_ready():
                    logger.success("Send verified: Returned to camera view.")
                    return True
                time.sleep(1)

            # Fallback: check if send button is gone
            u2_dev = self.adb.get_u2_device()
            if not u2_dev(resourceId="com.snapchat.android:id/send_to_bottom_panel_button").exists:
                logger.success("Send verified: Send panel closed.")
                return True

            logger.warning("Verification incomplete: Screen state ambiguous.")
            return False
        except Exception as e:
            raise SnapchatVerificationError("Error during snap send verification", original_exception=e)

    def recover(self) -> None:
        """Performs inside-app reset recovery."""
        logger.warning("Performing Snapchat in-app recovery...")
        try:
            self.go_to_camera()
            self.adb.force_stop_app(self.config.package_name)
            time.sleep(2)
            self.open()
        except Exception as e:
            logger.error(f"In-app recovery failed: {e}")

    def close(self) -> None:
        """Closes Snapchat app."""
        logger.info("Closing Snapchat application...")
        self.adb.force_stop_app(self.config.package_name)
