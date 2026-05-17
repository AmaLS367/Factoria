from pathlib import Path
from typing import Generator

import pytest

from backend.config import settings
from backend.utils.cache import (
    _deterministic_json_dumps,
    _ensure_cache_table,
    _get_connection,
    get_cache,
    make_cache_key,
    set_cache,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_path: Path) -> Generator[None, None, None]:
    # Override settings path to avoid polluting actual test db
    original_db_path = settings.db_path
    settings.db_path = str(tmp_path / "test_db.sqlite")
    yield
    settings.db_path = original_db_path


def test_deterministic_json_dumps() -> None:
    d1 = {"b": 2, "a": 1}
    d2 = {"a": 1, "b": 2}
    assert _deterministic_json_dumps(d1) == _deterministic_json_dumps(d2)
    assert " " not in _deterministic_json_dumps(d1)


def test_make_cache_key() -> None:
    payload1 = {"b": 2, "a": 1}
    payload2 = {"a": 1, "b": 2}
    payload3 = {"a": 2, "b": 2}

    key1 = make_cache_key("test", "prov", "mod", payload1)
    key2 = make_cache_key("test", "prov", "mod", payload2)
    key3 = make_cache_key("test", "prov", "mod", payload3)

    assert key1 == key2
    assert key1 != key3


def test_set_and_get_cache() -> None:
    payload = {"result": "success"}
    key = make_cache_key("test", "prov", "mod", payload)

    set_cache(key, "test", "prov", "mod", payload, 10)

    cached = get_cache(key)
    assert cached == payload


def test_expired_cache() -> None:
    payload = {"result": "success"}
    key = make_cache_key("test", "prov", "mod", payload)

    set_cache(key, "test", "prov", "mod", payload, -1)  # expired 1 day ago

    cached = get_cache(key)
    assert cached is None


def test_corrupted_cache() -> None:
    payload = {"result": "success"}
    key = make_cache_key("test", "prov", "mod", payload)

    set_cache(key, "test", "prov", "mod", payload, 1)

    # Corrupt the json directly in the db
    with _get_connection() as conn:
        _ensure_cache_table(conn)
        cur = conn.cursor()
        cur.execute(
            "UPDATE cache_entries SET payload_json = '{corrupted' WHERE cache_key = ?", (key,)
        )
        conn.commit()

    cached = get_cache(key)
    assert cached is None


def test_cache_cleanup() -> None:
    payload1 = {"result": "expired"}
    key1 = make_cache_key("test", "prov", "mod", payload1)

    payload2 = {"result": "valid"}
    key2 = make_cache_key("test", "prov", "mod", payload2)

    # Insert an expired entry
    set_cache(key1, "test", "prov", "mod", payload1, -1)

    # Insert a valid entry which should trigger cleanup
    set_cache(key2, "test", "prov", "mod", payload2, 1)

    with _get_connection() as conn:
        _ensure_cache_table(conn)
        cur = conn.cursor()
        cur.execute("SELECT cache_key FROM cache_entries")
        keys = {row[0] for row in cur.fetchall()}

    # The expired key should have been deleted during the write of key2
    assert key1 not in keys
    assert key2 in keys

def test_cache_initializes_missing_directory(tmp_path: Path) -> None:
    # Set db path to a directory that doesn't exist yet
    missing_dir = tmp_path / "missing"
    db_file = missing_dir / "cache.sqlite"

    settings.db_path = str(db_file)

    payload = {"status": "ok"}
    key = make_cache_key("test", "prov", "mod", payload)

    # Should create directory and table, then insert
    set_cache(key, "test", "prov", "mod", payload, 10)

    # Verify file exists
    assert db_file.exists()

    # Verify cache can be retrieved
    cached = get_cache(key)
    assert cached == payload
