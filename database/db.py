"""
SQLite Database connection and table schema initializer.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from loguru import logger
from config.config_loader import DatabaseConfig
from core.exceptions import DatabaseError


class DatabaseManager:
    """Manages thread-safe SQLite connections and schema initialization."""

    def __init__(self, config: DatabaseConfig):
        self.db_path = Path(config.path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provides a transactional context-managed SQLite connection."""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database transaction error: {e}")
            raise DatabaseError("SQLite connection error", original_exception=e)
        finally:
            if conn:
                conn.close()

    def init_db(self) -> None:
        """Initializes database tables if they do not exist."""
        logger.info(f"Initializing SQLite database schema at: {self.db_path}")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table: executions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_seconds REAL DEFAULT 0.0,
                    recipients_count INTEGER DEFAULT 0,
                    error_message TEXT
                )
            """)

            # Table: errors
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    step TEXT NOT NULL,
                    exception_class TEXT NOT NULL,
                    traceback TEXT NOT NULL,
                    screenshot_path TEXT
                )
            """)

            # Table: restarts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS restarts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    tier_level INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    success_after_restart INTEGER DEFAULT 0
                )
            """)

            # Table: statistics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    date TEXT PRIMARY KEY,
                    total_executions INTEGER DEFAULT 0,
                    successful_executions INTEGER DEFAULT 0,
                    failed_executions INTEGER DEFAULT 0,
                    total_restarts INTEGER DEFAULT 0,
                    streak_days INTEGER DEFAULT 0
                )
            """)
        logger.success("SQLite database schema initialized successfully.")
