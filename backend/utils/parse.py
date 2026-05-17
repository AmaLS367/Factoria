import json
import logging
import re

logger = logging.getLogger(__name__)

_JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def parse_answer(answer: str, fields: list[str]) -> tuple[dict[str, str], dict[str, float | None]]:
    """
    Parses LLM response. Returns (values_dict, confidence_dict).
    Supports {"values":{...}, "confidence":{...}} and legacy flat {"field": "value"}.
    """
    try:
        json_match = _JSON_PATTERN.search(answer)
        data = json.loads(json_match.group() if json_match else answer)

        if "values" in data and isinstance(data["values"], dict):
            values_raw = data["values"]
            confidence_raw = data.get("confidence", {})
        else:
            # Legacy flat format
            values_raw = data
            confidence_raw = {}

        values = {field: str(values_raw.get(field, "Not found")) for field in fields}

        confidence: dict[str, float | None] = {}
        for field in fields:
            raw = confidence_raw.get(field)
            if raw is None:
                confidence[field] = None
            else:
                try:
                    val = float(raw)
                    confidence[field] = round(min(max(val, 0.0), 1.0), 3)
                except (ValueError, TypeError):
                    confidence[field] = None

        return values, confidence

    except Exception as e:
        logger.warning(f"Failed to parse JSON response: {e}. Raw answer: {answer[:100]}...")
        return {field: "Not found" for field in fields}, {field: None for field in fields}
