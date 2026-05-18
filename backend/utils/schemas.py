from typing import Any

from pydantic import BaseModel, ConfigDict


class LLMResponseValidationError(ValueError):
    """Raised when the LLM response cannot be coerced into LLMExtractionResponse."""


class LLMExtractionResponse(BaseModel):
    """Strict schema for the LLM extract response.

    Enforces the outer shape:
        {"values": {field_name: any}, "confidence": {field_name: any}}

    Field-level type coercion (string conversion of values, float clamping of
    confidence) is handled downstream in `parse_answer_strict`. The schema
    intentionally uses ``dict[str, Any]`` so that field-level oddities (e.g. a
    confidence value of "high") are repaired rather than triggering a retry.
    """

    model_config = ConfigDict(extra="ignore")

    values: dict[str, Any]
    confidence: dict[str, Any] = {}
