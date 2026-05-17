import logging
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SOURCES_FIELD_NAME = "Sources"


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
        int(row[0]) for row in cur.execute("SELECT version FROM schema_migrations").fetchall()
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

    # If the identifier column name is the same as one of the fields, or if one of the fields was 'id', we avoid dupes  # noqa: E501
    unique_columns = []
    seen = set()
    for col in columns:
        c = col.split(" ")[0].strip('"')
        if c.lower() == "id":
            # Skip if it conflicts with `id INTEGER PRIMARY KEY`
            continue
        if c not in seen:
            unique_columns.append(col)
            seen.add(c)

    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {", ".join(unique_columns)}
        )
        """
    )


def sync_configured_result_columns(cur: sqlite3.Cursor, context: MigrationContext) -> None:
    # Check if results exists first
    table_exists = (
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='results'").fetchone()
        is not None
    )

    if not table_exists:
        return

    existing_columns = {str(row[1]) for row in cur.execute("PRAGMA table_info(results)").fetchall()}

    for field in dict.fromkeys([context.identifier_column, *context.fields]):
        if field.lower() == "id" or field in existing_columns:
            continue
        cur.execute(f"ALTER TABLE results ADD COLUMN {quote_identifier(field)} TEXT")
        existing_columns.add(field)
        logger.info("Added missing database column: %s", field)

    ensure_identifier_index(cur, context.identifier_column)


def ensure_identifier_index(cur: sqlite3.Cursor, identifier_column: str) -> None:
    if identifier_column.lower() == "id":
        return
    index_name = f"idx_results_{identifier_column}_unique"
    try:
        cur.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {quote_identifier(index_name)} "
            f"ON results ({quote_identifier(identifier_column)})"
        )
    except sqlite3.Error as exc:
        logger.warning("Could not create unique index for %s: %s", identifier_column, exc)


def rename_legacy_table(cur: sqlite3.Cursor) -> bool:
    table_exists = (
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='results'").fetchone()
        is not None
    )

    legacy_exists = (
        cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='legacy_results'"
        ).fetchone()
        is not None
    )

    if table_exists and not legacy_exists:
        cur.execute("ALTER TABLE results RENAME TO legacy_results")
        return True

    return legacy_exists


def create_runs_table(cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            finished_at TEXT,
            status TEXT NOT NULL DEFAULT 'running',
            input_file TEXT,
            output_file TEXT,
            model_name TEXT,
            web_search_provider TEXT
        )
        """
    )


def create_items_table(cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            identifier_column TEXT NOT NULL,
            identifier_value TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'completed',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        )
        """
    )
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_items_identifier ON items (identifier_column, identifier_value)"  # noqa: E501
    )


def create_item_fields_table(cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS item_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            field_value TEXT,
            confidence REAL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
        """
    )
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_item_fields_item_id_name ON item_fields (item_id, field_name)"  # noqa: E501
    )


def create_item_sources_table(cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS item_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            title TEXT,
            url TEXT,
            snippet TEXT,
            provider TEXT,
            retrieved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
        """
    )


def create_normalized_tables(cur: sqlite3.Cursor, context: MigrationContext) -> None:
    should_migrate = rename_legacy_table(cur)

    create_runs_table(cur)
    create_items_table(cur)
    create_item_fields_table(cur)
    create_item_sources_table(cur)

    if should_migrate:
        _migrate_legacy_data(cur, context)


def _migrate_legacy_data(cur: sqlite3.Cursor, context: MigrationContext) -> None:
    # 1. Create or fetch a dummy run for legacy data
    cur.execute("SELECT id FROM runs WHERE status = 'legacy_migrated'")
    run_row = cur.fetchone()
    if run_row:
        run_id = run_row[0]
    else:
        cur.execute(
            """
            INSERT INTO runs (status, input_file, output_file, model_name, web_search_provider)
            VALUES ('legacy_migrated', 'legacy', 'legacy', 'legacy', 'legacy')
            """
        )
        run_id = cur.lastrowid

    # Get column names from legacy_results
    columns_info = cur.execute("PRAGMA table_info(legacy_results)").fetchall()
    columns = [col[1] for col in columns_info]

    id_col = context.identifier_column

    # If ID was the identifier_column but skipped in the results creation due to lowercase `id` matching  # noqa: E501
    if id_col not in columns and id_col.lower() == "id":
        id_col = "id"

    if id_col not in columns:
        raise RuntimeError(
            f"Identifier column '{id_col}' not found in legacy_results. Cannot migrate data."
        )  # noqa: E501

    fields = [c for c in columns if c not in ["id", id_col]]

    rows = cur.execute("SELECT * FROM legacy_results").fetchall()

    for row in rows:
        row_dict = dict(zip(columns, row, strict=False))
        identifier_value = row_dict.get(id_col)

        # Fallback to the original identifier if possible
        if identifier_value is None and len(columns) > 1:
            identifier_value = row_dict.get(columns[1])

        if not identifier_value:
            continue

        identifier_value = str(identifier_value)

        # 2. Insert item
        try:
            cur.execute(
                """
                INSERT INTO items (run_id, identifier_column, identifier_value)
                VALUES (?, ?, ?)
                """,
                (run_id, context.identifier_column, identifier_value),
            )
            item_id = cur.lastrowid
        except sqlite3.IntegrityError:
            cur.execute(
                "SELECT id FROM items WHERE identifier_column = ? AND identifier_value = ?",
                (context.identifier_column, identifier_value),
            )
            item_id = cur.fetchone()[0]

        # 3. Insert fields and sources
        for field in fields:
            val = row_dict.get(field)
            if val is None:
                continue
            val_str = str(val)

            if field == SOURCES_FIELD_NAME:
                urls = [u.strip() for u in val_str.split("\n") if u.strip()]
                for url in urls:
                    cur.execute(
                        "SELECT 1 FROM item_sources WHERE item_id = ? AND url = ?", (item_id, url)
                    )  # noqa: E501
                    if not cur.fetchone():
                        cur.execute(
                            """
                            INSERT INTO item_sources (item_id, title, url, snippet, provider)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (item_id, "", url, "", "legacy"),
                        )
            else:
                try:
                    cur.execute(
                        """
                        INSERT INTO item_fields (item_id, field_name, field_value)
                        VALUES (?, ?, ?)
                        """,
                        (item_id, field, val_str),
                    )
                except sqlite3.IntegrityError:
                    pass


def quote_identifier(identifier: str) -> str:
    return f'"{identifier.replace(chr(34), chr(34) + chr(34))}"'


MIGRATIONS = [
    Migration(1, "create_results_table", create_results_table),
    Migration(2, "sync_configured_result_columns", sync_configured_result_columns),
    Migration(3, "create_normalized_tables", create_normalized_tables),
]
