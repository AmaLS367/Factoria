import sqlite3
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from backend.config import settings
from backend.utils.db_writer import init_db
from backend.utils.jobs import (
    cancel_job,
    create_job,
    get_job,
    get_recent_jobs,
    update_job_progress,
    update_job_status,
    update_job_token_usage,
    update_job_total_items,
)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path: Path) -> Generator[None, None, None]:
    # Override db_path for tests
    db_file = tmp_path / "test_jobs.sqlite"
    original_db_path = settings.db_path
    settings.db_path = str(db_file)

    # Initialize DB schema
    init_db(settings.target_fields)

    yield

    # Restore db_path
    settings.db_path = original_db_path


def test_job_lifecycle() -> None:
    # 1. Create a job
    job_id = create_job("in.xlsx", "out.xlsx", 10)
    assert job_id is not None

    # Verify job creation
    job = get_job(job_id)
    assert job is not None
    assert job["job_id"] == job_id
    assert job["status"] == "queued"
    assert job["total_items"] == 10
    assert job["processed_items"] == 0
    assert job["started_at"] is None
    assert job["finished_at"] is None

    # 2. Update status to running
    update_job_status(job_id, "running")
    job = get_job(job_id)
    assert job is not None
    assert job["status"] == "running"
    assert job["started_at"] is not None
    assert job["finished_at"] is None

    # 3. Update progress
    update_job_progress(job_id, processed=5, skipped=2, failed=1)
    job = get_job(job_id)
    assert job is not None
    assert job["processed_items"] == 5
    assert job["skipped_items"] == 2
    assert job["failed_items"] == 1

    # 4. Update status to completed
    update_job_status(job_id, "completed")
    job = get_job(job_id)
    assert job is not None
    assert job["status"] == "completed"
    assert job["finished_at"] is not None
    assert job["error_message"] is None


def test_job_failure() -> None:
    job_id = create_job("in2.xlsx", "out2.xlsx", 5)

    update_job_status(job_id, "failed", "Test error message")
    job = get_job(job_id)
    assert job is not None
    assert job["status"] == "failed"
    assert job["error_message"] == "Test error message"
    assert job["finished_at"] is not None


def test_get_recent_jobs() -> None:
    job_id1 = create_job("in1.xlsx", "out1.xlsx", 1)
    time.sleep(1)
    job_id2 = create_job("in2.xlsx", "out2.xlsx", 2)

    jobs = get_recent_jobs(limit=10)
    assert len(jobs) >= 2
    # Ensure ordered by created_at DESC
    assert jobs[0]["job_id"] == job_id2
    assert jobs[1]["job_id"] == job_id1


def test_cancel_job_happy_path() -> None:
    job_id = create_job("in.xlsx", "out.xlsx", 5)
    assert cancel_job(job_id) is True

    job = get_job(job_id)
    assert job is not None
    assert job["status"] == "cancelled"
    assert job["finished_at"] is not None


def test_cancel_job_running_is_allowed() -> None:
    job_id = create_job("in.xlsx", "out.xlsx", 5)
    update_job_status(job_id, "running")
    assert cancel_job(job_id) is True


def test_cancel_job_returns_false_for_unknown_id() -> None:
    assert cancel_job("nonexistent-job-id") is False


def test_cancel_job_returns_false_when_already_completed() -> None:
    job_id = create_job("in.xlsx", "out.xlsx", 5)
    update_job_status(job_id, "completed")
    assert cancel_job(job_id) is False


def test_update_job_total_items() -> None:
    job_id = create_job("in.xlsx", "out.xlsx", 0)
    update_job_total_items(job_id, 42)
    job = get_job(job_id)
    assert job is not None
    assert job["total_items"] == 42


def test_update_job_token_usage_accumulates() -> None:
    job_id = create_job("in.xlsx", "out.xlsx", 0)

    update_job_token_usage(job_id, 100, 50, 0.001)
    update_job_token_usage(job_id, 100, 50, 0.001)

    job = get_job(job_id)
    assert job is not None
    assert job["total_prompt_tokens"] == 200
    assert job["total_completion_tokens"] == 100
    assert job["total_llm_requests"] == 2
    assert job["estimated_cost_usd"] == pytest.approx(0.002)


def test_get_job_includes_token_fields() -> None:
    job_id = create_job("in.xlsx", "out.xlsx", 0)

    update_job_token_usage(job_id, 500, 200, 0.01)

    job = get_job(job_id)
    assert job is not None
    assert job["total_prompt_tokens"] == 500
    assert job["total_completion_tokens"] == 200
    assert job["total_llm_requests"] == 1
    assert job["estimated_cost_usd"] == pytest.approx(0.01)


def test_get_job_returns_none_for_unknown_id() -> None:
    assert get_job("does-not-exist") is None


def test_get_recent_jobs_returns_empty_when_table_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Point at a fresh empty sqlite that has no `jobs` table
    empty_db = tmp_path / "empty.sqlite"
    conn = sqlite3.connect(str(empty_db))
    conn.close()
    monkeypatch.setattr(settings, "db_path", str(empty_db))
    assert get_recent_jobs() == []


def test_update_job_progress_accumulates() -> None:
    job_id = create_job("in.xlsx", "out.xlsx", 10)
    update_job_progress(job_id, processed=2, skipped=1, failed=0)
    update_job_progress(job_id, processed=3, skipped=0, failed=1)

    job = get_job(job_id)
    assert job is not None
    assert job["processed_items"] == 5
    assert job["skipped_items"] == 1
    assert job["failed_items"] == 1


def test_create_job_with_template_fields_roundtrips() -> None:
    job_id = create_job(
        "in.xlsx",
        "out.xlsx",
        0,
        sheet_name="Sheet2",
        column_name="Part Number",
        target_fields=["Name", "Material"],
        item_label="component",
    )
    job = get_job(job_id)
    assert job is not None
    assert job["sheet_name"] == "Sheet2"
    assert job["column_name"] == "Part Number"
    assert job["item_label"] == "component"
    # target_fields stored as JSON string
    assert job["target_fields"] == '["Name", "Material"]'
