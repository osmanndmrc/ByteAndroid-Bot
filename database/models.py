"""
Database models and dataclasses for SnapBot telemetry.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionRecord:
    id: Optional[int] = None
    timestamp: str = ""
    status: str = "PENDING"  # SUCCESS, FAILED
    duration_seconds: float = 0.0
    recipients_count: int = 0
    error_message: Optional[str] = None


@dataclass
class ErrorRecord:
    id: Optional[int] = None
    timestamp: str = ""
    step: str = ""
    exception_class: str = ""
    traceback: str = ""
    screenshot_path: Optional[str] = None


@dataclass
class RestartRecord:
    id: Optional[int] = None
    timestamp: str = ""
    tier_level: int = 1
    reason: str = ""
    success_after_restart: bool = False


@dataclass
class StatisticRecord:
    date: str = ""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_restarts: int = 0
    streak_days: int = 0
