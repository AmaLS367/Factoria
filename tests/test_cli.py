from unittest.mock import MagicMock, patch

from backend import cli


@patch("backend.cli.Console")
@patch("backend.cli.ResearchAgent")
@patch("backend.cli.LLMClient")
def test_process_single_item_collect_error(
    mock_llm_client: MagicMock,
    mock_research_agent: MagicMock,
    mock_console_class: MagicMock,
) -> None:
    """
    Tests that an exception during the collect_item process in the CLI
    is properly caught, an error message is printed, and execution stops.
    """
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    cli.console = mock_console  # Replace the module-level console

    mock_agent_instance = MagicMock()
    mock_research_agent.return_value = mock_agent_instance

    # Simulate an error during collection
    error_message = "Simulated collection failure"
    mock_agent_instance.collect_item.side_effect = Exception(error_message)

    cli.process_single_item("FAIL-123")

    # Verify the error was printed to the console
    printed_texts = [call.args[0] for call in mock_console.print.call_args_list if call.args]

    # Should print the "Processing..." panel
    assert len(printed_texts) >= 2

    # Check that an error message was printed
    error_printed = False
    for text in printed_texts:
        if isinstance(text, str) and "[bold red]Error:[/]" in text and error_message in text:
            error_printed = True
            break

    assert error_printed, f"Expected error message not found in console output: {printed_texts}"

    # Ensure save_single_item was not called since it returned early
    with patch("backend.cli.save_single_item") as mock_save:
        cli.process_single_item("FAIL-123")
        mock_save.assert_not_called()
