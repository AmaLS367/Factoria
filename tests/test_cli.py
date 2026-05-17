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
