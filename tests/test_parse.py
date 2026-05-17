import pytest

from backend.utils.parse import parse_answer


def test_parse_answer_normal_case() -> None:
    answer = '{"Name": "Widget", "Color": "Red"}'
    fields = ["Name", "Color", "Size"]

    result = parse_answer(answer, fields)

    assert result == {"Name": "Widget", "Color": "Red", "Size": "Not found"}


def test_parse_answer_with_markdown() -> None:
    answer = """Here is the JSON you requested:
```json
{
    "Name": "Gadget",
    "Price": "19.99"
}
```
Have a nice day!"""
    fields = ["Name", "Price", "Brand"]

    result = parse_answer(answer, fields)

    assert result == {"Name": "Gadget", "Price": "19.99", "Brand": "Not found"}


def test_parse_answer_invalid_json() -> None:
    answer = "This is not JSON at all."
    fields = ["Name", "Color"]

    result = parse_answer(answer, fields)

    assert result == {"Name": "Not found", "Color": "Not found"}


def test_parse_answer_logs_warning_on_invalid_json(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    answer = "This string has no JSON braces at all"
    fields = ["Name"]

    with caplog.at_level(logging.WARNING):
        result = parse_answer(answer, fields)

    assert result == {"Name": "Not found"}
    assert "Failed to parse JSON response" in caplog.text
    assert "This string has no JSON braces at all" in caplog.text


def test_parse_answer_logs_warning_on_malformed_json_block(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    answer = """Here is your data:
{
    "Name": "Widget",
    "Color": "Red"
    missing quotes and comma
}"""
    fields = ["Name"]

    with caplog.at_level(logging.WARNING):
        result = parse_answer(answer, fields)

    assert result == {"Name": "Not found"}
    assert "Failed to parse JSON response" in caplog.text
