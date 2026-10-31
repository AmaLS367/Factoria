import argparse
import os
import sqlite3
from collections.abc import Sequence

from backend.utils.db_writer import get_db_path


def quote_identifier(identifier: str) -> str:
    """Safely quote a SQLite identifier.

    Args:
        identifier: Table, column, or index name.

    Returns:
        Double-quoted identifier with embedded quotes escaped.
    """
    return f'"{identifier.replace(chr(34), chr(34) + chr(34))}"'


def list_tables(conn: sqlite3.Connection) -> list[str]:
    """List non-internal tables in a SQLite database.

    Args:
        conn: Open SQLite connection.

    Returns:
        Table names ordered alphabetically.
    """
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [str(row[0]) for row in rows]


def list_columns(conn: sqlite3.Connection, table_name: str) -> list[tuple[str, str]]:
    """Inspect the columns in one SQLite table.

    Args:
        conn: Open SQLite connection.
        table_name: Name of the table to inspect.

    Returns:
        List of ``(column_name, declared_type)`` pairs.
    """
    rows = conn.execute(f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()
    return [(str(row[1]), str(row[2])) for row in rows]


def schema_lines(db_path: str | None = None, table_name: str | None = None) -> list[str]:
    """Build a human-readable schema listing.

    Args:
        db_path: Database file to inspect; defaults to the configured database.
        table_name: Optional table to inspect; defaults to all user tables.

    Returns:
        Lines describing the database status and its tables and columns.
    """
    resolved_path = os.path.abspath(db_path or get_db_path())
    lines = [f"Database: {resolved_path}"]

    if not os.path.exists(resolved_path):
        lines.append("Status: database file not found")
        return lines

    conn = sqlite3.connect(resolved_path)
    try:
        table_names = [table_name] if table_name else list_tables(conn)
        if not table_names:
            lines.append("Status: no tables found")
            return lines

        for current_table in table_names:
            columns = list_columns(conn, current_table)
            if not columns:
                lines.append(f"{current_table}: not found or has no columns")
                continue

            lines.append(f"{current_table}:")
            for column_name, column_type in columns:
                suffix = f" ({column_type})" if column_type else ""
                lines.append(f"  - {column_name}{suffix}")
    finally:
        conn.close()

    return lines


def show_columns(db_path: str | None = None, table_name: str | None = None) -> None:
    """Print the schema listing to standard output.

    Args:
        db_path: Database file to inspect; defaults to the configured database.
        table_name: Optional table to inspect; defaults to all user tables.
    """
    for line in schema_lines(db_path, table_name):
        print(line)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the schema inspection command.

    Returns:
        Configured ``argparse.ArgumentParser``.
    """
    parser = argparse.ArgumentParser(description="Inspect SQLite table columns.")
    parser.add_argument(
        "--db-path",
        default=None,
        help="SQLite database path. Defaults to settings.db_path.",
    )
    parser.add_argument(
        "--table",
        default=None,
        help="Optional table name to inspect. Defaults to all non-SQLite internal tables.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Parse options and print database schema details.

    Args:
        argv: Optional argument list; defaults to command-line arguments.
    """
    args = build_parser().parse_args(argv)
    show_columns(args.db_path, args.table)


if __name__ == "__main__":
    main()
