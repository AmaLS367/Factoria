import time
import typing

import pytest

from backend.config import settings
from backend.utils.db_writer import init_db
from backend.utils.jobs import (
    create_job,
    get_job,
    get_recent_jobs,
    update_job_progress,
    update_job_status,
)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path: typing.Any) -> typing.Generator[None, None, None]:
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
