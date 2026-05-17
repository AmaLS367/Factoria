from pathlib import Path
from typing import Any, Generator
import pytest

from backend.config import settings
from backend.utils.cache import (
    _deterministic_json_dumps,
    _get_connection,
    get_cache,
    make_cache_key,
    set_cache,
)
from backend.utils.db_writer import init_db
from backend.utils.migrations import run_migrations


@pytest.fixture(autouse=True)
def setup_db(tmp_path: Path) -> Generator[None, None, None]:
    # Override settings path to avoid polluting actual test db
    original_db_path = settings.db_path
    settings.db_path = str(tmp_path / "test_db.sqlite")
    init_db(["field1"], create_default_run=False)

    # Ensure migrations are fully applied (including cache table)
    with _get_connection() as conn:
        run_migrations(conn, "field1", ["field1"])

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

    set_cache(key, "test", "prov", "mod", "hash", payload, 1)

    cached = get_cache(key)
    assert cached == payload


def test_expired_cache() -> None:
    payload = {"result": "success"}
    key = make_cache_key("test", "prov", "mod", payload)

    set_cache(key, "test", "prov", "mod", "hash", payload, -1)  # expired 1 day ago

    cached = get_cache(key)
    assert cached is None


def test_corrupted_cache() -> None:
    payload = {"result": "success"}
    key = make_cache_key("test", "prov", "mod", payload)

    set_cache(key, "test", "prov", "mod", "hash", payload, 1)

    # Corrupt the json directly in the db
    with _get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE cache_entries SET payload_json = '{corrupted' WHERE cache_key = ?", (key,)
        )
        conn.commit()

    cached = get_cache(key)
    assert cached is None
