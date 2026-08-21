"""
Standalone Automated Scheduler Daemon for Touch Gesture Replay.

Features:
  1. Auto-wakes and unlocks device screen.
  2. Auto-heals Wi-Fi network connectivity.
  3. Replays recorded gestures with timestamped step-by-step screenshots.
  4. Runs daily at randomized time windows (e.g. 09:00-11:00 & 20:00-22:00).
  5. Compatible with Termux (On-Device Python execution without PC) & Mac/PC.

Usage:
  python3 runner.py [--now] [--device DEVICE_ID]
"""

import sys
import time
import random
import argparse
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path
from record_replay import TouchReplayer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("SnapRunner")


class AutoSnapRunner:
    """Manages automatic screen unlock, Wi-Fi recovery, gesture replay with screenshots, and daily scheduling."""

    def __init__(self, device_id: str = None, gesture_file: str = "snap_fiziksel.json", app_package: str = "com.snapchat.android"):
        self.device_id = device_id
        self.gesture_file = gesture_file
        self.app_package = app_package
        self.adb_cmd = ["adb"]
        if self.device_id:
            self.adb_cmd.extend(["-s", self.device_id])

    def wake_and_unlock(self) -> None:
        """Wakes up phone screen and unlocks keyguard."""
        logger.info("Waking up device screen and unlocking keyguard...")
        try:
            # Wake screen (Keyevent 224: WAKEUP, 26: POWER)
            subprocess.run(self.adb_cmd + ["shell", "input", "keyevent", "224"], check=False)
            time.sleep(1)
            # Unlock swipe gesture
            subprocess.run(self.adb_cmd + ["shell", "input", "keyevent", "82"], check=False)
            time.sleep(0.5)
            subprocess.run(self.adb_cmd + ["shell", "input", "swipe", "500", "1500", "500", "500", "300"], check=False)
            time.sleep(1)
            # Stay awake while plugged in
            subprocess.run(self.adb_cmd + ["shell", "settings", "put", "global", "stay_on_while_plugged_in", "7"], check=False)
            logger.info("Device screen is awake and unlocked.")
        except Exception as e:
            logger.warning(f"Wake/unlock exception: {e}")

    def ensure_wifi(self) -> None:
        """Forces Wi-Fi to enable if network dropped."""
        logger.info("Verifying device network connectivity...")
        try:
            res = subprocess.run(self.adb_cmd + ["shell", "ping", "-c", "1", "8.8.8.8"], capture_output=True, text=True)
            if "bytes from" in res.stdout:
                logger.info("Wi-Fi network connection verified.")
                return
        except Exception:
            pass

        logger.warning("Wi-Fi network disconnected. Force-enabling Wi-Fi via ADB...")
        try:
            subprocess.run(self.adb_cmd + ["shell", "svc", "wifi", "enable"], check=False)
            subprocess.run(self.adb_cmd + ["shell", "cmd", "wifi", "set-wifi-enabled", "enabled"], check=False)
            time.sleep(5)
        except Exception as e:
            logger.warning(f"Failed to enable Wi-Fi: {e}")

    def run_job(self) -> bool:
        """Executes the full automated workflow with screenshots."""
        logger.info("==================================================")
        logger.info(f"  EXECUTING AUTOMATED SNAP REPLAY WORKFLOW [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
        logger.info("==================================================")

        # 1. Ensure Wi-Fi
        self.ensure_wifi()

        # 2. Wake screen & unlock keyguard
        self.wake_and_unlock()

        # 3. Replay gestures with step-by-step screenshots
        try:
            replayer = TouchReplayer(device_id=self.device_id)
            replayer.replay(
                input_file=self.gesture_file,
                repeat=1,
                speed=1.0,
                app_package=self.app_package,
                take_screenshots=True,
            )
            logger.info("SUCCESS: Automated Snap replay completed!")
            return True
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return False

    def schedule_loop(self, windows=[("09:00", "11:00"), ("20:00", "22:00")]) -> None:
        """Runs the continuous background daemon scheduling runs at random minutes within target windows."""
        logger.info("SnapRunner background daemon started. Monitoring daily schedule...")

        while True:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")

            # Calculate today's target execution times
            target_times = []
            for start_str, end_str in windows:
                start_dt = datetime.strptime(f"{today_str} {start_str}", "%Y-%m-%d %H:%M")
                end_dt = datetime.strptime(f"{today_str} {end_str}", "%Y-%m-%d %H:%M")

                total_seconds = int((end_dt - start_dt).total_seconds())
                random_offset = random.randint(0, total_seconds)
                target_dt = start_dt + timedelta(seconds=random_offset)

                if target_dt > now:
                    target_times.append(target_dt)

            if not target_times:
                # All windows passed today, sleep until midnight
                tomorrow = now.date() + timedelta(days=1)
                midnight = datetime.combine(tomorrow, datetime.min.time())
                sleep_seconds = (midnight - now).total_seconds() + 60
                logger.info(f"All today's run windows completed. Sleeping until tomorrow midnight ({int(sleep_seconds)}s)...")
                time.sleep(sleep_seconds)
                continue

            next_run = min(target_times)
            wait_seconds = (next_run - now).total_seconds()
            logger.info(f"NEXT SCHEDULED RUN AT: {next_run.strftime('%H:%M:%S')} (Waiting {int(wait_seconds)} seconds)...")

            time.sleep(wait_seconds)

            # Execute run
            self.run_job()
            time.sleep(60)  # Avoid duplicate triggers within same minute


def main():
    parser = argparse.ArgumentParser(description="Automated Snap Replay Runner Daemon")
    parser.add_argument("--now", action="store_true", help="Run workflow immediately once and exit")
    parser.add_argument("--device", "-s", type=str, default=None, help="ADB target device ID")
    parser.add_argument("--input", "-i", type=str, default="snap_fiziksel.json", help="Gesture JSON file")
    args = parser.parse_args()

    runner = AutoSnapRunner(device_id=args.device, gesture_file=args.input)

    if args.now:
        runner.run_job()
    else:
        try:
            runner.schedule_loop()
        except KeyboardInterrupt:
            logger.info("SnapRunner stopped by user.")


if __name__ == "__main__":
    main()
