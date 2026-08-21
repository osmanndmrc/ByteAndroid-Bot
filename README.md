# Android Touch Gesture Recorder, Replayer & Screenshot Logger

A lightweight, high-precision Python tool to record physical touchscreen gestures from an Android device, replay them accurately, log timestamps, and automatically capture step-by-step screenshots into timestamped folders.

---

## 🚀 Usage

### 1. Record Gestures
Connect your Android phone via USB/ADB and record your touch taps, swipes, and delays:
```bash
python3 record_replay.py record --output snap_fiziksel.json
```
*(Perform your gestures on your phone, then press `Ctrl+C` to save).*

---

### 2. Replay Gestures with Step-by-Step Screenshots
Replay the recorded gestures while automatically launching Snapchat, logging timestamps, and capturing a screenshot PNG at every single step:

```bash
python3 record_replay.py replay --input snap_fiziksel.json --app com.snapchat.android
```

#### Screenshots Output Directory:
Screenshots are automatically saved step-by-step into timestamped folders:
```text
screenshots/
└── run_20260820_163000/
    ├── step_01_tap_685_345.png
    ├── step_02_tap_242_1895.png
    ├── step_03_tap_760_2056.png
    └── step_04_swipe_614_2400_to_707_1864.png
```

---

### 💡 Options & Customization

- **Speed Multiplier**: Replay 1.5x faster
  ```bash
  python3 record_replay.py replay --input snap_fiziksel.json --speed 1.5
  ```
- **Repeat Loop**: Repeat the recorded scenario 5 times
  ```bash
  python3 record_replay.py replay --input snap_fiziksel.json --repeat 5
  ```
- **Disable Screenshots**:
  ```bash
  python3 record_replay.py replay --input snap_fiziksel.json --no-screenshots
  ```
