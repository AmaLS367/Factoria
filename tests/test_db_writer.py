import sqlite3
from pathlib import Path

import pytest
from utils import db_writer

from backend.utils.schemas import TokenUsage


@pytest.fixture
def mock_db_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "database.sqlite"

    mock_settings = type(
        "MockSettings",
        (),
        {
            "column_name": "Part Number",
            "input_file": "input.xlsx",
            "output_file": "output.xlsx",
            "model_name": "mock-model",
            "web_search_provider": "mock-provider",
            "db_path": str(db_path),
            "review_enabled": True,
            "review_confidence_threshold": 0.6,
        },
    )()

    monkeypatch.setattr(db_writer, "settings", mock_settings)

    db_writer._CURRENT_RUN_ID = None
    db_writer._CURRENT_RUN_DB_PATH = None

    return db_path


def test_migration_converts_legacy_results_to_normalized_tables(mock_db_writer: Path) -> None:
    # Set up old results table
    conn = sqlite3.connect(mock_db_writer)
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
            ("OLD-123", "Old Widget", "http://old.com\nhttp://old2.com\nhttp://old.com"),
        )
        conn.commit()
    finally:
        conn.close()

    db_writer.init_db(["Name", "Sources"])
    db_writer.save_results_bulk(
        [("ABC-123", "Widget", "https://example.com")],
        ["Name", "Sources"],
    )

    df = db_writer.fetch_all()
    assert df is not None
    assert len(df) == 2

    # Assert expected columns are present
    assert list(df.columns) == ["Part Number", "Name", "Sources"]

    old_row = df[df["Part Number"] == "OLD-123"].iloc[0]
    assert old_row["Name"] == "Old Widget"
    # Deduplication check
    assert old_row["Sources"] == "http://old.com\nhttp://old2.com"

    new_row = df[df["Part Number"] == "ABC-123"].iloc[0]
    assert new_row["Name"] == "Widget"
    assert new_row["Sources"] == "https://example.com"

    # Check existing IDs
    existing_ids = db_writer.get_all_existing_ids()
    assert "OLD-123" in existing_ids
    assert "ABC-123" in existing_ids
    assert "NO-123" not in existing_ids

    # Normalized tables check
    conn = sqlite3.connect(mock_db_writer)
    try:
        results_exists = (
            conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='results'"
            ).fetchone()
            is not None
        )  # noqa: E501
        assert not results_exists

        legacy_exists = (
            conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='legacy_results'"
            ).fetchone()
            is not None
        )  # noqa: E501
        assert legacy_exists

        items_count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        assert items_count == 2

        fields_count = conn.execute("SELECT COUNT(*) FROM item_fields").fetchone()[0]
        assert fields_count == 2  # One name per item

        sources_count = conn.execute("SELECT COUNT(*) FROM item_sources").fetchone()[0]
        assert sources_count == 3  # 2 for old (deduplicated), 1 for new
    finally:
        conn.close()


def test_init_db_records_applied_schema_migrations(mock_db_writer: Path) -> None:
    db_writer.init_db(["Name", "Sources"])
    db_writer.init_db(["Name", "Sources"])

    conn = sqlite3.connect(mock_db_writer)
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
        (4, "create_jobs_table"),
        (5, "create_cache_table"),
        (6, "add_job_import_config"),
        (7, "add_source_credibility_score"),
        (8, "add_job_template_fields"),
        (9, "add_job_token_accounting"),
        (10, "add_item_token_accounting"),
        (11, "add_human_review_fields"),
    ]
    assert migration_count == len(migration_rows)


def test_token_accounting_columns_exist_with_zero_defaults(mock_db_writer: Path) -> None:
    db_writer.init_db(["Name"])
    db_writer.save_results_bulk([("A", "Apple")], ["Name"])

    conn = sqlite3.connect(mock_db_writer)
    conn.row_factory = sqlite3.Row
    try:
        job_columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
        item_columns = {row["name"] for row in conn.execute("PRAGMA table_info(items)").fetchall()}
        item = conn.execute(
            """
            SELECT prompt_tokens, completion_tokens, llm_requests, estimated_cost_usd
            FROM items WHERE identifier_value = 'A'
            """
        ).fetchone()
    finally:
        conn.close()

    assert {
        "total_prompt_tokens",
        "total_completion_tokens",
        "total_llm_requests",
        "estimated_cost_usd",
    }.issubset(job_columns)
    assert {
        "prompt_tokens",
        "completion_tokens",
        "llm_requests",
        "estimated_cost_usd",
    }.issubset(item_columns)
    assert dict(item) == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "llm_requests": 0,
        "estimated_cost_usd": 0.0,
    }


def test_save_results_bulk_idempotency(mock_db_writer: Path) -> None:
    db_writer.init_db(["Name"])

    db_writer.save_results_bulk([("A", "Apple")], ["Name"])
    db_writer.save_results_bulk([("A", "Apple2"), ("B", "Banana")], ["Name"])

    df = db_writer.fetch_all()
    assert df is not None
    assert len(df) == 2
    assert df[df["Part Number"] == "A"].iloc[0]["Name"] == "Apple"  # First save should stick
    assert df[df["Part Number"] == "B"].iloc[0]["Name"] == "Banana"


def test_fetch_all_empty(mock_db_writer: Path) -> None:
    db_writer.init_db(["Name"])

    df = db_writer.fetch_all()
    assert df is not None
    assert df.empty


def test_save_results_bulk_raises_runtime_error_before_init_db(mock_db_writer: Path) -> None:
    with pytest.raises(RuntimeError, match="save_results_bulk called before init_db"):
        db_writer.save_results_bulk([("A", "Apple")], ["Name"])


def test_save_results_bulk_raises_value_error_for_short_row(mock_db_writer: Path) -> None:
    db_writer.init_db(["Name", "Sources"])
    with pytest.raises(ValueError, match="Row data length"):
        # We need (Item ID, Name, Sources) but only provide (Item ID, Name)
        db_writer.save_results_bulk([("A", "Apple")], ["Name", "Sources"])


def test_save_results_bulk_stores_none_as_null(mock_db_writer: Path) -> None:
    db_writer.init_db(["Name", "Description"])
    # First field is item_id, second is Name, third is Description
    db_writer.save_results_bulk([("A", None, "A Description")], ["Name", "Description"])

    conn = sqlite3.connect(mock_db_writer)
    try:
        fields = conn.execute("SELECT field_name, field_value FROM item_fields").fetchall()
        assert set(fields) == {("Name", None), ("Description", "A Description")}
    finally:
        conn.close()


def test_switching_db_path_creates_run_for_new_database(
    mock_db_writer: Path, tmp_path: Path
) -> None:
    first_db_path = mock_db_writer
    second_db_path = tmp_path / "second.sqlite"

    db_writer.init_db(["Name"])
    db_writer.save_results_bulk([("A", "Apple")], ["Name"])

    db_writer.settings.db_path = str(second_db_path)
    db_writer.init_db(["Name"])
    db_writer.save_results_bulk([("B", "Banana")], ["Name"])

    for db_path, expected_item in [(first_db_path, "A"), (second_db_path, "B")]:
        conn = sqlite3.connect(db_path)
        try:
            runs_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            item_values = conn.execute("SELECT identifier_value FROM items").fetchall()
        finally:
            conn.close()

        assert runs_count >= 1
        assert item_values == [(expected_item,)]


def test_save_results_bulk_rejects_changed_db_path_without_init(
    mock_db_writer: Path, tmp_path: Path
) -> None:
    db_writer.init_db(["Name"])
    db_writer.settings.db_path = str(tmp_path / "changed.sqlite")

    with pytest.raises(RuntimeError, match="current database path"):
        db_writer.save_results_bulk([("A", "Apple")], ["Name"])


def test_migration_is_safe_if_legacy_results_exists(mock_db_writer: Path) -> None:
    conn = sqlite3.connect(mock_db_writer)
    try:
        conn.execute(
            'CREATE TABLE legacy_results (id INTEGER PRIMARY KEY, "Part Number" TEXT UNIQUE)'
        )  # noqa: E501
        conn.execute("INSERT INTO legacy_results (\"Part Number\") VALUES ('OLD-1')")
        conn.commit()
    finally:
        conn.close()

    db_writer.init_db(["Name"])
    df = db_writer.fetch_all()
    assert df is not None
    assert len(df) == 1
    assert df.iloc[0]["Part Number"] == "OLD-1"


def test_repeated_migration_does_not_duplicate_legacy_data(mock_db_writer: Path) -> None:
    conn = sqlite3.connect(mock_db_writer)
    try:
        conn.execute(
            'CREATE TABLE results (id INTEGER PRIMARY KEY, "Part Number" TEXT UNIQUE, "Name" TEXT)'
        )  # noqa: E501
        conn.execute("INSERT INTO results (\"Part Number\", \"Name\") VALUES ('OLD-1', 'A')")
        conn.commit()
    finally:
        conn.close()

    # Apply migration 1
    db_writer.init_db(["Name"])

    # Check items count
    conn = sqlite3.connect(mock_db_writer)
    try:
        items_count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        assert items_count == 1

        # Reset schema_migrations manually to simulate repeated execution of same migration
        conn.execute("DELETE FROM schema_migrations WHERE version=3")
        conn.execute("ALTER TABLE legacy_results RENAME TO results")
        conn.commit()
    finally:
        conn.close()

    # Re-apply migration
    db_writer.init_db(["Name"])

    # Check items count - should still be 1 due to duplicate safety logic
    conn = sqlite3.connect(mock_db_writer)
    try:
        items_count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        assert items_count == 1
    finally:
        conn.close()


def test_ensure_identifier_index_handles_error(
    mock_db_writer: Path, caplog: pytest.LogCaptureFixture
) -> None:
    import logging
    import sqlite3

    from backend.utils.migrations import ensure_identifier_index

    class MockCursor:
        def execute(self, query: str, parameters: tuple[str, ...] = ()) -> None:
            raise sqlite3.Error("Mock error")

    from typing import cast

    cur = cast(sqlite3.Cursor, MockCursor())

    with caplog.at_level(logging.WARNING):
        # Should not raise exception, just log a warning
        ensure_identifier_index(cur, "mock_column")

    assert "Could not create unique index for mock_column" in caplog.text
    assert "Mock error" in caplog.text


def test_run_isolation(mock_db_writer: Path) -> None:
    db_writer.init_db(["Name", "Sources"], create_default_run=False)

    run_1 = db_writer.create_run("in1.xlsx", "out1.xlsx", "mock-model", "mock-provider")
    run_2 = db_writer.create_run("in2.xlsx", "out2.xlsx", "mock-model", "mock-provider")

    # Save to run 1
    db_writer.save_results_bulk([("A", "Apple", "Apple.com")], ["Name", "Sources"], run_id=run_1)

    # Save to run 2
    db_writer.save_results_bulk([("B", "Banana", "Banana.com")], ["Name", "Sources"], run_id=run_2)

    # Fetch run 1
    df1 = db_writer.fetch_all(run_id=run_1)
    assert df1 is not None
    assert len(df1) == 1
    assert df1.iloc[0]["Part Number"] == "A"
    assert df1.iloc[0]["Name"] == "Apple"

    # Fetch run 2
    df2 = db_writer.fetch_all(run_id=run_2)
    assert df2 is not None
    assert len(df2) == 1
    assert df2.iloc[0]["Part Number"] == "B"
    assert df2.iloc[0]["Name"] == "Banana"

    # Fetch all (no run_id filter)
    df_all = db_writer.fetch_all()
    assert df_all is not None
    assert len(df_all) == 2


def test_save_results_bulk_with_confidence(mock_db_writer: Path) -> None:
    db_writer.init_db(["Name", "Color"])
    data_list = [("A", "Apple", "Red"), ("B", "Banana", "Yellow")]
    conf_list = [{"Name": 0.9, "Color": 0.8}, {"Name": 1.0, "Color": 0.5}]

    db_writer.save_results_bulk(data_list, ["Name", "Color"], confidence_list=conf_list)

    conn = sqlite3.connect(mock_db_writer)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT item_id, field_name, field_value, confidence
FROM item_fields ORDER BY item_id, field_name"""
        ).fetchall()

        results = [dict(row) for row in rows]

        # Item 1 (A)
        assert results[0]["field_name"] == "Color"
        assert results[0]["confidence"] == 0.8
        assert results[1]["field_name"] == "Name"
        assert results[1]["confidence"] == 0.9

        # Item 2 (B)
        assert results[2]["field_name"] == "Color"
        assert results[2]["confidence"] == 0.5
        assert results[3]["field_name"] == "Name"
        assert results[3]["confidence"] == 1.0
    finally:
        conn.close()


def test_save_results_bulk_stores_token_usage(mock_db_writer: Path) -> None:
    db_writer.init_db(["Name"])

    db_writer.save_results_bulk(
        [("A", "Apple")],
        ["Name"],
        token_usage_list=[
            TokenUsage(
                prompt_tokens=100,
                completion_tokens=25,
                total_tokens=125,
                estimated_cost_usd=0.00125,
            )
        ],
    )

    conn = sqlite3.connect(mock_db_writer)
    conn.row_factory = sqlite3.Row
    try:
        item = conn.execute(
            """
            SELECT prompt_tokens, completion_tokens, llm_requests, estimated_cost_usd
            FROM items WHERE identifier_value = 'A'
            """
        ).fetchone()
    finally:
        conn.close()

    assert dict(item) == {
        "prompt_tokens": 100,
        "completion_tokens": 25,
        "llm_requests": 1,
        "estimated_cost_usd": 0.00125,
    }
