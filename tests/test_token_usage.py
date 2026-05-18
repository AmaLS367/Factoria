from backend.utils.pricing import estimate_cost, get_price_per_1k
from backend.utils.schemas import TokenUsage


def test_token_usage_defaults() -> None:
    tu = TokenUsage()
    assert tu.prompt_tokens == 0
    assert tu.completion_tokens == 0
    assert tu.total_tokens == 0
    assert tu.estimated_cost_usd == 0.0


def test_token_usage_addition() -> None:
    tu1 = TokenUsage(100, 50, 150, 0.001)
    tu2 = TokenUsage(200, 100, 300, 0.002)
    tu3 = tu1 + tu2
    assert tu3.prompt_tokens == 300
    assert tu3.completion_tokens == 150
    assert tu3.total_tokens == 450
    assert tu3.estimated_cost_usd == 0.003


def test_estimate_cost_known_model() -> None:
    cost = estimate_cost(1000, 500, "gpt-4o-mini")
    assert cost == 0.00045


def test_estimate_cost_unknown_model() -> None:
    cost = estimate_cost(0, 0, "totally-unknown-model-xyz")
    assert cost == 0.0


def test_get_price_per_1k() -> None:
    assert get_price_per_1k("deepseek-chat") == (0.000270, 0.001100)
    assert get_price_per_1k("MY-CUSTOM-GPT-4O-MINI-FINETUNED") == (0.000150, 0.000600)
