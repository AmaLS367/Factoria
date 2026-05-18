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
    assert estimate_cost(1000, 500, "gpt-5.5") == 0.02


def test_estimate_cost_for_unknown_model_uses_config_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "llm_cost_per_1k_input_tokens", 0.0)
    monkeypatch.setattr(settings, "llm_cost_per_1k_output_tokens", 0.0)

    assert estimate_cost(0, 0, "totally-unknown-model-xyz") == 0.0


def test_get_price_per_1k_known_model() -> None:
    assert get_price_per_1k("deepseek-v4-flash") == (0.000140, 0.000280)


def test_get_price_per_1k_matches_case_insensitive_substring() -> None:
    assert get_price_per_1k("MY-CUSTOM-GPT-4O-MINI-FINETUNED") == (0.000150, 0.000600)


def test_get_price_per_1k_prefers_specific_model_before_prefix() -> None:
    assert get_price_per_1k("gpt-5.5-pro") == (0.030000, 0.180000)
    assert get_price_per_1k("gpt-5.5") == (0.005000, 0.030000)


def test_get_price_per_1k_current_deepseek_alias() -> None:
    assert get_price_per_1k("deepseek-chat") == (0.000140, 0.000280)
    assert get_price_per_1k("deepseek-reasoner") == (0.000140, 0.000280)


def test_get_price_per_1k_current_gemini_and_claude_models() -> None:
    assert get_price_per_1k("gemini-3.1-pro-preview") == (0.002000, 0.012000)
    assert get_price_per_1k("gemini-2.5-flash") == (0.000300, 0.002500)
    assert get_price_per_1k("claude-opus-4-7") == (0.005000, 0.025000)
    assert get_price_per_1k("claude-opus-4.7") == (0.005000, 0.025000)
    assert get_price_per_1k("claude-opus-4-1-20250805") == (
        0.015000,
        0.075000,
    )
    assert get_price_per_1k("claude-opus-4.1") == (0.015000, 0.075000)
    assert get_price_per_1k("claude-sonnet-4-6") == (0.003000, 0.015000)
    assert get_price_per_1k("claude-sonnet-4.6") == (0.003000, 0.015000)
    assert get_price_per_1k("claude-sonnet-4.5") == (0.003000, 0.015000)
