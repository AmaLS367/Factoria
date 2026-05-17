import datetime
import logging
import sqlite3
import uuid
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.utils.db_writer import get_db_path, init_db

logger = logging.getLogger(__name__)


def create_job(
    input_file: str,
    output_file: str,
    total_items: int,
    job_id: Optional[str] = None,
    sheet_name: Optional[str] = None,
    column_name: Optional[str] = None,
) -> str:
    # Ensure DB is initialized to have the table
    init_db(settings.target_fields, create_default_run=False)

    job_id = job_id or str(uuid.uuid4())
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO jobs (job_id, status, input_file, output_file, total_items, sheet_name, column_name)
            VALUES (?, 'queued', ?, ?, ?, ?, ?)
            """,
            (job_id, input_file, output_file, total_items, sheet_name, column_name),
        )
        conn.commit()
        return job_id
    except Exception as e:
        logger.error(f"Error creating job {job_id}: {e}")
        raise
    finally:
        conn.close()


def cancel_job(job_id: str) -> bool:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM jobs WHERE job_id = ?", (job_id,))
        row = cur.fetchone()
        if not row or row[0] not in ("queued", "running"):
            return False
        cur.execute(
            "UPDATE jobs SET status = 'cancelled', finished_at = ? WHERE job_id = ?",
            (now, job_id),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        return False
    finally:
        conn.close()


def update_job_status(job_id: str, status: str, error_message: Optional[str] = None) -> None:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        cur = conn.cursor()

        updates = ["status = ?"]
        params: List[Any] = [status]

        if status == "running":
            updates.append("started_at = ?")
            params.append(now)
        elif status in ("completed", "failed", "cancelled"):
            updates.append("finished_at = ?")
            params.append(now)

        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)

        params.append(job_id)

        query = f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?"
        cur.execute(query, tuple(params))
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating job {job_id} status: {e}")
    finally:
        conn.close()


def update_job_progress(job_id: str, processed: int = 0, skipped: int = 0, failed: int = 0) -> None:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE jobs
            SET processed_items = processed_items + ?,
                skipped_items = skipped_items + ?,
                failed_items = failed_items + ?
            WHERE job_id = ?
            """,
            (processed, skipped, failed, job_id),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating job {job_id} progress: {e}")
    finally:
        conn.close()


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        return None
    finally:
        conn.close()


def get_recent_jobs(limit: int = 10) -> List[Dict[str, Any]]:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # Just in case the DB doesn't exist yet, try initializing
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'")
        if not cur.fetchone():
            return []

        cur.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        return []
    finally:
        conn.close()


def update_job_total_items(job_id: str, total_items: int) -> None:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("UPDATE jobs SET total_items = ? WHERE job_id = ?", (total_items, job_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating job {job_id} total_items: {e}")
    finally:
        conn.close()
