import hashlib
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Union, cast

from backend.utils.db_writer import get_db_path

logger = logging.getLogger(__name__)


def _deterministic_json_dumps(obj: Any) -> str:
    """Serialize an object to a deterministic JSON string for hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def make_cache_key(kind: str, provider: str, model: str, payload: Any) -> str:
    """Generate a unique cache key based on kind, provider, model, and deterministic payload."""
    payload_str = _deterministic_json_dumps(payload)
    input_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    key_parts = [kind, provider, model, input_hash]
    # Use another hash to keep the key length manageable
    key_str = "|".join(key_parts)
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()


def _ensure_cache_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache_entries (
            cache_key TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            provider TEXT,
            model TEXT,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cache_kind_expires_at ON cache_entries (kind, expires_at)"
    )


def _get_connection() -> sqlite3.Connection:
    """Get a database connection for cache operations."""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path, timeout=20.0)


def get_cache(cache_key: str) -> Union[Dict[str, Any], List[Any], None]:
    """Retrieve an entry from the cache, if it exists and is not expired."""
    try:
        with _get_connection() as conn:
            _ensure_cache_table(conn)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT payload_json, expires_at
                FROM cache_entries
                WHERE cache_key = ?
                """,
                (cache_key,),
            )
            row = cur.fetchone()

            if not row:
                return None

            payload_json, expires_at_str = row

            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if expires_at < datetime.now(timezone.utc):
                        return None
                except ValueError:
                    logger.warning(
                        f"Invalid expires_at format in cache for key {cache_key}: {expires_at_str}"
                    )
                    # If we can't parse expiration, assume it's expired to be safe
                    return None

            try:
                return cast(Union[Dict[str, Any], List[Any], None], json.loads(payload_json))
            except json.JSONDecodeError as e:
                logger.warning(f"Corrupted JSON in cache for key {cache_key}: {e}")
                return None
    except sqlite3.OperationalError as e:
        # Expected if the database or table hasn't been created yet
        logger.debug(f"Cache table might not exist yet: {e}")
        return None
    except Exception as e:
        logger.warning(f"Failed to read from cache: {e}")
        return None


def set_cache(
    cache_key: str,
    kind: str,
    provider: str,
    model: str,
    payload: Any,
    ttl_days: int,
) -> None:
    """Store an entry in the cache."""
    try:
        payload_json = _deterministic_json_dumps(payload)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=ttl_days)

        with _get_connection() as conn:
            _ensure_cache_table(conn)
            cur = conn.cursor()
            cur.execute("DELETE FROM cache_entries WHERE expires_at < ?", (now.isoformat(),))
            cur.execute(
                """
                INSERT INTO cache_entries
                (cache_key, kind, provider, model, payload_json, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    created_at=excluded.created_at,
                    expires_at=excluded.expires_at
                """,
                (
                    cache_key,
                    kind,
                    provider,
                    model,
                    payload_json,
                    now.isoformat(),
                    expires_at.isoformat(),
                ),
            )
            conn.commit()
    except sqlite3.OperationalError as e:
        # Table probably hasn't been created yet
        logger.debug(f"Failed to write to cache, table might not exist yet: {e}")
    except Exception as e:
        logger.warning(f"Failed to write to cache: {e}")
