"""
Task definitions and execution workflow wrapper for Snapchat daily snap job.
"""

import traceback
from datetime import datetime
from typing import List, Optional
from loguru import logger

from config.config_loader import AppConfig
from snapchat.controller import SnapchatController
from core.device_manager import DeviceManager
from watchdog.watchdog import WatchdogEngine
from database.repository import BotRepository
from database.models import ExecutionRecord, ErrorRecord
from utils.metrics import ExecutionTimer
from utils.screenshot import ScreenshotManager


class SnapTaskExecutor:
    """Executes the complete Snapchat daily snap workflow with retries and logging."""

    def __init__(
        self,
        config: AppConfig,
        snapchat_controller: SnapchatController,
        device_manager: DeviceManager,
        watchdog_engine: WatchdogEngine,
        repository: BotRepository,
        screenshot_manager: ScreenshotManager,
    ):
        self.config = config
        self.snapchat = snapchat_controller
        self.device = device_manager
        self.watchdog = watchdog_engine
        self.repo = repository
        self.screenshot_mgr = screenshot_manager

    def run_snap_workflow(self, recipients: Optional[List[str]] = None) -> bool:
        """
        Executes the main daily snap workflow:
        1. Ensure system health via watchdog
        2. Wake screen & unlock
        3. Launch Snapchat
        4. Take black photo
        5. Press Next
        6. Select recipients
        7. Send snap
        8. Verify send success
        9. Return device to idle
        """
        target_recipients = recipients or self.config.snapchat.recipients
        logger.info(f"=== STARTING DAILY SNAP WORKFLOW (Recipients: {target_recipients}) ===")
        
        with ExecutionTimer() as timer:
            # 1. Run pre-flight health check & diagnostics
            if not self.watchdog.run_diagnostics_and_recover():
                logger.error("Pre-flight health check failed. Aborting workflow execution.")
                self._record_failure("Pre-flight health check failed", timer.duration_seconds, target_recipients)
                return False

            # 2. Wake screen & unlock
            try:
                self.device.wake_screen()
                self.device.unlock_screen()
                self.device.keep_screen_awake()
            except Exception as e:
                logger.error(f"Device wake/unlock failed: {e}")
                self._record_error_step("device_wake", e)

            # 3. Execute Snapchat step chain
            try:
                self.snapchat.open()
                self.snapchat.go_to_camera()
                self.snapchat.take_black_photo()
                self.snapchat.press_next()
                self.snapchat.select_recipients(target_recipients)
                self.snapchat.send()

                if not self.snapchat.verify_send():
                    raise Exception("Snap send verification failed - Toast/State not confirmed.")

                # 4. Clean teardown to idle
                self.snapchat.close()
                logger.success("=== SNAP WORKFLOW COMPLETED SUCCESSFULLY ===")

                exec_record = ExecutionRecord(
                    timestamp=datetime.now().isoformat(),
                    status="SUCCESS",
                    duration_seconds=timer.duration_seconds,
                    recipients_count=len(target_recipients),
                )
                self.repo.record_execution(exec_record)
                return True

            except Exception as e:
                logger.error(f"Snap workflow encountered error: {e}")
                self._record_error_step("workflow_execution", e)
                self.snapchat.recover()
                self._record_failure(str(e), timer.duration_seconds, target_recipients)
                return False

    def _record_error_step(self, step_name: str, exc: Exception) -> None:
        """Helper to save error records and diagnostic screenshots."""
        screenshot_path = self.screenshot_mgr.capture(f"error_{step_name}")
        err_record = ErrorRecord(
            timestamp=datetime.now().isoformat(),
            step=step_name,
            exception_class=type(exc).__name__,
            traceback=traceback.format_exc(),
            screenshot_path=screenshot_path,
        )
        self.repo.record_error(err_record)

    def _record_failure(self, err_msg: str, duration: float, recipients: List[str]) -> None:
        """Helper to record failed execution in repo."""
        exec_record = ExecutionRecord(
            timestamp=datetime.now().isoformat(),
            status="FAILED",
            duration_seconds=duration,
            recipients_count=len(recipients),
            error_message=err_msg,
        )
        self.repo.record_execution(exec_record)
