import os
import sys

# Add the project root to sys.path so 'backend.*' imports work when run as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows
from tqdm import tqdm

from backend.agents.research_agent import ResearchAgent, ensure_sources_field
from backend.config import settings
from backend.utils.db_writer import (
    fetch_all,
    get_all_existing_ids,
    init_db,
    prepare_row_data,
    save_results_bulk,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler("collector.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def format_output_excel(filepath: str, df: pd.DataFrame | None) -> None:
    if df is None or df.empty:
        logger.warning("No data to save to Excel.")
        return

    wb = Workbook()
    ws = wb.active
    if ws is None:
        ws = wb.create_sheet()

    for row in dataframe_to_rows(df, index=False, header=True):
        ws.append(row)

    wrap_alignment = Alignment(wrap_text=True, vertical="top")
    for col in ws.columns:
        column_idx = col[0].column
        if not isinstance(column_idx, int):
            continue

        max_length = 0
        col_letter = get_column_letter(column_idx)
        for cell in col:
            cell.alignment = wrap_alignment
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_length * 1.1, 60)

    for cell in ws[1]:
        cell.font = Font(bold=True)

    wb.save(filepath)
    logger.info(f"Results formatted and saved to {filepath}")


def main() -> None:
    logger.info("Starting AI Data Collector")
    output_fields = ensure_sources_field(settings.target_fields)
    init_db(output_fields)

    try:
        df = pd.read_excel(settings.input_file, sheet_name=settings.sheet_name)
    except Exception as e:
        logger.error(f"Failed to read input file: {e}")
        return

    agent = ResearchAgent()
    buffer: list[tuple[str, ...]] = []
    existing_ids = get_all_existing_ids()
    col_idx = list(df.columns).index(settings.column_name) + 1

    for start in range(0, len(df), settings.batch_size):
        batch_df = df.iloc[start : start + settings.batch_size]

        for row in tqdm(batch_df.itertuples(), total=len(batch_df), desc="Processing batch"):
            item_id = str(row[col_idx])

            if item_id in existing_ids:
                logger.debug(f"Skipping {item_id} — already in database")
                continue

            parsed = agent.collect_item(item_id, output_fields)

            row_data = prepare_row_data(item_id, parsed, output_fields)
            buffer.append(row_data)

        if buffer:
            save_results_bulk(buffer, output_fields)
            buffer.clear()

    final_df = fetch_all()
    format_output_excel(settings.output_file, final_df)
    logger.info("Data collection completed successfully")


if __name__ == "__main__":
    main()
