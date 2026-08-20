"""Tests for ADBManager low-level device connection handling."""

from unittest.mock import MagicMock, patch
import subprocess
from config.config_loader import ADBConfig
from adb.adb_manager import ADBManager


def test_adb_target_property():
    config = ADBConfig(host="10.0.0.5", port=5555)
    mgr = ADBManager(config)
    assert mgr.target == "10.0.0.5:5555"


@patch("subprocess.run")
def test_adb_is_device_connected(mock_run):
    config = ADBConfig(host="127.0.0.1", port=5555)
    mgr = ADBManager(config)

    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="List of devices attached\n127.0.0.1:5555\tdevice\n", stderr=""
    )
    assert mgr.is_device_connected() is True
