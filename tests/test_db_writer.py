import sqlite3
from pathlib import Path
from typing import Any, cast

import pytest
from utils import db_writer


def test_init_db_adds_missing_columns_to_existing_results_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Set up old results table
    db_module = cast(Any, db_writer)
    db_path = tmp_path / "database.sqlite"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                "Part Number" TEXT UNIQUE,
                "Name" TEXT,
                "Sources" TEXT
            )
            """
        )
        # Insert a legacy row
        conn.execute(
            """
            INSERT INTO results ("Part Number", "Name", "Sources")
            VALUES (?, ?, ?)
            """,
            ("OLD-123", "Old Widget", "http://old.com\nhttp://old2.com")
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(db_writer, "DB_PATH", str(db_path))
    monkeypatch.setattr(db_module.settings, "column_name", "Part Number")

    # reset state
    db_writer._CURRENT_RUN_ID = None

    db_writer.init_db(["Name", "Sources"])
    db_writer.save_results_bulk(
        [("ABC-123", "Widget", "https://example.com")],
        ["Name", "Sources"],
    )

    df = db_writer.fetch_all()
    assert df is not None
    assert len(df) == 2

    old_row = df[df["Part Number"] == "OLD-123"].iloc[0]
    assert old_row["Name"] == "Old Widget"
    assert "http://old.com\nhttp://old2.com" in old_row["Sources"]

    new_row = df[df["Part Number"] == "ABC-123"].iloc[0]
    assert new_row["Name"] == "Widget"
    assert new_row["Sources"] == "https://example.com"

    # Check detail exists
    assert db_writer.detail_exists("OLD-123")
    assert db_writer.detail_exists("ABC-123")
    assert not db_writer.detail_exists("NO-123")


def test_init_db_records_applied_schema_migrations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "database.sqlite"
    monkeypatch.setattr(db_writer, "DB_PATH", str(db_path))

    db_writer._CURRENT_RUN_ID = None
    db_writer.init_db(["Name", "Sources"])
    db_writer.init_db(["Name", "Sources"])

    conn = sqlite3.connect(db_path)
    try:
        migration_rows = conn.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        migration_count = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    finally:
        conn.close()

    assert migration_rows == [
        (1, "create_results_table"),
        (2, "sync_configured_result_columns"),
        (3, "create_normalized_tables"),
    ]
    assert migration_count == 3


def test_save_results_bulk_idempotency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "database.sqlite"
    monkeypatch.setattr(db_writer, "DB_PATH", str(db_path))
    monkeypatch.setattr(db_writer, "settings", type("MockSettings", (), {"column_name": "ID", "input_file": "input.xlsx", "output_file": "output.xlsx", "model_name": "mock", "web_search_provider": "mock", "db_path": db_path})())  # noqa: E501

    db_writer._CURRENT_RUN_ID = None
    db_writer.init_db(["Name"])

    db_writer.save_results_bulk([("A", "Apple")], ["Name"])
    db_writer.save_results_bulk([("A", "Apple2"), ("B", "Banana")], ["Name"])

    df = db_writer.fetch_all()
    assert df is not None
    assert len(df) == 2
    assert df[df["ID"] == "A"].iloc[0]["Name"] == "Apple"  # First save should stick
    assert df[df["ID"] == "B"].iloc[0]["Name"] == "Banana"


def test_fetch_all_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "database.sqlite"
    monkeypatch.setattr(db_writer, "DB_PATH", str(db_path))
    db_writer._CURRENT_RUN_ID = None
    db_writer.init_db(["Name"])

    df = db_writer.fetch_all()
    assert df is not None
    assert df.empty
