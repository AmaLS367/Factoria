import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from backend.utils.check_columns import (
    build_parser,
    main,
    schema_lines,
    show_columns,
)


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


def test_schema_lines_no_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.sqlite"
    conn = sqlite3.connect(db_path)
    conn.close()

    output = schema_lines(str(db_path))
    assert any("no tables found" in line for line in output)


def test_schema_lines_unknown_table(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite"
    create_normalized_schema(db_path)

    output = schema_lines(str(db_path), table_name="nonexistent_table")
    assert any("nonexistent_table" in line and "not found" in line for line in output)


def test_show_columns_prints_schema(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db_path = tmp_path / "db.sqlite"
    create_normalized_schema(db_path)

    show_columns(str(db_path), "items")
    captured = capsys.readouterr()
    assert "items:" in captured.out
    assert "identifier_value (TEXT)" in captured.out


def test_build_parser_accepts_args() -> None:
    parser = build_parser()
    args = parser.parse_args(["--db-path", "x.sqlite", "--table", "items"])
    assert args.db_path == "x.sqlite"
    assert args.table == "items"


def test_main_runs_without_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db_path = tmp_path / "db.sqlite"
    create_normalized_schema(db_path)
    main(["--db-path", str(db_path), "--table", "items"])
    captured = capsys.readouterr()
    assert "items:" in captured.out
