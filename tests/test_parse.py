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
