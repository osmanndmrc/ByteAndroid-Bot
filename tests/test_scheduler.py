"""Tests for JobScheduler randomized time window calculation and scheduling logic."""

from unittest.mock import MagicMock
from datetime import datetime
from config.config_loader import AppConfig, TimeWindowConfig
from scheduler.job_scheduler import JobScheduler


def test_calculate_random_execution_time():
    config = AppConfig()
    mock_executor = MagicMock()
    scheduler = JobScheduler(config, mock_executor)

    window = TimeWindowConfig(start_time="09:00", end_time="11:00")
    target_date = datetime(2026, 8, 20)

    for _ in range(50):
        random_dt = scheduler.calculate_random_execution_time(window, target_date)
        assert random_dt.date() == target_date.date()
        assert random_dt.hour in [9, 10, 11]
        if random_dt.hour == 11:
            assert random_dt.minute == 0
