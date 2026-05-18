import json
import logging
import re

from pydantic import ValidationError

from backend.utils.schemas import LLMExtractionResponse, LLMResponseValidationError

logger = logging.getLogger(__name__)

_JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def _normalize_fields(
    values_raw: dict[str, object], confidence_raw: dict[str, object], fields: list[str]
) -> tuple[dict[str, str], dict[str, float | None]]:
    values = {field: str(values_raw.get(field, "Not found")) for field in fields}

    confidence: dict[str, float | None] = {}
    for field in fields:
        raw = confidence_raw.get(field)
        if raw is None:
            confidence[field] = None
        else:
            try:
                val = float(raw)  # type: ignore[arg-type]
                confidence[field] = round(min(max(val, 0.0), 1.0), 3)
            except (ValueError, TypeError):
                confidence[field] = None

    return values, confidence


def parse_answer_strict(
    answer: str, fields: list[str]
) -> tuple[dict[str, str], dict[str, float | None]]:
    """
    Parses an LLM response with strict schema validation.

    Raises:
        LLMResponseValidationError: if the response is not parseable JSON or does
        not match LLMExtractionResponse (missing or non-dict "values" key).
    """
    json_match = _JSON_PATTERN.search(answer)
    raw_text = json_match.group() if json_match else answer

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise LLMResponseValidationError(f"Invalid JSON: {e}") from e

    if not isinstance(data, dict):
        raise LLMResponseValidationError(
            f"Top-level must be an object, got {type(data).__name__}"
        )

    try:
        validated = LLMExtractionResponse.model_validate(data)
    except ValidationError as e:
        raise LLMResponseValidationError(f"Schema validation failed: {e}") from e

    return _normalize_fields(validated.values, validated.confidence, fields)


def parse_answer(answer: str, fields: list[str]) -> tuple[dict[str, str], dict[str, float | None]]:
    """
    Parses LLM response. Returns (values_dict, confidence_dict).
    Supports {"values":{...}, "confidence":{...}} and legacy flat {"field": "value"}.

    Lenient: never raises. Used as a final fallback after strict validation retries
    have been exhausted.
    """
    try:
        json_match = _JSON_PATTERN.search(answer)
        data = json.loads(json_match.group() if json_match else answer)

        if isinstance(data, dict) and "values" in data and isinstance(data["values"], dict):
            values_raw = data["values"]
            confidence_candidate = data.get("confidence")
            confidence_raw = confidence_candidate if isinstance(confidence_candidate, dict) else {}
        elif isinstance(data, dict):
            # Legacy flat format
            values_raw = data
            confidence_raw = {}
        else:
            raise ValueError(f"Top-level must be a dict, got {type(data).__name__}")

        return _normalize_fields(values_raw, confidence_raw or {}, fields)

    except Exception as e:
        logger.warning(f"Failed to parse JSON response: {e}. Raw answer: {answer[:100]}...")
        return {field: "Not found" for field in fields}, {field: None for field in fields}
