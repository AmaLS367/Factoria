import logging
import os
import shutil
import sqlite3
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.agents.research_agent import ResearchAgent, ensure_sources_field
from backend.config import settings
from backend.main import main as run_excel_job
from backend.tools.web_search import WebSearchTool
from backend.utils.db_writer import fetch_all, get_db_path, save_single_item
from backend.utils.jobs import create_job, get_job, get_recent_jobs

router = APIRouter()
logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str


class CollectRequest(BaseModel):
    item_id: str


@router.get("/health")
def health() -> dict[str, Any]:
    db_status = "ok"
    try:
        db_path = get_db_path()
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            conn.execute("SELECT 1")
            conn.close()
        else:
            db_status = "not_initialized"
    except Exception as e:
        logger.error(f"DB Health check failed: {e}")
        db_status = "error"

    return {"status": "ok", "app": "AI Data Collector API", "db": db_status}


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
        logger.error(f"Item collection failed: {e}")
        raise HTTPException(status_code=500, detail="Item collection failed") from e

    try:
        save_single_item(item_id, data, output_fields)
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error") from e

    return data


@router.post("/jobs/excel")
async def start_excel_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),  # noqa: B008
) -> dict[str, str]:  # noqa: B008
    try:
        job_id = str(uuid.uuid4())

        input_dir = os.path.join("input", "jobs")
        output_dir = os.path.join("results", "jobs")
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        job_input_file = os.path.join(input_dir, f"{job_id}.xlsx")
        job_output_file = os.path.join(output_dir, f"{job_id}.xlsx")

        with open(job_input_file, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Total items will be calculated by the background worker
        create_job(job_input_file, job_output_file, 0, job_id=job_id)
        background_tasks.add_task(run_excel_job, job_id, job_input_file, job_output_file)

        return {"job_id": job_id, "status": "queued"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue Excel job: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue Excel job") from e


@router.get("/jobs")
def list_jobs() -> list[dict[str, Any]]:
    return get_recent_jobs(10)


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/export", response_class=FileResponse, response_model=None)
def export_job_file(job_id: str) -> Any:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed")

    output_file = job["output_file"]
    if not output_file or not os.path.exists(output_file):
        return JSONResponse(status_code=404, content={"detail": "Export file not found"})

    return FileResponse(
        output_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"export_{job_id}.xlsx",
    )


@router.get("/items")
def list_items(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")

    db_path = get_db_path()
    if not os.path.exists(db_path):
        return []
    df = fetch_all()
    if df is None or df.empty:
        return []
    # Replace NaN with None
    records = df.where(df.notna(), None).to_dict(orient="records")
    records = records[offset : offset + limit]
    return [dict(r) for r in records]


@router.get("/export/latest", response_class=FileResponse, response_model=None)
def export_latest() -> Any:
    if os.path.exists(settings.output_file):
        return FileResponse(
            settings.output_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    return JSONResponse(status_code=404, content={"detail": "Export file not found"})
