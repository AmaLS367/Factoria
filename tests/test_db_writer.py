import sqlite3
from pathlib import Path
from typing import Any, cast

import pytest
from utils import db_writer


def test_init_db_adds_missing_columns_to_existing_results_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_module = cast(Any, db_writer)
    db_path = tmp_path / "database.sqlite"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                "Item ID" TEXT UNIQUE,
                "Name" TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(db_writer, "DB_PATH", str(db_path))
    monkeypatch.setattr(db_module.settings, "column_name", "Part Number")

    db_writer.init_db(["Name", "Sources"])
    db_writer.save_results_bulk(
        [("ABC-123", "Widget", "https://example.com")],
        ["Name", "Sources"],
    )

    conn = sqlite3.connect(db_path)
    try:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(results)").fetchall()]
        row = conn.execute(
            'SELECT "Part Number", "Name", "Sources" FROM results WHERE "Part Number" = ?',
            ("ABC-123",),
        ).fetchone()
    finally:
        conn.close()

    assert "Part Number" in columns
    assert "Sources" in columns
    assert row == ("ABC-123", "Widget", "https://example.com")
