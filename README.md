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

## 🚀 Getting Started

### 1. Requirements
- Linux Server (Ubuntu 20.04/22.04/24.04 recommended)
- Docker & Docker Compose
- ReDroid container running (`redroid/redroid:11.0.0-latest`)

### 2. Local Setup
```bash
# Clone repository
git clone https://github.com/your-repo/ByteAndroid-Bot.git
cd ByteAndroid-Bot

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Unit Tests
```bash
pytest -v
```

### 4. Running via Docker Compose
```bash
docker-compose up -d --build
```

### 5. Manual Execution Flag
To run an immediate snap workflow test run without waiting for the scheduler:
```bash
python main.py --now
```
