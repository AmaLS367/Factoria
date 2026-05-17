import pytest

from backend.utils.parse import parse_answer


def test_parse_answer_normal_case() -> None:
    answer = '{"Name": "Widget", "Color": "Red"}'
    fields = ["Name", "Color", "Size"]

    result, conf = parse_answer(answer, fields)

    assert conf == {k: None for k in fields}

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

    result, conf = parse_answer(answer, fields)

    assert conf == {k: None for k in fields}

    assert result == {"Name": "Gadget", "Price": "19.99", "Brand": "Not found"}


def test_parse_answer_invalid_json() -> None:
    answer = "This is not JSON at all."
    fields = ["Name", "Color"]

    result, conf = parse_answer(answer, fields)

    assert conf == {k: None for k in fields}

    assert result == {"Name": "Not found", "Color": "Not found"}


def test_parse_answer_logs_warning_on_invalid_json(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    answer = "This string has no JSON braces at all"
    fields = ["Name"]

    with caplog.at_level(logging.WARNING):
        result, conf = parse_answer(answer, fields)

    assert conf == {k: None for k in fields}

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
        result, conf = parse_answer(answer, fields)

    assert conf == {k: None for k in fields}

    assert result == {"Name": "Not found"}
    assert "Failed to parse JSON response" in caplog.text


def test_parse_answer_new_format() -> None:
    answer = (
        '{"values": {"Name": "Widget", "Color": "Red"}, "confidence": {"Name": 0.95, "Color": 0.5}}'
    )
    fields = ["Name", "Color", "Size"]

    result, conf = parse_answer(answer, fields)

    assert result == {"Name": "Widget", "Color": "Red", "Size": "Not found"}
    assert conf == {"Name": 0.95, "Color": 0.5, "Size": None}


def test_parse_answer_confidence_clamping() -> None:
    answer = (
        '{"values": {"Name": "Widget", "Color": "Red"}, "confidence": {"Name": 1.5, "Color": -0.5}}'
    )
    fields = ["Name", "Color"]

    result, conf = parse_answer(answer, fields)

    assert result == {"Name": "Widget", "Color": "Red"}
    assert conf == {"Name": 1.0, "Color": 0.0}


def test_parse_answer_invalid_confidence_type() -> None:
    answer = '{"values": {"Name": "Widget"}, "confidence": {"Name": "high"}}'
    fields = ["Name"]

    result, conf = parse_answer(answer, fields)

    assert result == {"Name": "Widget"}
    assert conf == {"Name": None}
