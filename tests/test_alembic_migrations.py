import sqlite3
from pathlib import Path

import pytest
from alembic import command

from backend.config import settings
from backend.db.alembic_runner import ensure_alembic_initialized, get_alembic_config


@pytest.fixture
def mock_settings_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "test_migrate.sqlite"

    # Mock the settings.db_path using monkeypatch
    monkeypatch.setattr(settings, "db_path", str(db_path))

    return db_path


def test_fresh_database_alembic_initialization(mock_settings_db: Path) -> None:
    """Test that a fresh database is fully initialized via Alembic to head version."""
    assert not mock_settings_db.exists()

    # Call ensure_alembic_initialized for a fresh database
    ensure_alembic_initialized("Part Number", ["Name", "Sources"])

    # Verify database file now exists
    assert mock_settings_db.exists()

    # Connect to database and verify schema integrity
    conn = sqlite3.connect(mock_settings_db)
    try:
        cur = conn.cursor()

        # Check alembic_version table exists and contains a version
        alembic_version = cur.execute("SELECT version_num FROM alembic_version").fetchone()
        assert alembic_version is not None
        assert len(alembic_version[0]) > 0

        # Check that normalized tables exist
        tables = [
            row[0]
            for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]
        assert "runs" in tables
        assert "items" in tables
        assert "item_fields" in tables
        assert "item_sources" in tables
        assert "jobs" in tables
        assert "cache_entries" in tables

        # Verify that the legacy schema_migrations table DOES NOT exist for fresh installations
        assert "schema_migrations" not in tables
    finally:
        conn.close()


def test_alembic_upgrade_0001_to_0002_scopes_index(
    mock_settings_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that upgrading from 0001 to 0002 correctly scopes uniqueness to run_id."""
    # Run the 0001 migration to create the old schema (tables + old index)
    config = get_alembic_config()
    command.upgrade(config, "0001")

    # Verify we are at 0001 and the old index was global
    conn = sqlite3.connect(mock_settings_db)
    try:
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        assert version == "0001"

        # Verify the old index exists
        indexes = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_items_identifier'"
            ).fetchall()
        ]
        assert len(indexes) == 1
    finally:
        conn.close()

    # Upgrade to head (0002)
    command.upgrade(config, "head")

    # Verify we are now at 0002
    conn = sqlite3.connect(mock_settings_db)
    try:
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        assert version == "0002"
    finally:
        conn.close()

    # Verify the new index works: same identifier allowed in different runs
    import backend.utils.db_writer as db_writer

    monkeypatch.setattr(db_writer, "settings", settings)

    db_writer.init_db(["Name"], create_default_run=False)
    run_1 = db_writer.create_run("in1.xlsx", "out1.xlsx", "model", "provider")
    run_2 = db_writer.create_run("in2.xlsx", "out2.xlsx", "model", "provider")

    db_writer.save_results_bulk([("ABC-123", "Run 1 Value")], ["Name"], run_id=run_1)
    db_writer.save_results_bulk([("ABC-123", "Run 2 Value")], ["Name"], run_id=run_2)

    conn = sqlite3.connect(mock_settings_db)
    try:
        items = conn.execute("SELECT identifier_value FROM items").fetchall()
        assert len(items) == 2
        assert all(row[0] == "ABC-123" for row in items)
    finally:
        conn.close()


def test_legacy_bridge_migration_flow(
    mock_settings_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that legacy databases are migrated and stamped as Alembic baseline '0001'."""
    assert not mock_settings_db.exists()

    # 1. Create a legacy results flat table schema
    conn = sqlite3.connect(mock_settings_db)
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
        conn.execute(
            """
            INSERT INTO results ("Part Number", "Name", "Sources")
            VALUES (?, ?, ?)
            """,
            ("LEGACY-1", "Legacy Item 1", "http://source1.com\nhttp://source2.com"),
        )
        conn.commit()
    finally:
        conn.close()

    # Ensure alembic_version is not there yet
    conn = sqlite3.connect(mock_settings_db)
    try:
        cur = conn.cursor()
        alembic_version_exists = (
            cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'"
            ).fetchone()
            is not None
        )
        assert not alembic_version_exists
    finally:
        conn.close()

    # 2. Trigger the initialization which should invoke the bridge
    ensure_alembic_initialized("Part Number", ["Name", "Sources"])

    # 3. Verify tables and migrated data
    conn = sqlite3.connect(mock_settings_db)
    try:
        cur = conn.cursor()

        # Check alembic_version table exists and contains a version
        alembic_version = cur.execute("SELECT version_num FROM alembic_version").fetchone()
        assert alembic_version is not None

        # Verify tables list
        tables = [
            row[0]
            for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]
        assert "runs" in tables
        assert "items" in tables
        assert "item_fields" in tables
        assert (
            "schema_migrations" in tables
        )  # The legacy schema migrations table should be preserved

        # Verify data migration was completed successfully
        items = cur.execute("SELECT identifier_value FROM items").fetchall()
        assert len(items) == 1
        assert items[0][0] == "LEGACY-1"

        # Verify fields migration
        fields = cur.execute(
            """
            SELECT field_name, field_value FROM item_fields
            JOIN items ON item_fields.item_id = items.id
            WHERE items.identifier_value = 'LEGACY-1'
            """
        ).fetchall()
        field_dict = {row[0]: row[1] for row in fields}
        assert field_dict["Name"] == "Legacy Item 1"

        # Verify sources migration
        sources = cur.execute(
            """
            SELECT url FROM item_sources
            JOIN items ON item_sources.item_id = items.id
            WHERE items.identifier_value = 'LEGACY-1'
            """
        ).fetchall()
        urls = {row[0] for row in sources}
        assert "http://source1.com" in urls
        assert "http://source2.com" in urls
    finally:
        conn.close()
