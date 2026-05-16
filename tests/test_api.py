import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath('backend'))
from api.app import app

client = TestClient(app)

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

@patch("api.routes.WebSearchTool")
def test_search(mock_web_search_tool: MagicMock) -> None:
    mock_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.to_dict.return_value = {
        "title": "Test Title",
        "url": "https://test.com",
        "snippet": "Test snippet"
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

@patch("api.routes.save_results_bulk")
@patch("api.routes.init_db")
@patch("api.routes.ResearchAgent")
def test_collect_item(
    mock_research_agent: MagicMock,
    mock_init_db: MagicMock,
    mock_save_results: MagicMock
) -> None:
    mock_agent_instance = MagicMock()
    mock_agent_instance.collect_item.return_value = {"Name": "Test Item", "Weight": "1kg"}
    mock_research_agent.return_value = mock_agent_instance

    response = client.post("/items/collect", json={"item_id": "test-id"})
    assert response.status_code == 200
    data = response.json()
    assert data["Name"] == "Test Item"
    mock_init_db.assert_called_once()
    mock_save_results.assert_called_once()

@patch("api.routes.fetch_all")
def test_list_items(mock_fetch_all: MagicMock) -> None:
    mock_df = pd.DataFrame({
        "Item ID": ["test-1"],
        "Name": ["Test Item 1"]
    })
    mock_fetch_all.return_value = mock_df

    response = client.get("/items")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["Item ID"] == "test-1"

@patch("api.routes.fetch_all")
def test_list_items_empty(mock_fetch_all: MagicMock) -> None:
    mock_fetch_all.return_value = pd.DataFrame()

    response = client.get("/items")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

@patch("api.routes.run_excel_job")
def test_jobs_excel(mock_run_excel_job: MagicMock) -> None:
    response = client.post("/jobs/excel")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "output_path" in data
    mock_run_excel_job.assert_called_once()

@patch("api.routes.run_excel_job")
def test_jobs_excel_failure(mock_run_excel_job: MagicMock) -> None:
    mock_run_excel_job.side_effect = Exception("Test Error")
    response = client.post("/jobs/excel")
    assert response.status_code == 500
    data = response.json()
    assert "Excel job failed: Test Error" in data["detail"]

@patch("api.routes.os.path.exists")
def test_export_latest_not_found(mock_exists: MagicMock) -> None:
    mock_exists.return_value = False
    response = client.get("/export/latest")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Export file not found"

@patch("api.routes.FileResponse")
@patch("api.routes.os.path.exists")
def test_export_latest_found(mock_exists: MagicMock, mock_file_response: MagicMock) -> None:
    mock_exists.return_value = True
    # We mock FileResponse because actually returning it looks for a file
    mock_file_response.return_value = {"file": "fake"}

    # We cannot test FileResponse easily since we mock it, but we can verify it's called
    import api.routes as routes
    from fastapi.responses import JSONResponse

    with patch.object(routes, 'FileResponse', return_value=JSONResponse(content={"fake": "file"})):
        response = client.get("/export/latest")
        assert response.status_code == 200
