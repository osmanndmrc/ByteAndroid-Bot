"""
Android Touchscreen Event Recorder and Replayer with Automated Screenshot Capture.

Features:
  1. Record touchscreen gestures (taps, swipes, delays) from physical Android device.
  2. Replay recorded gestures with timestamps.
  3. Automatic step-by-step screenshot capture at every action stored in screenshots/ directory.

Usage:
  Record:
    python3 record_replay.py record --output gestures.json

  Replay with screenshots & logs:
    python3 record_replay.py replay --input gestures.json --app com.snapchat.android
"""

import sys
import time
import json
import re
import argparse
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import uiautomator2 as u2
    HAS_U2 = True
except ImportError:
    HAS_U2 = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("TouchRecorder")


class TouchRecorder:
    """Captures touchscreen events via ADB getevent and converts them to replayable gesture actions."""

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.adb_base_cmd = ["adb"]
        if self.device_id:
            self.adb_base_cmd.extend(["-s", self.device_id])

    def _get_touch_device_info(self) -> tuple[str, int, int]:
        """Detects the touchscreen input event device node and max X/Y bounds."""
        cmd = self.adb_base_cmd + ["shell", "getevent", "-p"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = res.stdout
        except Exception as e:
            logger.error(f"Failed to get input devices: {e}")
            sys.exit(1)

        current_dev = ""
        touch_dev = ""
        max_x = 0
        max_y = 0

        for line in output.splitlines():
            if line.startswith("add device"):
                match = re.search(r"add device \d+: (/.+)", line)
                if match:
                    current_dev = match.group(1).strip()
            elif "ABS_MT_POSITION_X" in line or "0035" in line:
                if current_dev and not touch_dev:
                    touch_dev = current_dev
                match = re.search(r"max (\d+)", line)
                if match and max_x == 0:
                    max_x = int(match.group(1))
            elif "ABS_MT_POSITION_Y" in line or "0036" in line:
                match = re.search(r"max (\d+)", line)
                if match and max_y == 0:
                    max_y = int(match.group(1))

        if not touch_dev:
            logger.warning("Auto-detect fallback: Targeting touchscreen event stream...")
            touch_dev = "/dev/input/event1"

        if max_x == 0:
            max_x = 1080
        if max_y == 0:
            max_y = 2400

        logger.info(f"Targeting Touchscreen Device Node: {touch_dev}, Max Bounds: X={max_x}, Y={max_y}")
        return touch_dev, max_x, max_y

    def record(self, output_file: str) -> None:
        """Starts recording touchscreen input events until interrupted by Ctrl+C."""
        touch_dev, max_x, max_y = self._get_touch_device_info()

        # Get screen size resolution via wm size
        res_cmd = self.adb_base_cmd + ["shell", "wm", "size"]
        try:
            res_out = subprocess.run(res_cmd, capture_output=True, text=True).stdout
            match = re.search(r"(\d+)x(\d+)", res_out)
            screen_w, screen_h = (int(match.group(1)), int(match.group(2))) if match else (1080, 2400)
        except Exception:
            screen_w, screen_h = 1080, 2400

        logger.info(f"Screen Display Resolution: {screen_w}x{screen_h}")

        scale_x = screen_w / max_x if max_x > 0 else 1.0
        scale_y = screen_h / max_y if max_y > 0 else 1.0

        getevent_cmd = self.adb_base_cmd + ["shell", "getevent", "-lt", touch_dev]

        logger.info("==================================================")
        logger.info("  RECORDING STARTED! Perform touch gestures on your phone.")
        logger.info("  Press Ctrl+C in this terminal when finished to save.")
        logger.info("==================================================")

        proc = subprocess.Popen(
            getevent_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        actions: List[Dict[str, Any]] = []
        stroke_x_coords: List[int] = []
        stroke_y_coords: List[int] = []
        touch_down = False
        stroke_start_time = 0.0
        last_event_time = time.time()

        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    break

                time_match = re.match(r"\[\s*([\d.]+)\s*\]\s*(.*)", line)
                if not time_match:
                    continue

                ts = float(time_match.group(1))
                payload = time_match.group(2)

                if "ABS_MT_POSITION_X" in payload:
                    val_hex = payload.split()[-1]
                    raw_x = int(val_hex, 16)
                    scaled_x = int(raw_x * scale_x)
                    stroke_x_coords.append(scaled_x)

                elif "ABS_MT_POSITION_Y" in payload:
                    val_hex = payload.split()[-1]
                    raw_y = int(val_hex, 16)
                    scaled_y = int(raw_y * scale_y)
                    stroke_y_coords.append(scaled_y)

                elif "BTN_TOUCH" in payload or "ABS_MT_TRACKING_ID" in payload:
                    if "DOWN" in payload or ("ABS_MT_TRACKING_ID" in payload and "ffffffff" not in payload):
                        if not touch_down:
                            touch_down = True
                            stroke_start_time = ts
                            stroke_x_coords.clear()
                            stroke_y_coords.clear()

                    elif "UP" in payload or "ffffffff" in payload:
                        if touch_down:
                            touch_down = False
                            stroke_end_time = ts

                            if stroke_x_coords and stroke_y_coords:
                                start_x = stroke_x_coords[0]
                                start_y = stroke_y_coords[0]
                                end_x = stroke_x_coords[-1]
                                end_y = stroke_y_coords[-1]

                                duration = round(max(0.05, stroke_end_time - stroke_start_time), 3)
                                dist = ((start_x - end_x) ** 2 + (start_y - end_y) ** 2) ** 0.5

                                delay = round(stroke_start_time - last_event_time, 3) if last_event_time else 0.5
                                if delay > 10.0 or len(actions) == 0:
                                    delay = 0.5

                                timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                                if dist < 40:  # Tap gesture
                                    avg_x = int(sum(stroke_x_coords) / len(stroke_x_coords))
                                    avg_y = int(sum(stroke_y_coords) / len(stroke_y_coords))
                                    action = {
                                        "timestamp": timestamp_str,
                                        "type": "tap",
                                        "x": avg_x,
                                        "y": avg_y,
                                        "delay": delay,
                                    }
                                    logger.info(f"Recorded TAP at ({avg_x}, {avg_y}) [delay={delay}s]")
                                else:  # Swipe gesture
                                    action = {
                                        "timestamp": timestamp_str,
                                        "type": "swipe",
                                        "x1": start_x,
                                        "y1": start_y,
                                        "x2": end_x,
                                        "y2": end_y,
                                        "duration_ms": int(duration * 1000),
                                        "delay": delay,
                                    }
                                    logger.info(
                                        f"Recorded SWIPE from ({start_x}, {start_y}) to ({end_x}, {end_y}) [{int(duration*1000)}ms, delay={delay}s]"
                                    )

                                actions.append(action)
                                last_event_time = stroke_end_time

        except KeyboardInterrupt:
            logger.info("Recording stopped by user.")
        finally:
            proc.terminate()

        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(actions, f, indent=2)

        logger.info(f"SUCCESS: Saved {len(actions)} recorded gestures to: {out_path.absolute()}")


class TouchReplayer:
    """Replays saved touch gesture JSON actions and captures step-by-step screenshots."""

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.adb_base_cmd = ["adb"]
        if self.device_id:
            self.adb_base_cmd.extend(["-s", self.device_id])

        self.u2_dev = None
        if HAS_U2:
            try:
                target = self.device_id if self.device_id else None
                self.u2_dev = u2.connect(target)
                logger.info("Using high-precision uiautomator2 engine for replay & screenshots.")
            except Exception as e:
                logger.warning(f"uiautomator2 connection failed: {e}. Falling back to adb shell...")

    def launch_app(self, package_name: str, delay_seconds: float = 3.0) -> None:
        """Launches target app package and waits for main screen readiness."""
        logger.info(f"Launching target app package: {package_name}...")
        try:
            cmd = self.adb_base_cmd + [
                "shell",
                "monkey",
                "-p",
                package_name,
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
            ]
            subprocess.run(cmd, check=False)
            time.sleep(delay_seconds)
            logger.info(f"App '{package_name}' launched. Waiting {delay_seconds}s for UI readiness.")
        except Exception as e:
            logger.warning(f"Failed to launch app '{package_name}': {e}")

    def capture_step_screenshot(self, run_dir: Path, step_idx: int, action_desc: str) -> None:
        """Captures a screenshot of the phone screen after executing a gesture step."""
        filename = f"step_{step_idx:02d}_{action_desc}.png"
        target_path = run_dir / filename

        try:
            if self.u2_dev:
                self.u2_dev.screenshot(str(target_path))
            else:
                self.adb_base_cmd
                subprocess.run(
                    self.adb_base_cmd + ["shell", "screencap", "-p", f"/sdcard/{filename}"],
                    check=False,
                )
                subprocess.run(
                    self.adb_base_cmd + ["pull", f"/sdcard/{filename}", str(target_path)],
                    check=False,
                )
                subprocess.run(
                    self.adb_base_cmd + ["shell", "rm", f"/sdcard/{filename}"], check=False
                )

            if target_path.exists():
                logger.info(f"Captured screenshot: {target_path.name}")
        except Exception as e:
            logger.warning(f"Failed to capture step screenshot: {e}")

    def replay(
        self,
        input_file: str,
        repeat: int = 1,
        speed: float = 1.0,
        app_package: Optional[str] = None,
        take_screenshots: bool = True,
    ) -> None:
        """Replays gesture sequence and records timestamps and step-by-step screenshots."""
        in_path = Path(input_file)
        if not in_path.exists():
            logger.error(f"Gesture file not found: {in_path}")
            sys.exit(1)

        with open(in_path, "r", encoding="utf-8") as f:
            actions: List[Dict[str, Any]] = json.load(f)

        if not actions:
            logger.warning("Gesture file is empty. Nothing to replay.")
            return

        if app_package:
            self.launch_app(app_package)

        # Create timestamped screenshot output folder: screenshots/run_YYYYMMDD_HHMMSS/
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path("screenshots") / f"run_{run_timestamp}"
        if take_screenshots:
            run_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Screenshots for this run will be saved in: {run_dir.absolute()}")

        logger.info(f"Replaying {len(actions)} gestures (Repeat: {repeat}x, Speed: {speed}x)...")

        for iteration in range(1, repeat + 1):
            logger.info(f"--- Iteration {iteration}/{repeat} ---")
            for idx, act in enumerate(actions, start=1):
                delay = act.get("delay", 0.5) / max(0.1, speed)
                if delay > 0:
                    time.sleep(delay)

                now_time = datetime.now().strftime("%H:%M:%S")
                act_type = act.get("type")

                if act_type == "tap":
                    x, y = act["x"], act["y"]
                    logger.info(f"[{now_time}] Step {idx}/{len(actions)}: TAP at ({x}, {y})")

                    if self.u2_dev:
                        self.u2_dev.click(x, y)
                    else:
                        cmd = self.adb_base_cmd + ["shell", "input", "tap", str(x), str(y)]
                        subprocess.run(cmd, check=False)

                    if take_screenshots:
                        time.sleep(0.5)  # Short pause for UI transition
                        self.capture_step_screenshot(run_dir, idx, f"tap_{x}_{y}")

                elif act_type == "swipe":
                    x1, y1 = act["x1"], act["y1"]
                    x2, y2 = act["x2"], act["y2"]
                    dur = int(act.get("duration_ms", 300) / max(0.1, speed))
                    logger.info(
                        f"[{now_time}] Step {idx}/{len(actions)}: SWIPE ({x1},{y1}) -> ({x2},{y2}) [{dur}ms]"
                    )

                    if self.u2_dev:
                        self.u2_dev.swipe(x1, y1, x2, y2, duration=dur / 1000.0)
                    else:
                        cmd = self.adb_base_cmd + [
                            "shell",
                            "input",
                            "swipe",
                            str(x1),
                            str(y1),
                            str(x2),
                            str(y2),
                            str(dur),
                        ]
                        subprocess.run(cmd, check=False)

                    if take_screenshots:
                        time.sleep(0.5)
                        self.capture_step_screenshot(run_dir, idx, f"swipe_{x1}_{y1}_to_{x2}_{y2}")

        logger.info(f"SUCCESS: Gesture replay finished! Screenshots saved in: {run_dir.absolute() if take_screenshots else 'None'}")


def main():
    parser = argparse.ArgumentParser(description="Android Touch Gesture Recorder and Replayer with Screenshots")
    parser.add_argument(
        "mode", choices=["record", "replay"], help="Operation mode: 'record' or 'replay'"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="gestures.json",
        help="Path to save recorded gestures JSON",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="gestures.json",
        help="Path to load recorded gestures JSON for replay",
    )
    parser.add_argument(
        "--device", "-s", type=str, default=None, help="ADB target device ID or IP:Port"
    )
    parser.add_argument(
        "--app",
        "-a",
        type=str,
        default=None,
        help="Optional package name to auto-launch before replaying (e.g. com.snapchat.android)",
    )
    parser.add_argument(
        "--repeat", "-r", type=int, default=1, help="Number of replay iterations"
    )
    parser.add_argument(
        "--speed", type=float, default=1.0, help="Replay playback speed multiplier (e.g. 1.5, 2.0)"
    )
    parser.add_argument(
        "--no-screenshots",
        action="store_true",
        help="Disable automatic step-by-step screenshot capture during replay",
    )

    args = parser.parse_args()

    if args.mode == "record":
        recorder = TouchRecorder(device_id=args.device)
        recorder.record(output_file=args.output)
    elif args.mode == "replay":
        replayer = TouchReplayer(device_id=args.device)
        replayer.replay(
            input_file=args.input,
            repeat=args.repeat,
            speed=args.speed,
            app_package=args.app,
            take_screenshots=not args.no_screenshots,
        )


if __name__ == "__main__":
    main()
