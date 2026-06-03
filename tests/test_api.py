import os
import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pandas as pd
from fastapi.testclient import TestClient
from openpyxl import Workbook

from backend.config import settings
from backend.utils.schemas import TokenUsage

sys.path.insert(0, os.path.abspath("backend"))
from api.app import app

client = TestClient(app)

_XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _make_xlsx_bytes() -> bytes:
    wb = Workbook()
    ws = wb.active or wb.create_sheet()
    ws.append(["Item ID"])
    ws.append(["PART-001"])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "AI Data Collector API"
    assert "db" in data


def test_settings_no_keys() -> None:
    response = client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    assert "model_name" in data
    assert "input_file" in data
    # Ensure no sensitive keys are leaked
    assert "openai_api_key" not in data
    assert "llm_api_key" not in data
    assert "web_search_api_key" not in data


@patch("backend.api.routes.WebSearchTool")
def test_search(mock_web_search_tool: MagicMock) -> None:
    mock_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.to_dict.return_value = {
        "title": "Test Title",
        "url": "https://test.com",
        "snippet": "Test snippet",
    }
    mock_instance.search.return_value = [mock_result]
    mock_web_search_tool.return_value = mock_instance

    response = client.post("/search", json={"query": "test query"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "Test Title"
    mock_instance.search.assert_called_once_with("test query")


@patch("backend.api.routes.save_single_item")
@patch("backend.api.routes.ResearchAgent")
def test_collect_item(mock_research_agent: MagicMock, mock_save_single_item: MagicMock) -> None:
    mock_agent_instance = MagicMock()
    mock_agent_instance.collect_item_with_confidence.return_value = (
        {"Name": "Test Item", "Weight": "1kg"},
        {"Name": 1.0, "Weight": 0.8},
        TokenUsage(
            prompt_tokens=12, completion_tokens=4, total_tokens=16, estimated_cost_usd=0.002
        ),
    )
    mock_research_agent.return_value = mock_agent_instance

    response = client.post("/items/collect", json={"item_id": "test-id"})
    assert response.status_code == 200
    data = response.json()
    assert data["Name"] == "Test Item"
    mock_save_single_item.assert_called_once()
    assert mock_save_single_item.call_args.kwargs["token_usage"] == TokenUsage(
        prompt_tokens=12,
        completion_tokens=4,
        total_tokens=16,
        estimated_cost_usd=0.002,
    )


@patch("backend.api.routes.os.path.exists")
@patch("backend.api.routes.fetch_all")
def test_list_items(mock_fetch_all: MagicMock, mock_exists: MagicMock) -> None:
    mock_exists.return_value = True
    mock_df = pd.DataFrame({"Item ID": ["test-1"], "Name": ["Test Item 1"]})
    mock_fetch_all.return_value = mock_df

    response = client.get("/items")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["Item ID"] == "test-1"


@patch("backend.api.routes.os.path.exists")
@patch("backend.api.routes.fetch_all")
def test_list_items_empty(mock_fetch_all: MagicMock, mock_exists: MagicMock) -> None:
    mock_exists.return_value = True
    mock_fetch_all.return_value = pd.DataFrame()

    response = client.get("/items")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@patch("backend.api.routes.os.makedirs")
@patch("backend.api.routes.create_job")
@patch("backend.api.routes.BackgroundTasks.add_task")
def test_jobs_excel(
    mock_add_task: MagicMock,
    mock_create_job: MagicMock,
    _mock_makedirs: MagicMock,
) -> None:

    mock_create_job.return_value = "test-job-123"
    with patch("builtins.open", mock_open()):
        response = client.post(
            "/jobs/excel",
            files={"file": ("test.xlsx", _make_xlsx_bytes(), _XLSX_CONTENT_TYPE)},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert isinstance(data["job_id"], str)
    assert len(data["job_id"]) == 36
    mock_add_task.assert_called_once()
    mock_create_job.assert_called_once()


@patch("backend.api.routes.get_recent_jobs")
def test_get_jobs(mock_get_recent_jobs: MagicMock) -> None:
    mock_get_recent_jobs.return_value = [{"job_id": "test-123", "status": "completed"}]
    response = client.get("/jobs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["job_id"] == "test-123"


@patch("backend.api.routes.get_job")
def test_get_job(mock_get_job: MagicMock) -> None:
    mock_get_job.return_value = {"job_id": "test-123", "status": "running"}
    response = client.get("/jobs/test-123")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "test-123"
    assert data["status"] == "running"


@patch("backend.api.routes.get_job")
def test_get_job_not_found(mock_get_job: MagicMock) -> None:
    mock_get_job.return_value = None
    response = client.get("/jobs/test-123")
    assert response.status_code == 404


@patch("backend.api.routes.get_job")
def test_cost_report_unknown_job_returns_404(mock_get_job: MagicMock) -> None:
    mock_get_job.return_value = None

    response = client.get("/jobs/nonexistent-id/cost-report")

    assert response.status_code == 404


@patch("backend.api.routes.get_job")
def test_cost_report_new_job_returns_zero_counters(mock_get_job: MagicMock) -> None:
    mock_get_job.return_value = {
        "job_id": "job-1",
        "status": "queued",
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "total_llm_requests": 0,
        "estimated_cost_usd": 0.0,
    }

    response = client.get("/jobs/job-1/cost-report")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-1",
        "status": "queued",
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "total_tokens": 0,
        "total_llm_requests": 0,
        "estimated_cost_usd": 0.0,
        "model": settings.resolved_llm_model,
        "provider": settings.resolved_llm_provider,
    }


@patch("backend.api.routes.os.makedirs")
@patch("backend.api.routes.create_job")
def test_jobs_excel_failure(mock_create_job: MagicMock, _mock_makedirs: MagicMock) -> None:

    mock_create_job.side_effect = Exception("Test Error")
    with patch("builtins.open", mock_open()):
        response = client.post(
            "/jobs/excel",
            files={"file": ("test.xlsx", _make_xlsx_bytes(), _XLSX_CONTENT_TYPE)},
        )
    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "Failed to queue Excel job"


def test_jobs_excel_no_file() -> None:
    response = client.post("/jobs/excel")
    assert response.status_code == 422


@patch("backend.api.routes.os.makedirs")
@patch("backend.api.routes.create_job")
@patch("backend.api.routes.BackgroundTasks.add_task")
def test_jobs_excel_saves_input_file(
    _mock_add_task: MagicMock,
    mock_create_job: MagicMock,
    _mock_makedirs: MagicMock,
) -> None:

    mock_create_job.return_value = "test-job-123"
    m = mock_open()
    with patch("builtins.open", m):
        response = client.post(
            "/jobs/excel",
            files={"file": ("test.xlsx", _make_xlsx_bytes(), _XLSX_CONTENT_TYPE)},
        )
    job_id = response.json()["job_id"]
    expected_path = f"input/jobs/{job_id}.xlsx".replace("/", os.sep)
    # Check if any call matches expected_path
    calls = m.call_args_list
    paths = [call.args[0] for call in calls if isinstance(call.args[0], str)]
    assert any(expected_path in p for p in paths)


@patch("backend.api.routes.os.path.exists")
def test_export_latest_not_found(mock_exists: MagicMock) -> None:
    mock_exists.return_value = False
    response = client.get("/export/latest")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Export file not found"


@patch("backend.api.routes.FileResponse")
@patch("backend.api.routes.os.path.exists")
def test_export_latest_found(mock_exists: MagicMock, mock_file_response: MagicMock) -> None:
    mock_exists.return_value = True
    from fastapi.responses import JSONResponse

    mock_file_response.return_value = JSONResponse(content={"fake": "file"})

    response = client.get("/export/latest")
    assert response.status_code == 200
    mock_file_response.assert_called_once_with(
        settings.output_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@patch("backend.api.routes.os.path.exists")
def test_list_items_no_db(mock_exists: MagicMock) -> None:
    mock_exists.return_value = False
    response = client.get("/items")
    assert response.status_code == 200
    data = response.json()
    assert data == []


@patch("backend.api.routes.os.path.exists")
@patch("backend.api.routes.fetch_all")
def test_list_items_pagination(mock_fetch_all: MagicMock, mock_exists: MagicMock) -> None:
    mock_exists.return_value = True
    mock_df = pd.DataFrame(
        {"Item ID": [f"test-{i}" for i in range(10)], "Name": [f"Test Item {i}" for i in range(10)]}
    )
    mock_fetch_all.return_value = mock_df

    response = client.get("/items?limit=2&offset=3")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["Item ID"] == "test-3"
    assert data[1]["Item ID"] == "test-4"


@patch("backend.api.routes.os.path.exists")
@patch("backend.api.routes.fetch_all")
def test_list_items_pagination_invalid(mock_fetch_all: MagicMock, mock_exists: MagicMock) -> None:
    mock_exists.return_value = True
    response = client.get("/items?limit=2000")
    assert response.status_code == 400

    response = client.get("/items?offset=-1")
    assert response.status_code == 400


@patch("backend.api.routes.BackgroundTasks.add_task")
@patch("backend.api.routes.create_job")
def test_jobs_excel_concurrency(mock_create_job: MagicMock, mock_add_task: MagicMock) -> None:
    def return_job_id(*_args: object, **kwargs: object) -> str:
        return str(kwargs["job_id"])

    mock_create_job.side_effect = return_job_id

    # Test that two different jobs get unique paths
    m = mock_open()
    with patch("builtins.open", m):
        response1 = client.post(
            "/jobs/excel",
            files={"file": ("test1.xlsx", _make_xlsx_bytes(), _XLSX_CONTENT_TYPE)},
        )
        response2 = client.post(
            "/jobs/excel",
            files={"file": ("test2.xlsx", _make_xlsx_bytes(), _XLSX_CONTENT_TYPE)},
        )

    assert response1.status_code == 200
    assert response2.status_code == 200

    job_id1 = response1.json()["job_id"]
    job_id2 = response2.json()["job_id"]

    assert job_id1 != job_id2

    # Verify open was called with unique paths
    import os

    calls = m.call_args_list
    paths = [call.args[0] for call in calls if isinstance(call.args[0], str)]
    expected1 = f"input/jobs/{job_id1}.xlsx".replace("/", os.sep)
    expected2 = f"input/jobs/{job_id2}.xlsx".replace("/", os.sep)
    assert any(expected1 in p for p in paths)
    assert any(expected2 in p for p in paths)


@patch("backend.api.routes.get_job")
def test_export_latest_uses_job_output(mock_get_job: MagicMock) -> None:
    # Test that /jobs/{job_id}/export uses job-specific output file
    job_id = "test-job-123"
    job_output = f"results/jobs/{job_id}.xlsx"
    mock_get_job.return_value = {"job_id": job_id, "status": "completed", "output_file": job_output}

    with patch("backend.api.routes.os.path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("backend.api.routes.FileResponse") as mock_file_response:
            from fastapi.responses import JSONResponse

            mock_file_response.return_value = JSONResponse(content={"fake": "file"})

            response = client.get(f"/jobs/{job_id}/export")

            assert response.status_code == 200
            mock_file_response.assert_called_once_with(
                job_output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=f"export_{job_id}.xlsx",
            )


def test_preview_xlsx() -> None:
    response = client.post(
        "/jobs/excel/preview",
        files={"file": ("preview.xlsx", _make_xlsx_bytes(), _XLSX_CONTENT_TYPE)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["file_type"] == "xlsx"
    assert "Item ID" in data["columns"]
    assert data["row_count"] == 1


def test_preview_csv() -> None:
    csv_bytes = b"Item ID,Name\nPART-001,Widget\nPART-002,Gadget\n"
    response = client.post(
        "/jobs/excel/preview",
        files={"file": ("preview.csv", csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["file_type"] == "csv"
    assert "Item ID" in data["columns"]
    assert data["row_count"] == 2


def test_preview_invalid_file() -> None:
    response = client.post(
        "/jobs/excel/preview",
        files={"file": ("bad.xlsx", b"not really xlsx", _XLSX_CONTENT_TYPE)},
    )
    assert response.status_code == 400


@patch("backend.api.routes.cancel_job")
@patch("backend.api.routes.get_job")
def test_cancel_job_happy_path(mock_get_job: MagicMock, mock_cancel_job: MagicMock) -> None:
    mock_get_job.return_value = {"job_id": "abc", "status": "running"}
    mock_cancel_job.return_value = True
    response = client.post("/jobs/abc/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


@patch("backend.api.routes.get_job")
def test_cancel_job_not_found(mock_get_job: MagicMock) -> None:
    mock_get_job.return_value = None
    response = client.post("/jobs/missing/cancel")
    assert response.status_code == 404


@patch("backend.api.routes.get_job")
def test_cancel_job_wrong_status(mock_get_job: MagicMock) -> None:
    mock_get_job.return_value = {"job_id": "abc", "status": "completed"}
    response = client.post("/jobs/abc/cancel")
    assert response.status_code == 400


@patch("backend.api.routes.os.path.exists")
@patch("backend.api.routes.create_job")
@patch("backend.api.routes.BackgroundTasks.add_task")
@patch("backend.api.routes.get_job")
def test_retry_job_happy_path(
    mock_get_job: MagicMock,
    _mock_add: MagicMock,
    mock_create: MagicMock,
    mock_exists: MagicMock,
) -> None:
    mock_get_job.return_value = {
        "job_id": "old",
        "status": "failed",
        "input_file": "input/jobs/old.xlsx",
        "sheet_name": None,
        "column_name": None,
        "target_fields": None,
        "item_label": None,
    }
    mock_exists.return_value = True
    mock_create.return_value = "new-job-id"
    response = client.post("/jobs/old/retry")
    assert response.status_code == 200
    assert response.json()["status"] == "queued"


@patch("backend.api.routes.get_job")
def test_retry_job_not_found(mock_get_job: MagicMock) -> None:
    mock_get_job.return_value = None
    response = client.post("/jobs/missing/retry")
    assert response.status_code == 404


@patch("backend.api.routes.get_job")
def test_retry_job_wrong_status(mock_get_job: MagicMock) -> None:
    mock_get_job.return_value = {"job_id": "x", "status": "running"}
    response = client.post("/jobs/x/retry")
    assert response.status_code == 400


@patch("backend.api.routes.os.path.exists")
@patch("backend.api.routes.get_job")
def test_retry_job_missing_input_file(mock_get_job: MagicMock, mock_exists: MagicMock) -> None:
    mock_get_job.return_value = {
        "job_id": "old",
        "status": "failed",
        "input_file": "gone.xlsx",
    }
    mock_exists.return_value = False
    response = client.post("/jobs/old/retry")
    assert response.status_code == 400


@patch("backend.api.routes.get_job")
def test_export_job_not_completed(mock_get_job: MagicMock) -> None:
    mock_get_job.return_value = {"job_id": "x", "status": "running"}
    response = client.get("/jobs/x/export")
    assert response.status_code == 400


@patch("backend.api.routes.get_job")
def test_export_job_not_found(mock_get_job: MagicMock) -> None:
    mock_get_job.return_value = None
    response = client.get("/jobs/missing/export")
    assert response.status_code == 404


@patch("backend.api.routes.os.path.exists")
def test_get_item_sources_no_db(mock_exists: MagicMock) -> None:
    mock_exists.return_value = False
    response = client.get("/items/foo/sources")
    assert response.status_code == 404


@patch("backend.api.routes.os.path.exists")
def test_get_item_fields_no_db(mock_exists: MagicMock) -> None:
    mock_exists.return_value = False
    response = client.get("/items/foo/fields")
    assert response.status_code == 404


def test_get_logs_invalid_lines() -> None:
    response = client.get("/logs?lines=99999")
    assert response.status_code == 400


@patch("backend.api.routes.os.path.exists")
def test_get_logs_missing_file(mock_exists: MagicMock) -> None:
    mock_exists.return_value = False
    response = client.get("/logs?lines=10")
    assert response.status_code == 200
    data = response.json()
    assert data["entries"] == []
    assert data["total_returned"] == 0


def test_get_logs_with_level_filter(tmp_path: Path) -> None:
    log_content = (
        "2026-05-18 10:00:00,000 [INFO] backend.main: starting up\n"
        "2026-05-18 10:00:01,000 [ERROR] backend.main: kaboom\n"
        "raw line with no format\n"
    )
    log_file = tmp_path / "collector.log"
    log_file.write_text(log_content, encoding="utf-8")

    with patch("backend.api.routes._LOG_FILE", str(log_file)):
        response = client.get("/logs?lines=10&level=ERROR")
        assert response.status_code == 200
        data = response.json()
        levels = {entry["level"] for entry in data["entries"]}
        assert levels == {"ERROR"}


def test_collect_item_agent_failure() -> None:
    with patch("backend.api.routes.ResearchAgent") as mock_agent:
        instance = MagicMock()
        instance.collect_item_with_confidence.side_effect = RuntimeError("boom")
        mock_agent.return_value = instance
        response = client.post("/items/collect", json={"item_id": "x"})
        assert response.status_code == 500


def test_collect_item_save_failure() -> None:
    with (
        patch("backend.api.routes.ResearchAgent") as mock_agent,
        patch("backend.api.routes.save_single_item") as mock_save,
    ):
        instance = MagicMock()
        instance.collect_item_with_confidence.return_value = (
            {"Name": "X"},
            {"Name": 0.5},
            TokenUsage(),
        )
        mock_agent.return_value = instance
        mock_save.side_effect = RuntimeError("db down")
        response = client.post("/items/collect", json={"item_id": "x"})
        assert response.status_code == 500


@patch("backend.api.routes.fetch_review_queue")
def test_list_review_fields_happy_path(mock_fetch: MagicMock) -> None:
    mock_fetch.return_value = [{"field_id": 1, "review_status": "needs_review"}]
    response = client.get("/reviews/fields?status=needs_review&limit=10&offset=5&job_id=job-123")
    assert response.status_code == 200
    assert response.json() == [{"field_id": 1, "review_status": "needs_review"}]
    mock_fetch.assert_called_once_with(status="needs_review", limit=10, offset=5, job_id="job-123")


def test_list_review_fields_validation() -> None:
    response = client.get("/reviews/fields?limit=9999")
    assert response.status_code == 400

    response = client.get("/reviews/fields?offset=-1")
    assert response.status_code == 400

    response = client.get("/reviews/fields?status=invalid_status")
    assert response.status_code == 400


@patch("backend.api.routes.update_field_review")
def test_review_field_happy_path(mock_update: MagicMock) -> None:
    mock_update.return_value = {"field_id": 1, "review_status": "approved"}
    response = client.patch(
        "/reviews/fields/1", json={"status": "approved", "reviewer_note": "looks good"}
    )
    assert response.status_code == 200
    assert response.json() == {"field_id": 1, "review_status": "approved"}
    mock_update.assert_called_once_with(
        field_id=1, status="approved", field_value=None, reviewer_note="looks good"
    )


def test_review_field_invalid_status() -> None:
    response = client.patch("/reviews/fields/1", json={"status": "invalid_status"})
    assert response.status_code == 422  # Pydantic Literal validation error


@patch("backend.api.routes.update_field_review")
def test_review_field_value_error(mock_update: MagicMock) -> None:
    mock_update.side_effect = ValueError("Corrected status requires a non-empty value")
    response = client.patch("/reviews/fields/1", json={"status": "corrected", "field_value": ""})
    assert response.status_code == 400
    assert "non-empty value" in response.json()["detail"]


@patch("backend.api.routes.update_field_review")
def test_review_field_not_found(mock_update: MagicMock) -> None:
    mock_update.return_value = None
    response = client.patch("/reviews/fields/999", json={"status": "approved"})
    assert response.status_code == 404


@patch("backend.api.routes.get_review_summary")
def test_review_summary_happy_path(mock_summary: MagicMock) -> None:
    mock_summary.return_value = {"needs_review": 5, "auto_accepted": 10}
    response = client.get("/reviews/summary?job_id=job-123")
    assert response.status_code == 200
    assert response.json() == {"needs_review": 5, "auto_accepted": 10}
    mock_summary.assert_called_once_with(job_id="job-123")
