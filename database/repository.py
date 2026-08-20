"""
Repository pattern implementations for database persistence queries.
"""

from datetime import datetime
from typing import Optional, List
from loguru import logger
from database.db import DatabaseManager
from database.models import ExecutionRecord, ErrorRecord, RestartRecord, StatisticRecord


class BotRepository:
    """Repository handling CRUD and metric aggregation queries for SnapBot telemetry."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def record_execution(self, record: ExecutionRecord) -> int:
        """Inserts a new execution record and updates daily statistics."""
        timestamp = record.timestamp or datetime.now().isoformat()
        today = datetime.now().strftime("%Y-%m-%d")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO executions (timestamp, status, duration_seconds, recipients_count, error_message)
                VALUES (?, ?, ?, ?, ?)
                """,
                (timestamp, record.status, record.duration_seconds, record.recipients_count, record.error_message),
            )
            exec_id = cursor.lastrowid

            # Update daily statistics aggregate
            is_success = 1 if record.status == "SUCCESS" else 0
            is_fail = 1 if record.status != "SUCCESS" else 0

            cursor.execute(
                """
                INSERT INTO statistics (date, total_executions, successful_executions, failed_executions, total_restarts, streak_days)
                VALUES (?, 1, ?, ?, 0, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_executions = total_executions + 1,
                    successful_executions = successful_executions + ?,
                    failed_executions = failed_executions + ?
                """,
                (today, is_success, is_fail, is_success, is_success, is_fail),
            )
            return exec_id

    def record_error(self, record: ErrorRecord) -> int:
        """Inserts an error record."""
        timestamp = record.timestamp or datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO errors (timestamp, step, exception_class, traceback, screenshot_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (timestamp, record.step, record.exception_class, record.traceback, record.screenshot_path),
            )
            return cursor.lastrowid

    def record_restart(self, record: RestartRecord) -> int:
        """Inserts a restart record and increments total_restarts stat."""
        timestamp = record.timestamp or datetime.now().isoformat()
        today = datetime.now().strftime("%Y-%m-%d")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO restarts (timestamp, tier_level, reason, success_after_restart)
                VALUES (?, ?, ?, ?)
                """,
                (timestamp, record.tier_level, record.reason, 1 if record.success_after_restart else 0),
            )
            restart_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO statistics (date, total_executions, successful_executions, failed_executions, total_restarts, streak_days)
                VALUES (?, 0, 0, 0, 1, 0)
                ON CONFLICT(date) DO UPDATE SET
                    total_restarts = total_restarts + 1
                """,
                (today,),
            )
            return restart_id

    def update_restart_status(self, restart_id: int, success: bool) -> None:
        """Updates restart success status after recovery attempt."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE restarts SET success_after_restart = ? WHERE id = ?",
                (1 if success else 0, restart_id),
            )

    def get_last_successful_execution(self) -> Optional[ExecutionRecord]:
        """Fetches the most recent successful execution record."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM executions WHERE status = 'SUCCESS' ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return ExecutionRecord(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    status=row["status"],
                    duration_seconds=row["duration_seconds"],
                    recipients_count=row["recipients_count"],
                    error_message=row["error_message"],
                )
            return None

    def get_restart_count_for_today(self) -> int:
        """Returns total restart events triggered today."""
        today = datetime.now().strftime("%Y-%m-%d")
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT total_restarts FROM statistics WHERE date = ?", (today,))
            row = cursor.fetchone()
            return row["total_restarts"] if row else 0
