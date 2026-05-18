import logging
import os
import sqlite3
from typing import Any

import pandas as pd

from backend.config import settings
from backend.utils.credibility import score_source
from backend.utils.migrations import run_migrations
from backend.utils.schemas import TokenUsage

logger = logging.getLogger(__name__)


def get_db_path() -> str:
    return os.path.abspath(settings.db_path)


_CURRENT_RUN_ID: int | None = None
_CURRENT_RUN_DB_PATH: str | None = None
SOURCES_FIELD_NAME = "Sources"


def create_run(input_file: str, output_file: str, model_name: str, web_search_provider: str) -> int:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO runs (input_file, output_file, model_name, web_search_provider)
            VALUES (?, ?, ?, ?)
            """,
            (input_file, output_file, model_name, web_search_provider),
        )
        run_id = cur.lastrowid
        conn.commit()
        if run_id is None:
            raise RuntimeError("Failed to create run.")
        return run_id
    finally:
        conn.close()


def init_db(fields: list[str], create_default_run: bool = True) -> None:
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        run_migrations(conn, settings.column_name, fields)
        conn.commit()

        if create_default_run:
            # Create or fetch a run for this session
            global _CURRENT_RUN_DB_PATH, _CURRENT_RUN_ID
            current_run_exists = False
            if _CURRENT_RUN_ID is not None and _CURRENT_RUN_DB_PATH == db_path:
                current_run_exists = (
                    conn.execute("SELECT 1 FROM runs WHERE id = ?", (_CURRENT_RUN_ID,)).fetchone()
                    is not None
                )

            if not current_run_exists:
                _CURRENT_RUN_ID = create_run(
                    settings.input_file,
                    settings.output_file,
                    settings.model_name,
                    settings.web_search_provider,
                )
                _CURRENT_RUN_DB_PATH = db_path

    finally:
        conn.close()
    logger.info(f"Database initialized at {db_path} (create_default_run={create_default_run})")


def get_all_existing_ids() -> set[str]:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT identifier_value FROM items
            WHERE identifier_column = ?
            """,
            (settings.column_name,),
        )
        return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


def prepare_row_data(
    item_id: str, data: dict[str, Any], output_fields: list[str]
) -> tuple[str, ...]:
    """Prepare a row of data for database insertion."""
    return (
        item_id,
        *[data.get(f, "Not found") for f in output_fields if f != settings.column_name],
    )


def save_single_item(
    item_id: str,
    data: dict[str, Any],
    output_fields: list[str],
    run_id: int | None = None,
    confidence: dict[str, float | None] | None = None,
    token_usage: TokenUsage | None = None,
) -> None:
    """Initialize the database and save a single item's data."""
    init_db(output_fields, create_default_run=(run_id is None))
    row_data = prepare_row_data(item_id, data, output_fields)
    conf_list = [confidence] if confidence is not None else None
    usage_list = [token_usage] if token_usage is not None else None
    save_results_bulk(
        [row_data],
        output_fields,
        run_id=run_id,
        confidence_list=conf_list,
        token_usage_list=usage_list,
    )


def determine_review_status(field_value: str | None, confidence: float | None) -> str:
    if not settings.review_enabled:
        return "auto_accepted"
    if field_value is None or field_value.strip() == "" or field_value == "Not found":
        return "needs_review"
    if confidence is None:
        return "needs_review"
    if confidence < settings.review_confidence_threshold:
        return "needs_review"
    return "auto_accepted"


def save_results_bulk(
    data_list: list[tuple[str, ...]],
    fields: list[str],
    run_id: int | None = None,
    confidence_list: list[dict[str, float | None]] | None = None,
    token_usage_list: list[TokenUsage] | None = None,
) -> None:
    if not data_list:
        return

    db_path = get_db_path()

    active_run_id = run_id
    if active_run_id is None:
        if _CURRENT_RUN_ID is None or _CURRENT_RUN_DB_PATH != db_path:
            raise RuntimeError(
                "save_results_bulk called before init_db for the current database path; "
                "_CURRENT_RUN_ID is not set and run_id was not explicitly passed."
            )
        active_run_id = _CURRENT_RUN_ID

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    all_fields = [settings.column_name] + [f for f in fields if f != settings.column_name]

    for row_data in data_list:
        if len(row_data) < len(all_fields):
            raise ValueError(
                f"Row data length ({len(row_data)}) is less than fields length ({len(all_fields)})."
            )  # noqa: E501

    try:
        for row_index, row_data in enumerate(data_list):
            item_id = row_data[0]

            # Try to insert item (or ignore if it already exists to maintain idempotency)
            try:
                cur.execute(
                    """
                    INSERT INTO items (run_id, identifier_column, identifier_value)
                    VALUES (?, ?, ?)
                    """,
                    (active_run_id, settings.column_name, item_id),
                )
                db_item_id = cur.lastrowid
            except sqlite3.IntegrityError:
                # If item already exists, we skip inserting new fields/sources for it
                # to mirror INSERT OR IGNORE behavior
                continue

            if token_usage_list is not None and row_index < len(token_usage_list):
                usage = token_usage_list[row_index]
                cur.execute(
                    """
                    UPDATE items
                    SET prompt_tokens = ?,
                        completion_tokens = ?,
                        llm_requests = ?,
                        estimated_cost_usd = ?
                    WHERE id = ?
                    """,
                    (
                        usage.prompt_tokens,
                        usage.completion_tokens,
                        usage.effective_llm_requests,
                        usage.estimated_cost_usd,
                        db_item_id,
                    ),
                )

            for i, field_name in enumerate(all_fields):
                if i == 0:
                    continue  # Skip item_id itself

                val = row_data[i]
                field_value = val if val is not None else None

                if field_name == SOURCES_FIELD_NAME:
                    if field_value is not None:
                        urls = [u.strip() for u in field_value.split("\n") if u.strip()]
                        for url in urls:
                            cur.execute(
                                """
                                INSERT INTO item_sources
                                    (item_id, title, url, snippet, provider, credibility_score)
                                VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (db_item_id, "", url, "", "legacy", score_source(url)),
                            )
                else:
                    conf_val = None
                    if confidence_list is not None and row_index < len(confidence_list):
                        if confidence_list[row_index]:
                            conf_val = confidence_list[row_index].get(field_name)

                    review_status = determine_review_status(field_value, conf_val)
                    cur.execute(
                        """
                        INSERT INTO item_fields (
                            item_id, field_name, field_value, confidence,
                            original_value, review_status, reviewed_at, reviewer_note
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            db_item_id,
                            field_name,
                            field_value,
                            conf_val,
                            field_value,
                            review_status,
                            None,
                            None,
                        ),
                    )

        conn.commit()
        logger.info(f"Saved {len(data_list)} items to database")
    except Exception as e:
        logger.error(f"Error saving to database: {e}")
        raise
    finally:
        conn.close()


def fetch_all(run_id: int | None = None) -> pd.DataFrame | None:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        # Fetch items
        if run_id is not None:
            items_df = pd.read_sql_query(
                "SELECT id, identifier_value FROM items WHERE run_id = ?", conn, params=(run_id,)
            )
        else:
            items_df = pd.read_sql_query("SELECT id, identifier_value FROM items", conn)
        if items_df.empty:
            return pd.DataFrame(columns=[settings.column_name])

        items_df = items_df.rename(columns={"identifier_value": settings.column_name})

        # Fetch fields
        if settings.review_enabled:
            field_value_col = (
                "CASE WHEN review_status = 'needs_review' "
                "THEN NULL ELSE field_value END AS field_value"
            )
        else:
            field_value_col = "field_value"

        if run_id is not None:
            fields_df = pd.read_sql_query(
                f"SELECT item_id, field_name, {field_value_col} "
                "FROM item_fields "
                "WHERE item_id IN (SELECT id FROM items WHERE run_id = ?)",
                conn,
                params=(run_id,),
            )
        else:
            fields_df = pd.read_sql_query(
                f"SELECT item_id, field_name, {field_value_col} FROM item_fields",
                conn,
            )

        if not fields_df.empty:
            pivoted = fields_df.pivot(
                index="item_id", columns="field_name", values="field_value"
            ).reset_index()  # noqa: E501
            # Merge items and fields
            merged = items_df.merge(pivoted, left_on="id", right_on="item_id", how="left")
            merged = merged.drop(columns=["item_id"])
        else:
            merged = items_df.copy()

        # Fetch sources
        if run_id is not None:
            sources_df = pd.read_sql_query(
                "SELECT item_id, url FROM item_sources "
                "WHERE item_id IN (SELECT id FROM items WHERE run_id = ?)",
                conn,
                params=(run_id,),
            )
        else:
            sources_df = pd.read_sql_query("SELECT item_id, url FROM item_sources", conn)
        if not sources_df.empty:
            # Group by item_id and join URLs with newline
            sources_grouped = (
                sources_df.groupby("item_id")["url"]
                .apply(lambda urls: "\n".join(dict.fromkeys(urls)))
                .reset_index()
            )  # noqa: E501
            sources_grouped = sources_grouped.rename(columns={"url": SOURCES_FIELD_NAME})

            # Merge sources
            merged = merged.merge(sources_grouped, left_on="id", right_on="item_id", how="left")
            merged = merged.drop(columns=["item_id"])
        else:
            merged[SOURCES_FIELD_NAME] = None

        # Ensure 'Sources' column exists if there were no sources found at all but we have fields
        if SOURCES_FIELD_NAME not in merged.columns:
            merged[SOURCES_FIELD_NAME] = None

        merged = merged.drop(columns=["id"])

        # Ensure column_name is the first column
        cols = [settings.column_name] + [c for c in merged.columns if c != settings.column_name]
        merged = merged[cols]

        return merged

    except Exception as e:
        logger.error(f"Error fetching from database: {e}")
        return None
    finally:
        conn.close()


def fetch_review_queue(
    status: str = "needs_review",
    limit: int = 100,
    offset: int = 0,
    job_id: str | None = None,
) -> list[dict[str, Any]]:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        query = """
            SELECT
                f.id AS field_id,
                f.item_id AS item_id,
                i.identifier_column AS identifier_column,
                i.identifier_value AS identifier_value,
                f.field_name AS field_name,
                f.field_value AS field_value,
                f.original_value AS original_value,
                f.confidence AS confidence,
                f.review_status AS review_status,
                f.reviewed_at AS reviewed_at,
                f.reviewer_note AS reviewer_note,
                j.job_id AS job_id
            FROM item_fields f
            JOIN items i ON f.item_id = i.id
            JOIN runs r ON i.run_id = r.id
            LEFT JOIN jobs j ON j.run_id = r.id
        """

        params: list[Any] = []
        if job_id is not None:
            query += " WHERE f.review_status = ? AND j.job_id = ?"
            params.extend([status, job_id])
        else:
            query += " WHERE f.review_status = ?"
            params.append(status)

        query += " ORDER BY f.id ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = cur.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_field_review(
    field_id: int,
    status: str,
    field_value: str | None = None,
    reviewer_note: str | None = None,
) -> dict[str, Any] | None:
    allowed_statuses = {"approved", "corrected", "rejected"}
    if status not in allowed_statuses:
        raise ValueError(f"Invalid review status: {status}")

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        # Fetch current record
        current = cur.execute(
            "SELECT id, field_value, review_status FROM item_fields WHERE id = ?",
            (field_id,),
        ).fetchone()
        if not current:
            return None

        # Determine updates
        if status == "approved":
            final_value = current["field_value"]
        elif status == "corrected":
            if field_value is None or field_value.strip() == "":
                raise ValueError("Corrected status requires a non-empty value")
            final_value = field_value
        elif status == "rejected":
            final_value = None
        else:
            final_value = current["field_value"]

        cur.execute(
            """
            UPDATE item_fields
            SET field_value = ?,
                review_status = ?,
                reviewed_at = CURRENT_TIMESTAMP,
                reviewer_note = ?
            WHERE id = ?
            """,
            (final_value, status, reviewer_note, field_id),
        )
        conn.commit()

        updated = cur.execute(
            """
            SELECT
                f.id AS field_id,
                f.item_id AS item_id,
                i.identifier_column AS identifier_column,
                i.identifier_value AS identifier_value,
                f.field_name AS field_name,
                f.field_value AS field_value,
                f.original_value AS original_value,
                f.confidence AS confidence,
                f.review_status AS review_status,
                f.reviewed_at AS reviewed_at,
                f.reviewer_note AS reviewer_note,
                j.job_id AS job_id
            FROM item_fields f
            JOIN items i ON f.item_id = i.id
            JOIN runs r ON i.run_id = r.id
            LEFT JOIN jobs j ON j.run_id = r.id
            WHERE f.id = ?
            """,
            (field_id,),
        ).fetchone()

        return dict(updated) if updated else None
    finally:
        conn.close()


def get_review_summary(job_id: str | None = None) -> dict[str, int]:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()

        query = """
            SELECT f.review_status, COUNT(*)
            FROM item_fields f
            JOIN items i ON f.item_id = i.id
            JOIN runs r ON i.run_id = r.id
        """
        params = []
        if job_id is not None:
            query += " JOIN jobs j ON j.run_id = r.id"
            query += " WHERE j.job_id = ?"
            params.append(job_id)

        query += " GROUP BY f.review_status"

        rows = cur.execute(query, params).fetchall()

        summary = {
            "needs_review": 0,
            "auto_accepted": 0,
            "approved": 0,
            "corrected": 0,
            "rejected": 0,
        }
        for status, count in rows:
            if status in summary:
                summary[status] = count

        return summary
    finally:
        conn.close()
