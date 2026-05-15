import sqlite3
import os
import pandas as pd

DB_PATH = os.path.abspath("db/results.db")

FIELDS = [
    "Part Number",
    "Name", "Description", "Weight", "Cross-references",
    "Material", "Dimensions", "Applicability", "Interchangeability"
]

def init_db():
    os.makedirs("db", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {" TEXT, ".join(f'"{f}"' for f in FIELDS)} TEXT,
            UNIQUE("Part Number")
        )
    """)
    conn.commit()
    conn.close()

def detail_exists(detail_number: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM parts WHERE \"Part Number\" = ?", (detail_number,))
    result = cur.fetchone()
    conn.close()
    return result is not None

def save_results_bulk(data_list: list[tuple]):
    if not data_list:
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executemany(f"""
        INSERT OR IGNORE INTO parts ({",".join(f'"{f}"' for f in FIELDS)})
        VALUES ({",".join("?" for _ in FIELDS)})
    """, data_list)

    conn.commit()
    conn.close()


def fetch_all():
    conn = sqlite3.connect(DB_PATH)
    df = None
    try:
        df = pd.read_sql_query("SELECT * FROM parts", conn)
    finally:
        conn.close()
    return df
