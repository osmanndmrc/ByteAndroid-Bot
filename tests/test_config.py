"""Tests for ConfigLoader and Pydantic validation models."""

import pytest
from pathlib import Path
from config.config_loader import ConfigLoader, AppConfig, TimeWindowConfig


def test_load_default_config(tmp_path: Path):
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("""
adb:
  host: "192.168.1.50"
  port: 5555
snapchat:
  recipients: ["user_a", "user_b"]
schedule:
  time_windows:
    - start_time: "08:00"
      end_time: "10:00"
""", encoding="utf-8")

    config = ConfigLoader.load(config_file)
    assert isinstance(config, AppConfig)
    assert config.adb.host == "192.168.1.50"
    assert config.adb.port == 5555
    assert config.snapchat.recipients == ["user_a", "user_b"]
    assert len(config.schedule.time_windows) == 1
    assert config.schedule.time_windows[0].start_time == "08:00"


def test_invalid_time_window():
    with pytest.raises(Exception):
        TimeWindowConfig(start_time="25:00", end_time="10:00")
