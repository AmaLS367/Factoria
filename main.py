import pandas as pd
from tqdm import tqdm
from scrapers.gemini import get_answer_from_gemini
from promts.generator import generate_prompt
from utils.parse import parse_answer
from utils.db_writer import init_db, fetch_all, FIELDS
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Alignment, Font
from utils.io import is_processed
from utils.db_writer import save_results_bulk
from config import USER_DATA_DIR
import sqlite3

INPUT_FILE = "input/input.xlsx"
OUTPUT_FILE = "results/output.xlsx"
SHEET_NAME = "Task1"
COLUMN_NAME = "Артикул"
BATCH_SIZE = 1

def format_output_excel(filepath: str, df: pd.DataFrame):
    wb = Workbook()
    ws = wb.active

    for row in dataframe_to_rows(df, index=False, header=True):
        ws.append(row)

    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_length * 1.1, 60)

    for cell in ws[1]:
        cell.font = Font(bold=True)

    wb.save(filepath)

def main():
    init_db()
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

    buffer = []

    for start in range(0, len(df), BATCH_SIZE):
        batch_df = df.iloc[start:start + BATCH_SIZE]

        for _, row in tqdm(batch_df.iterrows(), total=len(batch_df)):
            detail = str(row[COLUMN_NAME])

            if is_processed(detail):
                print(f"[INFO] Пропускаю {detail} — уже в базе")
                continue

            prompt = generate_prompt(detail)
            answer = get_answer_from_gemini(prompt, headless=False)
            parsed = parse_answer(answer)

            buffer.append((detail, *parsed.values()))

        save_results_bulk(buffer)
        buffer.clear()

    final_df = fetch_all()
    format_output_excel(OUTPUT_FILE, final_df)

if __name__ == "__main__":
    main()
