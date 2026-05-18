import logging
import os
import sqlite3

from alembic import command
from alembic.config import Config

from backend.config import settings
from backend.utils.migrations import run_migrations

logger = logging.getLogger(__name__)


def get_alembic_config() -> Config:
    """Load Alembic configuration dynamically and set the database URL."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ini_path = os.path.join(base_dir, "alembic.ini")
    config = Config(ini_path)

    # Convert absolute backslashes to forward slashes for SQLite URL format
    db_path = settings.db_path
    abs_path = os.path.abspath(db_path).replace("\\", "/")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{abs_path}")
    return config


def run_alembic_migrations() -> None:
    """Run all pending Alembic migrations to upgrade the schema to head."""
    logger.info("Running Alembic migrations to head...")
    config = get_alembic_config()
    command.upgrade(config, "head")
    logger.info("Alembic migrations completed successfully.")


def ensure_alembic_initialized(identifier_column: str, fields: list[str]) -> None:
    """Ensure the database is initialized, bridging any legacy runner migrations.

    If the database file already exists, we check if there is an existing
    custom migration scheme. If so, we complete the custom migrations up to
    the final version 11, and then stamp the Alembic baseline '0001'.
    """
    db_path = settings.db_path
    db_exists = os.path.exists(db_path)

    # Ensure the directory exists
    db_dir = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(db_dir, exist_ok=True)

    if not db_exists:
        # Fresh database: let Alembic initialize it directly to head
        logger.info("Fresh database detected. Initializing via Alembic...")
        run_alembic_migrations()
        return

    # Connection to detect existing database state
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        # Check if schema_migrations table exists
        schema_migrations_exists = (
            cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            ).fetchone()
            is not None
        )

        # Check if alembic_version table exists
        alembic_version_exists = (
            cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'"
            ).fetchone()
            is not None
        )

        # Check if legacy results exists but without migration table
        legacy_results_exists = (
            cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND "
                "(name='results' OR name='legacy_results')"
            ).fetchone()
            is not None
        )

        # If there are legacy tables but no alembic version
        if (schema_migrations_exists or legacy_results_exists) and not alembic_version_exists:
            logger.info("Legacy database detected. Running legacy migrations bridge...")
            # Run the old custom migrations to the end (version 11)
            run_migrations(conn, identifier_column, fields)
            conn.commit()

            # Stamp Alembic to baseline '0001'
            logger.info("Stamping Alembic baseline version '0001'...")
            config = get_alembic_config()
            command.stamp(config, "0001")

            # Now run any future Alembic migrations that might be after '0001'
            run_alembic_migrations()
        elif not alembic_version_exists:
            # Brand new database file was touched/empty, just upgrade to head
            logger.info("Touched/empty database detected. Running Alembic migrations...")
            run_alembic_migrations()
        else:
            # Database is already under Alembic control, just run migrations
            run_alembic_migrations()
    finally:
        conn.close()
