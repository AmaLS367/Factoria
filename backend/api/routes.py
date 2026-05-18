import collections
import csv
import dataclasses
import io
import json as _json
import logging
import os
import re
import shutil
import sqlite3
import uuid
from typing import Any

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.agents.research_agent import ResearchAgent, ensure_sources_field
from backend.config import settings
from backend.main import main as run_excel_job
from backend.tools.web_search import WebSearchTool
from backend.utils.db_writer import fetch_all, get_db_path, save_single_item
from backend.utils.jobs import cancel_job, create_job, get_job, get_recent_jobs
from backend.utils.templates import (
    Template as SchemaTemplate,
)
from backend.utils.templates import (
    delete_template,
    get_template,
    list_templates,
    save_template,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/templates")
def list_schema_templates() -> list[dict[str, Any]]:
    return [dataclasses.asdict(t) for t in list_templates()]


@router.get("/templates/{slug}")
def get_schema_template(slug: str) -> dict[str, Any]:
    t = get_template(slug)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return dataclasses.asdict(t)


class TemplateCreateRequest(BaseModel):
    slug: str
    name: str
    description: str = ""
    item_label: str
    column_name: str
    target_fields: list[str]


@router.post("/templates", status_code=201)
def create_schema_template(request: TemplateCreateRequest) -> dict[str, Any]:
    if not re.match(r"^[a-z0-9-]+$", request.slug):
        raise HTTPException(
            status_code=400, detail="Slug must contain only lowercase letters, numbers, and hyphens"
        )
    if len(request.slug) < 2 or len(request.slug) > 64:
        raise HTTPException(status_code=400, detail="Slug must be between 2 and 64 characters long")
    if not request.target_fields:
        raise HTTPException(status_code=400, detail="target_fields cannot be empty")
    if len(request.target_fields) > 50:
        raise HTTPException(status_code=400, detail="target_fields cannot exceed 50 fields")

    t = SchemaTemplate(
        slug=request.slug,
        name=request.name,
        description=request.description,
        item_label=request.item_label,
        column_name=request.column_name,
        target_fields=request.target_fields,
        is_builtin=False,
    )
    try:
        save_template(t)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return dataclasses.asdict(t)


@router.delete("/templates/{slug}", status_code=204)
def delete_schema_template(slug: str) -> None:
    try:
        found = delete_template(slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not found:
        raise HTTPException(status_code=404, detail="Template not found")


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
        data, conf = agent.collect_item_with_confidence(item_id, output_fields)
    except Exception as e:
        logger.error(f"Item collection failed: {e}")
        raise HTTPException(status_code=500, detail="Item collection failed") from e

    try:
        save_single_item(item_id, data, output_fields, confidence=conf)
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error") from e

    return data


@router.post("/jobs/excel/preview")
async def preview_excel_file(
    file: UploadFile = File(...),  # noqa: B008
    sheet_name: str | None = None,
) -> dict[str, Any]:
    try:
        raw = await file.read()
        filename = file.filename or ""
        buf = io.BytesIO(raw)

        if filename.endswith(".csv"):
            sample_text = raw[:4096].decode("utf-8", errors="replace")
            try:
                dialect = csv.Sniffer().sniff(sample_text)
                sep = dialect.delimiter
            except csv.Error:
                sep = ","
            df = pd.read_csv(io.BytesIO(raw), sep=sep)
            sheets: list[str] = ["Sheet1"]
            file_type = "csv"
        else:
            xl = pd.ExcelFile(buf)
            sheets = [str(s) for s in xl.sheet_names]
            active_sheet = sheet_name if sheet_name in sheets else sheets[0]
            df = pd.read_excel(buf, sheet_name=active_sheet)
            file_type = "xlsx"

        assert isinstance(df, pd.DataFrame)
        columns = [str(c) for c in df.columns.tolist()]
        sample_rows = [
            {str(k): (None if pd.isnull(v) else v) for k, v in row.items()}
            for row in df.head(3).to_dict(orient="records")
        ]

        return {
            "file_type": file_type,
            "sheets": sheets,
            "columns": columns,
            "row_count": len(df),
            "sample_rows": sample_rows,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preview file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}") from e


@router.post("/jobs/excel")
async def start_excel_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),  # noqa: B008
    sheet_name: str | None = Form(default=None),  # noqa: B008
    column_name: str | None = Form(default=None),  # noqa: B008
    target_fields: str | None = Form(default=None),  # noqa: B008
    item_label: str | None = Form(default=None),  # noqa: B008
) -> dict[str, str]:
    parsed_fields: list[str] | None = None
    if target_fields:
        try:
            parsed_fields = _json.loads(target_fields)
            if not isinstance(parsed_fields, list) or not all(
                isinstance(f, str) for f in parsed_fields
            ):
                raise ValueError("target_fields must be a JSON array of strings")
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=400, detail="target_fields must be a JSON array of strings"
            ) from e

    try:
        job_id = str(uuid.uuid4())

        input_dir = os.path.join("input", "jobs")
        output_dir = os.path.join("results", "jobs")
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        original_name = file.filename or "upload.xlsx"
        ext = os.path.splitext(original_name)[1].lower() or ".xlsx"
        job_input_file = os.path.join(input_dir, f"{job_id}{ext}")
        job_output_file = os.path.join(output_dir, f"{job_id}.xlsx")

        with open(job_input_file, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Total items will be calculated by the background worker
        create_job(
            job_input_file,
            job_output_file,
            0,
            job_id=job_id,
            sheet_name=sheet_name,
            column_name=column_name,
            target_fields=parsed_fields,
            item_label=item_label or None,
        )
        background_tasks.add_task(
            run_excel_job, job_id, job_input_file, job_output_file, sheet_name, column_name
        )

        return {"job_id": job_id, "status": "queued"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue Excel job: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue Excel job") from e


@router.post("/jobs/{job_id}/cancel")
def cancel_excel_job(job_id: str) -> dict[str, str]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in ("queued", "running"):
        raise HTTPException(  # noqa: E501
            status_code=400, detail=f"Cannot cancel job with status '{job['status']}'"
        )
    cancel_job(job_id)
    return {"job_id": job_id, "status": "cancelled"}


@router.post("/jobs/{job_id}/retry")
def retry_excel_job(job_id: str, background_tasks: BackgroundTasks) -> dict[str, str]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in ("failed", "cancelled"):
        raise HTTPException(  # noqa: E501
            status_code=400, detail=f"Cannot retry job with status '{job['status']}'"
        )

    old_input = job["input_file"]
    if not old_input or not os.path.exists(old_input):
        raise HTTPException(status_code=400, detail="Original input file no longer exists")

    new_job_id = str(uuid.uuid4())
    output_dir = os.path.join("results", "jobs")
    os.makedirs(output_dir, exist_ok=True)
    new_output = os.path.join(output_dir, f"{new_job_id}.xlsx")

    sheet_name = job.get("sheet_name")
    column_name = job.get("column_name")

    target_fields_raw = job.get("target_fields")
    parsed_fields: list[str] | None = None
    if target_fields_raw:
        try:
            parsed_fields = _json.loads(target_fields_raw)
        except Exception:
            pass

    item_label = job.get("item_label")

    create_job(
        old_input,
        new_output,
        0,
        job_id=new_job_id,
        sheet_name=sheet_name,
        column_name=column_name,
        target_fields=parsed_fields,
        item_label=item_label,
    )
    background_tasks.add_task(
        run_excel_job, new_job_id, old_input, new_output, sheet_name, column_name
    )

    return {"job_id": new_job_id, "status": "queued"}


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
    raw = df.to_dict(orient="records")
    records: list[dict[str, Any]] = [
        {str(k): (None if pd.isnull(v) else v) for k, v in row.items()} for row in raw
    ]
    return records[offset : offset + limit]


@router.get("/export/latest", response_class=FileResponse, response_model=None)
def export_latest() -> Any:
    if os.path.exists(settings.output_file):
        return FileResponse(
            settings.output_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    return JSONResponse(status_code=404, content={"detail": "Export file not found"})


@router.get("/items/{identifier_value}/fields")
def get_item_fields(identifier_value: str) -> list[dict[str, Any]]:
    db_path = get_db_path()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Item not found")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id FROM items WHERE identifier_column = ? AND identifier_value = ?",
            (settings.column_name, identifier_value),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")
        fields = conn.execute(
            "SELECT field_name, field_value, confidence FROM item_fields WHERE item_id = ?",
            (row["id"],),
        ).fetchall()
        return [dict(f) for f in fields]
    finally:
        conn.close()


@router.get("/items/{identifier_value}/sources")
def get_item_sources(identifier_value: str) -> list[dict[str, Any]]:
    db_path = get_db_path()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Item not found")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id FROM items WHERE identifier_column = ? AND identifier_value = ?",
            (settings.column_name, identifier_value),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")
        item_id = row["id"]
        sources = conn.execute(
            """
            SELECT title, url, snippet, provider, credibility_score, retrieved_at
            FROM item_sources WHERE item_id = ?
            ORDER BY credibility_score DESC NULLS LAST
            """,
            (item_id,),
        ).fetchall()
        return [dict(s) for s in sources]
    finally:
        conn.close()


_LOG_FILE = "collector.log"
_LOG_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+) \[(\w+)\] ([\w.]+): (.+)$")


@router.get("/logs")
def get_logs(lines: int = 200, level: str = "") -> dict[str, Any]:
    if lines < 1 or lines > 5000:
        raise HTTPException(status_code=400, detail="lines must be between 1 and 5000")

    if not os.path.exists(_LOG_FILE):
        return {"entries": [], "total_returned": 0, "file": _LOG_FILE}

    tail: collections.deque[str] = collections.deque(maxlen=lines)
    with open(_LOG_FILE, encoding="utf-8", errors="replace") as f:
        for line in f:
            tail.append(line.rstrip("\n"))

    entries = []
    for line in tail:
        m = _LOG_PATTERN.match(line)
        if m:
            entry = {
                "timestamp": m.group(1),
                "level": m.group(2),
                "logger": m.group(3),
                "message": m.group(4),
            }
        else:
            entry = {"timestamp": "", "level": "INFO", "logger": "", "message": line}

        if level and entry["level"] != level.upper():
            continue
        entries.append(entry)

    return {"entries": entries, "total_returned": len(entries), "file": _LOG_FILE}


@router.get("/jobs/{job_id}/cost-report")
def get_job_cost_report(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    pt = job.get("total_prompt_tokens") or 0
    ct = job.get("total_completion_tokens") or 0
    return {
        "job_id": job_id,
        "status": job["status"],
        "total_prompt_tokens": pt,
        "total_completion_tokens": ct,
        "total_tokens": pt + ct,
        "total_llm_requests": job.get("total_llm_requests") or 0,
        "estimated_cost_usd": job.get("estimated_cost_usd") or 0.0,
        "model": settings.resolved_llm_model,
        "provider": settings.resolved_llm_provider,
    }
