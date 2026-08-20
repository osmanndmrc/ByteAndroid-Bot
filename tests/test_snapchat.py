"""Tests for SnapchatController and CameraHandler UI automation abstraction."""

from unittest.mock import MagicMock
from config.config_loader import SnapchatConfig
from snapchat.controller import SnapchatController


def test_snapchat_controller_init():
    config = SnapchatConfig(recipients=["user1", "user2"])
    mock_adb = MagicMock()
    mock_screen = MagicMock()

    controller = SnapchatController(mock_adb, config, mock_screen)
    assert controller.config.recipients == ["user1", "user2"]


def test_snapchat_health_check_process_dead():
    config = SnapchatConfig()
    mock_adb = MagicMock()
    mock_adb.run_shell.return_value = ""  # empty pid string

    controller = SnapchatController(mock_adb, config)
    assert controller.health_check() is False
