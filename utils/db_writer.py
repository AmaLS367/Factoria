import logging
import os
import sqlite3

import pandas as pd

from config import settings

logger = logging.getLogger(__name__)

DB_PATH = os.path.abspath(settings.db_path)

def init_db(fields: list[str]) -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # We always have the primary ID and the input item identifier
    columns = [f'"{settings.column_name}" TEXT UNIQUE']
    for field in fields:
        if field != settings.column_name:
            columns.append(f'"{field}" TEXT')

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY AUTOINCREMENT,
        {', '.join(columns)})
    """)
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")

def detail_exists(item_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"SELECT 1 FROM results WHERE \"{settings.column_name}\" = ?", (item_id,))
    result = cur.fetchone()
    conn.close()
    return result is not None

def save_results_bulk(data_list: list[tuple[str, ...]], fields: list[str]) -> None:
    if not data_list:
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    all_fields = [settings.column_name] + [f for f in fields if f != settings.column_name]
    placeholders = ", ".join("?" for _ in all_fields)
    field_names = ", ".join(f'"{f}"' for f in all_fields)

    try:
        cur.executemany(f"""
            INSERT OR IGNORE INTO results ({field_names}) VALUES ({placeholders})
        """, data_list)
        conn.commit()
        logger.info(f"Saved {len(data_list)} items to database")
    except Exception as e:
        logger.error(f"Error saving to database: {e}")
    finally:
        conn.close()

def fetch_all() -> pd.DataFrame | None:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM results", conn)
        return df
    except Exception as e:
        logger.error(f"Error fetching from database: {e}")
        return None
    finally:
        conn.close()

