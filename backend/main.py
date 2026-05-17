import os
import sqlite3
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

import backend.utils.db_writer as db_writer
from backend.agents.research_agent import ResearchAgent, ensure_sources_field
from backend.config import settings
from backend.utils.db_writer import (
    fetch_all,
    get_all_existing_ids,
    get_db_path,
    init_db,
    prepare_row_data,
    save_results_bulk,
)
from backend.utils.jobs import update_job_progress, update_job_status, update_job_total_items

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


def main(
    job_id: str | None = None, input_file: str | None = None, output_file: str | None = None
) -> None:
    logger.info("Starting AI Data Collector")

    input_file_path = input_file or settings.input_file
    output_file_path = output_file or settings.output_file

    if job_id:
        update_job_status(job_id, "running")

    output_fields = ensure_sources_field(settings.target_fields)
    init_db(output_fields)

    current_run_id = db_writer._CURRENT_RUN_ID

    if job_id and current_run_id is not None:
        # Link run_id to job
        conn = sqlite3.connect(get_db_path())
        try:
            conn.execute("UPDATE jobs SET run_id = ? WHERE job_id = ?", (current_run_id, job_id))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to associate run_id with job: {e}")
        finally:
            conn.close()

    try:
        df = pd.read_excel(input_file_path, sheet_name=settings.sheet_name)
        if job_id:
            update_job_total_items(job_id, len(df))
    except Exception as e:
        logger.error(f"Failed to read input file: {e}")
        if job_id:
            update_job_status(job_id, "failed", str(e))
        return

    agent = ResearchAgent()
    buffer: list[tuple[str, ...]] = []
    existing_ids = get_all_existing_ids()
    try:
        col_idx = list(df.columns).index(settings.column_name) + 1
    except ValueError:
        error_msg = f"Column '{settings.column_name}' not found in the Excel file."
        logger.error(error_msg)
        if job_id:
            update_job_status(job_id, "failed", error_msg)
        return

    try:
        for start in range(0, len(df), settings.batch_size):
            batch_df = df.iloc[start : start + settings.batch_size]

            processed_in_batch = 0
            skipped_in_batch = 0
            failed_in_batch = 0

            for row in tqdm(batch_df.itertuples(), total=len(batch_df), desc="Processing batch"):
                item_id = str(row[col_idx])

                if item_id in existing_ids:
                    logger.debug(f"Skipping {item_id} — already in database")
                    skipped_in_batch += 1
                    continue

                try:
                    parsed = agent.collect_item(item_id, output_fields)
                    row_data = prepare_row_data(item_id, parsed, output_fields)
                    buffer.append(row_data)
                    processed_in_batch += 1
                except Exception as e:
                    logger.error(f"Failed processing item {item_id}: {e}")
                    failed_in_batch += 1

            if buffer:
                save_results_bulk(buffer, output_fields)
                buffer.clear()

            if job_id:
                update_job_progress(
                    job_id,
                    processed=processed_in_batch,
                    skipped=skipped_in_batch,
                    failed=failed_in_batch,
                )

        final_df = fetch_all(run_id=current_run_id if job_id else None)
        format_output_excel(output_file_path, final_df)
        logger.info("Data collection completed successfully")
        if job_id:
            update_job_status(job_id, "completed")

    except Exception as e:
        logger.error(f"Data collection failed: {e}")
        if job_id:
            update_job_status(job_id, "failed", str(e))


if __name__ == "__main__":
    main()
