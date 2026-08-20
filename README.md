# SnapBot - Snapchat Automation Daemon for ReDroid / Linux

Production-grade, highly resilient Snapchat automation bot designed to run 24/7 unattended on Linux servers inside ReDroid (Android in Docker).

---

## 🌟 Key Features

- **Continuous 30-60 Day Unattended Operation**: Self-healing architecture built for unattended long-term execution.
- **Randomized Execution Windows**: Schedules daily snap runs at a random minute within configured time windows (e.g. between 09:00-11:00 and 20:00-22:00) to mimic natural human activity.
- **5-Tier Escalation Recovery Matrix**:
  1. *Tier 1*: Force stop Snapchat and relaunch.
  2. *Tier 2*: Restart ADB server and reconnect socket.
  3. *Tier 3*: Restart ReDroid Docker container.
  4. *Tier 4*: Restart Docker system daemon.
  5. *Tier 5*: Reboot host OS (optional last resort).
- **SQLite Telemetry & Diagnostics**: Persists execution records, exception tracebacks, restart counts, and daily statistics.
- **Automatic Screen Capture on Error**: Saves PNG screenshots to `screenshots/` on UI failures.
- **Loguru Rotating Logs**: Structured console output and daily rotating file logs (`logs/snapbot_YYYY-MM-DD.log`).

---

## 📁 Project Structure

```
snapbot/
├── config/
│   ├── config.yaml          # Production configuration file
│   └── config_loader.py     # Pydantic & YAML validator
├── core/
│   ├── bot.py               # Main application orchestrator
│   ├── device_manager.py    # Screen wake/unlock & OS freeze detection
│   └── exceptions.py        # Custom exception hierarchy
├── adb/
│   └── adb_manager.py       # ADB connection & uiautomator2 wrapper
├── snapchat/
│   ├── camera_handler.py    # Camera shutter & black photo capture
│   ├── controller.py        # High-level Snapchat API
│   └── ui_selectors.py      # Selector strategies & fallback locators
├── watchdog/
│   ├── recovery.py          # Multi-tier escalation matrix
│   └── watchdog.py          # Health check engine
├── scheduler/
│   ├── job_scheduler.py     # APScheduler with randomized minute calculation
│   └── tasks.py             # Snap workflow task wrapper
├── database/
│   ├── db.py                # Thread-safe SQLite connection pool
│   ├── models.py            # Telemetry dataclasses
│   └── repository.py        # Persistence queries
├── utils/
│   ├── logger.py            # Loguru setup
│   ├── metrics.py           # Execution duration timer
│   └── screenshot.py        # Failure screenshot capture
├── tests/                   # Pytest test suite
├── Dockerfile               # Production Docker image build
├── docker-compose.yml       # ReDroid + SnapBot stack definition
├── requirements.txt         # Dependencies
└── main.py                  # Entrypoint CLI
```

---

## 🚀 Getting Started (Linux Server Deployment)

### 1. Host Kernel Preparation (Linux / Ubuntu Server)
```bash
sudo apt update
sudo apt install -y linux-modules-extra-$(uname -r)
sudo modprobe binder_linux devices="binder,hwbinder,vndbinder"
```

### 2. Launch Docker Stack
```bash
docker-compose up -d --build
```

### 3. Visual GUI Access & Snapchat Setup via `scrcpy`
ReDroid exposes port `5555`. You can visually view and control the Android screen directly from your local computer via network `scrcpy`:

```bash
# On your local computer (Mac/Linux/Windows):
adb connect <UBUNTU_SERVER_IP>:5555
scrcpy -s <UBUNTU_SERVER_IP>:5555
```

- Install Snapchat APK (`adb -s <UBUNTU_SERVER_IP>:5555 install snapchat.apk`).
- Perform initial account login and approve initial permissions.
- Once logged in, the session persists inside `redroid-data` volume for 30-60 days.

---

## 💻 Local CLI Test Execution
To run an immediate manual snap workflow test run:
```bash
python main.py --now
```
