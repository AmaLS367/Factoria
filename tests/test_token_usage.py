import pytest

from backend.config import settings
from backend.utils.pricing import estimate_cost, get_price_per_1k
from backend.utils.schemas import TokenUsage


def test_token_usage_defaults_to_zero() -> None:
    usage = TokenUsage()

    assert usage.prompt_tokens == 0
    assert usage.completion_tokens == 0
    assert usage.total_tokens == 0
    assert usage.estimated_cost_usd == 0.0


def test_token_usage_addition_sums_usage_and_cost() -> None:
    result = TokenUsage(100, 50, 150, 0.001) + TokenUsage(200, 100, 300, 0.002)

    assert result == TokenUsage(300, 150, 450, 0.003)


def test_estimate_cost_for_known_model() -> None:
    assert estimate_cost(1000, 500, "gpt-4o-mini") == 0.00045


def test_estimate_cost_for_unknown_model_uses_config_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "llm_cost_per_1k_input_tokens", 0.0)
    monkeypatch.setattr(settings, "llm_cost_per_1k_output_tokens", 0.0)

    assert estimate_cost(0, 0, "totally-unknown-model-xyz") == 0.0


def test_get_price_per_1k_known_model() -> None:
    assert get_price_per_1k("deepseek-chat") == (0.000270, 0.001100)


def test_get_price_per_1k_matches_case_insensitive_substring() -> None:
    assert get_price_per_1k("MY-CUSTOM-GPT-4O-MINI-FINETUNED") == (0.000150, 0.000600)
