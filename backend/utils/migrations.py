import logging
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MigrationContext:
    identifier_column: str
    fields: list[str]


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: Callable[[sqlite3.Cursor, MigrationContext], None]


def run_migrations(
    conn: sqlite3.Connection,
    identifier_column: str,
    fields: list[str],
) -> None:
    context = MigrationContext(identifier_column=identifier_column, fields=fields)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    ensure_migration_table(cur)

    applied_versions = {
        int(row[0])
        for row in cur.execute("SELECT version FROM schema_migrations").fetchall()
    }

    for migration in MIGRATIONS:
        if migration.version in applied_versions:
            continue
        migration.apply(cur, context)
        cur.execute(
            """
            INSERT INTO schema_migrations (version, name)
            VALUES (?, ?)
            """,
            (migration.version, migration.name),
        )
        logger.info("Applied database migration %s_%s", migration.version, migration.name)

    sync_configured_result_columns(cur, context)
    ensure_identifier_index(cur, context.identifier_column)


def ensure_migration_table(cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def create_results_table(cur: sqlite3.Cursor, context: MigrationContext) -> None:
    columns = [f"{quote_identifier(context.identifier_column)} TEXT UNIQUE"]
    for field in context.fields:
        if field != context.identifier_column:
            columns.append(f"{quote_identifier(field)} TEXT")

    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {', '.join(columns)}
        )
        """
    )


def sync_configured_result_columns(cur: sqlite3.Cursor, context: MigrationContext) -> None:
    existing_columns = {
        str(row[1])
        for row in cur.execute("PRAGMA table_info(results)").fetchall()
    }

    for field in dict.fromkeys([context.identifier_column, *context.fields]):
        if field == "id" or field in existing_columns:
            continue
        cur.execute(f"ALTER TABLE results ADD COLUMN {quote_identifier(field)} TEXT")
        existing_columns.add(field)
        logger.info("Added missing database column: %s", field)


def ensure_identifier_index(cur: sqlite3.Cursor, identifier_column: str) -> None:
    index_name = f"idx_results_{identifier_column}_unique"
    try:
        cur.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {quote_identifier(index_name)} "
            f"ON results ({quote_identifier(identifier_column)})"
        )
    except sqlite3.Error as exc:
        logger.warning("Could not create unique index for %s: %s", identifier_column, exc)


def quote_identifier(identifier: str) -> str:
    return f'"{identifier.replace(chr(34), chr(34) + chr(34))}"'


MIGRATIONS = [
    Migration(1, "create_results_table", create_results_table),
    Migration(2, "sync_configured_result_columns", sync_configured_result_columns),
]
