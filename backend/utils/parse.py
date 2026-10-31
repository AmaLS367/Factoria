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
    """Normalize requested values and confidence scores.

    Args:
        values_raw: Raw values mapping decoded from the response.
        confidence_raw: Raw confidence mapping decoded from the response.
        fields: Field names to include in the normalized output.

    Returns:
        Value mapping with missing entries set to ``Not found`` and confidence mapping clamped to 0–1.
    """
    values: dict[str, str] = {}
    for field in fields:
        raw_val = values_raw.get(field)
        values[field] = str(raw_val) if raw_val is not None else "Not found"

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
    """Parse an LLM response and validate its required extraction shape.

    Args:
        answer: Raw text returned by the LLM; surrounding prose around a JSON object is allowed.
        fields: Field names to include in the normalized output.

    Returns:
        Normalized field values and confidence scores. Missing values become ``Not found``;
        invalid or missing confidence scores become ``None``.

    Raises:
        LLMResponseValidationError: If the response is not valid JSON or does not contain the
            required ``values`` object.
    """
    json_match = _JSON_PATTERN.search(answer)
    raw_text = json_match.group() if json_match else answer

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise LLMResponseValidationError(f"Invalid JSON: {e}") from e

    if not isinstance(data, dict):
        raise LLMResponseValidationError(f"Top-level must be an object, got {type(data).__name__}")

    try:
        validated = LLMExtractionResponse.model_validate(data)
    except ValidationError as e:
        raise LLMResponseValidationError(f"Schema validation failed: {e}") from e

    return _normalize_fields(validated.values, validated.confidence, fields)


def parse_answer(answer: str, fields: list[str]) -> tuple[dict[str, str], dict[str, float | None]]:
    """Parse current or legacy LLM response formats without raising errors.

    Args:
        answer: Raw text returned by the LLM.
        fields: Field names to include in the normalized output.

    Returns:
        Normalized value and confidence mappings. If parsing fails, values are ``Not found`` and
        confidence scores are ``None``.

    Accepts the nested ``values``/``confidence`` format and the legacy flat field mapping. This
    lenient parser is used after strict validation retries are exhausted.
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
