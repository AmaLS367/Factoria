from dataclasses import dataclass
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


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    llm_requests: int = 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            estimated_cost_usd=round(self.estimated_cost_usd + other.estimated_cost_usd, 8),
            llm_requests=self.llm_requests + other.llm_requests,
        )

    @property
    def effective_llm_requests(self) -> int:
        if self.llm_requests:
            return self.llm_requests
        if (
            self.prompt_tokens
            or self.completion_tokens
            or self.total_tokens
            or self.estimated_cost_usd
        ):
            return 1
        return 0
