import os
import sqlite3
from typing import Any

from agents.research_agent import ResearchAgent, ensure_sources_field
from config import settings
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from main import main as run_excel_job
from pydantic import BaseModel
from tools.web_search import WebSearchTool
from utils.db_writer import DB_PATH, fetch_all, init_db, save_results_bulk

router = APIRouter()


class SearchRequest(BaseModel):
    query: str


class CollectRequest(BaseModel):
    item_id: str


@router.get("/health")
def health() -> dict[str, Any]:
    db_status = "ok"
    try:
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("SELECT 1")
            conn.close()
        else:
            db_status = "not_initialized"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok",
        "app": "AI Data Collector API",
        "db": db_status
    }


@router.get("/settings")
def get_settings() -> dict[str, Any]:
    return {
        "model_name": settings.model_name,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "web_search_enabled": settings.web_search_enabled,
        "web_search_provider": settings.web_search_provider,
        "input_file": settings.input_file,
        "output_file": settings.output_file,
        "batch_size": settings.batch_size,
        "target_fields": settings.target_fields,
        "item_label": settings.item_label,
    }


@router.post("/search")
def search(request: SearchRequest) -> list[dict[str, Any]]:
    tool = WebSearchTool()
    results = tool.search(request.query)
    return [result.to_dict() for result in results]


@router.post("/items/collect")
def collect_item(request: CollectRequest) -> dict[str, Any]:
    item_id = request.item_id
    agent = ResearchAgent()
    output_fields = ensure_sources_field(settings.target_fields)

    try:
        data = agent.collect_item(item_id, output_fields)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    # Initialize DB in case it wasn't
    init_db(output_fields)

    # Convert data dict back to tuple order for save_results_bulk
    row_data = (
        item_id,
        *[data.get(f, "Not found") for f in output_fields if f != settings.column_name]
    )

    try:
        save_results_bulk([row_data], output_fields)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") from e

    return data


@router.post("/jobs/excel")
def start_excel_job() -> dict[str, str]:
    try:
        run_excel_job()
        return {"status": "completed", "output_path": settings.output_file}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Excel job failed: {str(e)}") from e


@router.get("/items")
def list_items() -> list[dict[str, Any]]:
    df = fetch_all()
    if df is None or df.empty:
        return []
    # Replace NaN with None
    records = df.where(df.notna(), None).to_dict(orient="records")
    return [dict(r) for r in records]


@router.get("/export/latest", response_class=FileResponse, response_model=None)
def export_latest() -> Any:
    if os.path.exists(settings.output_file):
        return FileResponse(
            settings.output_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    return JSONResponse(status_code=404, content={"detail": "Export file not found"})
