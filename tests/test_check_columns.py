import sqlite3
import subprocess
import sys
from pathlib import Path

from backend.utils.check_columns import schema_lines


def create_normalized_schema(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE runs (id INTEGER PRIMARY KEY, status TEXT)")
        conn.execute(
            """
            CREATE TABLE items (
                id INTEGER PRIMARY KEY,
                run_id INTEGER,
                identifier_column TEXT,
                identifier_value TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE item_fields (
                id INTEGER PRIMARY KEY,
                item_id INTEGER,
                field_name TEXT,
                field_value TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE item_sources (
                id INTEGER PRIMARY KEY,
                item_id INTEGER,
                url TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def test_schema_lines_lists_normalized_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "database.sqlite"
    create_normalized_schema(db_path)

    output = "\n".join(schema_lines(str(db_path)))

    assert "items:" in output
    assert "identifier_value (TEXT)" in output
    assert "item_fields:" in output
    assert "field_value (TEXT)" in output
    assert "item_sources:" in output
    assert "url (TEXT)" in output


def test_schema_lines_handles_missing_database(tmp_path: Path) -> None:
    output = schema_lines(str(tmp_path / "missing.sqlite"))

    assert output[-1] == "Status: database file not found"


def test_check_columns_module_cli_outputs_ascii_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "database.sqlite"
    create_normalized_schema(db_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.utils.check_columns",
            "--db-path",
            str(db_path),
            "--table",
            "items",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "items:" in result.stdout
    assert "identifier_value (TEXT)" in result.stdout
