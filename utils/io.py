import sqlite3

DB_PATH = "db/results.db"

def is_processed(part_number: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM parts WHERE \"Номер детали\" = ?", (part_number,))
    result = cursor.fetchone()

    conn.close()
    return result is not None
