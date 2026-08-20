"""Tests for DatabaseManager and BotRepository CRUD operations."""

import pytest
from pathlib import Path
from config.config_loader import DatabaseConfig
from database.db import DatabaseManager
from database.repository import BotRepository
from database.models import ExecutionRecord, ErrorRecord, RestartRecord


@pytest.fixture
def temp_db(tmp_path: Path):
    db_file = tmp_path / "test_snapbot.db"
    config = DatabaseConfig(path=str(db_file))
    db_mgr = DatabaseManager(config)
    repo = BotRepository(db_mgr)
    return repo


def test_record_execution(temp_db: BotRepository):
    rec = ExecutionRecord(status="SUCCESS", duration_seconds=12.5, recipients_count=2)
    exec_id = temp_db.record_execution(rec)
    assert exec_id > 0

    last = temp_db.get_last_successful_execution()
    assert last is not None
    assert last.status == "SUCCESS"
    assert last.duration_seconds == 12.5
    assert last.recipients_count == 2


def test_record_error(temp_db: BotRepository):
    err = ErrorRecord(step="take_photo", exception_class="SnapchatCameraError", traceback="Traceback info")
    err_id = temp_db.record_error(err)
    assert err_id > 0


def test_record_restart(temp_db: BotRepository):
    rst = RestartRecord(tier_level=2, reason="ADB disconnect", success_after_restart=True)
    rst_id = temp_db.record_restart(rst)
    assert rst_id > 0

    restart_count = temp_db.get_restart_count_for_today()
    assert restart_count >= 1
