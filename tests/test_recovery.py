"""Tests for RecoveryManager multi-tier escalation matrix."""

from unittest.mock import MagicMock
import pytest
from config.config_loader import AppConfig
from watchdog.recovery import RecoveryManager
from core.exceptions import RecoveryEscalationMaxedError


def test_recovery_tier_exceeds_max():
    config = AppConfig()
    config.watchdog.max_tier = 3
    mock_adb = MagicMock()
    mock_dev = MagicMock()
    mock_repo = MagicMock()

    recovery = RecoveryManager(config, mock_adb, mock_dev, mock_repo)

    with pytest.raises(RecoveryEscalationMaxedError):
        recovery.recover(target_tier=4, reason="Test exceed tier")


def test_tier1_recovery_execution():
    config = AppConfig()
    mock_adb = MagicMock()
    mock_dev = MagicMock()
    mock_repo = MagicMock()
    mock_repo.record_restart.return_value = 1

    recovery = RecoveryManager(config, mock_adb, mock_dev, mock_repo)
    success = recovery.recover(target_tier=1, reason="Test tier 1")

    assert success is True
    mock_adb.force_stop_app.assert_called_once_with(config.snapchat.package_name)
    mock_adb.start_app.assert_called_once()
