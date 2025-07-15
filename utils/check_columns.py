import sqlite3

def show_columns():
    conn = sqlite3.connect("db/results.db")
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(parts)")
    columns = cursor.fetchall()

    print("Колонки в таблице 'parts':")
    for col in columns:
        print(f"- {col[1]}")

    conn.close()

show_columns()
