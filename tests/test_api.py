import os
import sys
from io import BytesIO
from unittest.mock import MagicMock, mock_open, patch

import pandas as pd
from fastapi.testclient import TestClient
from openpyxl import Workbook

from backend.config import settings

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
    )
    mock_research_agent.return_value = mock_agent_instance

    response = client.post("/items/collect", json={"item_id": "test-id"})
    assert response.status_code == 200
    data = response.json()
    assert data["Name"] == "Test Item"
    mock_save_single_item.assert_called_once()


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
def test_jobs_excel_concurrency(mock_add_task: MagicMock) -> None:

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
