import logging
import os
import sqlite3

import pandas as pd
from config import settings

from utils.migrations import run_migrations

logger = logging.getLogger(__name__)

DB_PATH = os.path.abspath(settings.db_path)

_CURRENT_RUN_ID: int | None = None


def init_db(fields: list[str]) -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        run_migrations(conn, settings.column_name, fields)
        conn.commit()

        # Create or fetch a run for this session
        global _CURRENT_RUN_ID
        if _CURRENT_RUN_ID is None:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO runs (input_file, output_file, model_name, web_search_provider)
                VALUES (?, ?, ?, ?)
                """,
                (settings.input_file, settings.output_file, settings.model_name, settings.web_search_provider)  # noqa: E501
            )
            _CURRENT_RUN_ID = cur.lastrowid
            conn.commit()

    finally:
        conn.close()
    logger.info(f"Database initialized at {DB_PATH}")


def detail_exists(item_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1 FROM items
        WHERE identifier_column = ? AND identifier_value = ?
        """,
        (settings.column_name, item_id),
    )
    result = cur.fetchone()
    conn.close()
    return result is not None

def save_results_bulk(data_list: list[tuple[str, ...]], fields: list[str]) -> None:
    if not data_list:
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    all_fields = [settings.column_name] + [f for f in fields if f != settings.column_name]

    try:
        for row_data in data_list:
            item_id = row_data[0]

            # Try to insert item (or ignore if it already exists to maintain idempotency)
            try:
                cur.execute(
                    """
                    INSERT INTO items (run_id, identifier_column, identifier_value)
                    VALUES (?, ?, ?)
                    """,
                    (_CURRENT_RUN_ID, settings.column_name, item_id)
                )
                db_item_id = cur.lastrowid
            except sqlite3.IntegrityError:
                # If item already exists, we skip inserting new fields/sources for it
                # to mirror INSERT OR IGNORE behavior
                continue

            for i, field_name in enumerate(all_fields):
                if i == 0:
                    continue  # Skip item_id itself

                val = row_data[i]
                if val is None:
                    continue
                field_value = str(val)

                if field_name == "Sources":
                    urls = [u.strip() for u in field_value.split("\n") if u.strip()]
                    for url in urls:
                        cur.execute(
                            """
                            INSERT INTO item_sources (item_id, title, url, snippet, provider)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (db_item_id, "", url, "", "legacy")
                        )
                else:
                    cur.execute(
                        """
                        INSERT INTO item_fields (item_id, field_name, field_value)
                        VALUES (?, ?, ?)
                        """,
                        (db_item_id, field_name, field_value)
                    )

        conn.commit()
        logger.info(f"Saved {len(data_list)} items to database")
    except Exception as e:
        logger.error(f"Error saving to database: {e}")
    finally:
        conn.close()

def fetch_all() -> pd.DataFrame | None:
    conn = sqlite3.connect(DB_PATH)
    try:
        # Fetch items
        items_df = pd.read_sql_query("SELECT id, identifier_value FROM items", conn)
        if items_df.empty:
            return pd.DataFrame(columns=[settings.column_name])

        items_df = items_df.rename(columns={"identifier_value": settings.column_name})

        # Fetch fields
        fields_df = pd.read_sql_query("SELECT item_id, field_name, field_value FROM item_fields", conn)  # noqa: E501

        if not fields_df.empty:
            pivoted = fields_df.pivot(index="item_id", columns="field_name", values="field_value").reset_index()  # noqa: E501
            # Merge items and fields
            merged = items_df.merge(pivoted, left_on="id", right_on="item_id", how="left")
            merged = merged.drop(columns=["item_id"])
        else:
            merged = items_df.copy()

        # Fetch sources
        sources_df = pd.read_sql_query("SELECT item_id, url FROM item_sources", conn)
        if not sources_df.empty:
            # Group by item_id and join URLs with newline
            sources_grouped = sources_df.groupby("item_id")["url"].apply(lambda urls: "\n".join(dict.fromkeys(urls))).reset_index()  # noqa: E501
            sources_grouped = sources_grouped.rename(columns={"url": "Sources"})

            # Merge sources
            merged = merged.merge(sources_grouped, left_on="id", right_on="item_id", how="left")
            merged = merged.drop(columns=["item_id"])
        else:
            merged["Sources"] = None

        # Ensure 'Sources' column exists if there were no sources found at all but we have fields
        if "Sources" not in merged.columns:
            merged["Sources"] = None

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

