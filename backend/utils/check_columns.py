import sqlite3

from backend.config import settings


def show_columns() -> None:
    conn = sqlite3.connect(settings.db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(parts)")
    columns = cursor.fetchall()

    print("Колонки в таблице 'parts':")
    for col in columns:
        print(f"- {col[1]}")

    conn.close()


if __name__ == "__main__":
    show_columns()
