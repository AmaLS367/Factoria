from typing import Any
from unittest.mock import MagicMock, patch

from backend import cli


@patch("backend.cli.Console")
@patch("backend.cli.ResearchAgent")
@patch("backend.cli.LLMClient")
def test_process_single_item_collect_error(
    _mock_llm_client: MagicMock,
    mock_research_agent: MagicMock,
    mock_console_class: MagicMock,
) -> None:
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    cli.console = mock_console

    mock_agent_instance = MagicMock()
    mock_research_agent.return_value = mock_agent_instance

    error_message = "Simulated collection failure"
    mock_agent_instance.collect_item.side_effect = Exception(error_message)

    cli.process_single_item("FAIL-123")

    printed_texts = [call.args[0] for call in mock_console.print.call_args_list if call.args]

    assert len(printed_texts) >= 2

    error_printed = any(
        isinstance(text, str) and "[bold red]Error:[/]" in text and error_message in text
        for text in printed_texts
    )
    assert error_printed, f"Expected error message not found in console output: {printed_texts}"


@patch("backend.cli.fetch_review_queue")
def test_run_review_mode_json(mock_fetch: MagicMock, capsys: Any) -> None:
    mock_fetch.return_value = [{"field_id": 1, "review_status": "needs_review"}]
    cli.run_review_mode(limit=5, as_json=True)
    captured = capsys.readouterr()
    assert "field_id" in captured.out
    mock_fetch.assert_called_once_with(status="needs_review", limit=5)


@patch("backend.cli.fetch_review_queue")
def test_run_review_mode_empty(mock_fetch: MagicMock) -> None:
    mock_fetch.return_value = []
    mock_console = MagicMock()
    with patch("backend.cli.console", mock_console):
        cli.run_review_mode(limit=5, as_json=False)
        mock_console.print.assert_called_once()
        args = mock_console.print.call_args[0][0]
        assert "No fields need review" in args


@patch("backend.cli.update_field_review")
@patch("backend.cli.fetch_review_queue")
def test_run_review_mode_interactive_approve(
    mock_fetch: MagicMock, mock_update: MagicMock
) -> None:
    mock_fetch.return_value = [
        {
            "field_id": 10,
            "identifier_column": "part_number",
            "identifier_value": "PART-A",
            "field_name": "price",
            "field_value": "12.5",
            "confidence": 0.85,
        }
    ]
    mock_console = MagicMock()
    mock_console.input.return_value = "a"
    with patch("backend.cli.console", mock_console):
        cli.run_review_mode(limit=5, as_json=False)
        mock_update.assert_called_once_with(field_id=10, status="approved")


@patch("backend.cli.update_field_review")
@patch("backend.cli.fetch_review_queue")
def test_run_review_mode_interactive_reject(
    mock_fetch: MagicMock, mock_update: MagicMock
) -> None:
    mock_fetch.return_value = [
        {
            "field_id": 20,
            "identifier_column": "part_number",
            "identifier_value": "PART-B",
            "field_name": "weight",
            "field_value": "1.2",
            "confidence": 0.90,
        }
    ]
    mock_console = MagicMock()
    mock_console.input.return_value = "r"
    with patch("backend.cli.console", mock_console):
        cli.run_review_mode(limit=5, as_json=False)
        mock_update.assert_called_once_with(field_id=20, status="rejected")


@patch("backend.cli.update_field_review")
@patch("backend.cli.fetch_review_queue")
def test_run_review_mode_interactive_edit(
    mock_fetch: MagicMock, mock_update: MagicMock
) -> None:
    mock_fetch.return_value = [
        {
            "field_id": 30,
            "identifier_column": "part_number",
            "identifier_value": "PART-C",
            "field_name": "description",
            "field_value": "old description",
            "confidence": 0.50,
        }
    ]
    mock_console = MagicMock()
    mock_console.input.side_effect = ["e", "new description", "fixed typo"]
    with patch("backend.cli.console", mock_console):
        cli.run_review_mode(limit=5, as_json=False)
        mock_update.assert_called_once_with(
            field_id=30,
            status="corrected",
            field_value="new description",
            reviewer_note="fixed typo",
        )
