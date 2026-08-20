"""
Screenshot utility for capturing diagnostic UI screenshots on unexpected screens or errors.
"""

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from adb.adb_manager import ADBManager

from config.config_loader import ScreenshotConfig


class ScreenshotManager:
    """Captures and manages diagnostic screenshots taken during automation runs."""

    def __init__(self, adb_manager: "ADBManager", config: ScreenshotConfig):
        self.adb = adb_manager
        self.config = config
        self.output_dir = Path(config.directory)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def capture(self, prefix: str = "error") -> Optional[str]:
        """Captures screen PNG image and saves it to designated screenshot directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{prefix}_{timestamp}.png"
        target_path = self.output_dir / filename

        logger.info(f"Capturing diagnostic screenshot to: {target_path}")

        # Attempt 1: uiautomator2 screenshot method
        try:
            u2_dev = self.adb.get_u2_device()
            u2_dev.screenshot(str(target_path))
            if target_path.exists() and target_path.stat().st_size > 0:
                return str(target_path.absolute())
        except Exception as e:
            logger.warning(f"u2 screenshot capture failed: {e}. Falling back to adb exec-out...")

        # Attempt 2: ADB exec-out fallback
        try:
            self.adb.run_shell(f"screencap -p /sdcard/{filename}")
            self.adb.run_cmd(["pull", f"/sdcard/{filename}", str(target_path)])
            self.adb.run_shell(f"rm /sdcard/{filename}")

            if target_path.exists() and target_path.stat().st_size > 0:
                return str(target_path.absolute())
        except Exception as e:
            logger.error(f"ADB fallback screenshot capture failed: {e}")

        return None

    def cleanup_old_screenshots(self) -> int:
        """Removes screenshot files older than configured retention days."""
        cutoff = datetime.now() - timedelta(days=self.config.retention_days)
        removed_count = 0

        for file_path in self.output_dir.glob("*.png"):
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff:
                    file_path.unlink()
                    removed_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete old screenshot {file_path}: {e}")

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old screenshot files.")
        return removed_count
