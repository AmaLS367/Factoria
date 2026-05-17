import os
import sqlite3
import sys

# Add the parent directory of backend to sys.path to allow importing from config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import settings


def show_columns() -> None:
    conn = sqlite3.connect(settings.db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(results)")
    columns = cursor.fetchall()

    print("Колонки в таблице 'results':")
    for col in columns:
        print(f"- {col[1]}")

    conn.close()


show_columns()
