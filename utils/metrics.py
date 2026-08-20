"""
Execution timer and performance metrics tracking module.
"""

import time
from typing import Optional


class ExecutionTimer:
    """Context manager for timing task and step execution durations."""

    def __init__(self, name: str = "task"):
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def __enter__(self) -> "ExecutionTimer":
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.end_time = time.time()

    @property
    def duration_seconds(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return round(end - self.start_time, 2)
