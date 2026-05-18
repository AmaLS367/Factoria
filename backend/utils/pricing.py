from backend.config import settings

_PRICE_TABLE: dict[str, tuple[float, float]] = {
    # OpenAI flagship / specialized text models. Prices are standard short-context USD per 1K tokens
    "gpt-5.5-pro": (0.030000, 0.180000),
    "gpt-5.5": (0.005000, 0.030000),
    "gpt-5.4-pro": (0.030000, 0.180000),
    "gpt-5.4-mini": (0.000750, 0.004500),
    "gpt-5.4-nano": (0.000200, 0.001250),
    "gpt-5.4": (0.002500, 0.015000),
    "gpt-5.3-codex": (0.001750, 0.014000),
    "gpt-5.2-pro": (0.021000, 0.168000),
    "gpt-5.2": (0.001750, 0.014000),
    "gpt-4o-mini": (0.000150, 0.000600),
    "gpt-4o": (0.002500, 0.010000),
    "gpt-4-turbo": (0.010000, 0.030000),
    "gpt-4": (0.030000, 0.060000),
    "gpt-3.5-turbo": (0.000500, 0.001500),
    # DeepSeek official API. deepseek-chat/reasoner are compatibility aliases for V4 Flash.
    "deepseek-v4-flash": (0.000140, 0.000280),
    # Current discounted V4 Pro rate as published by DeepSeek until 2026-05-31.
    "deepseek-v4-pro": (0.000435, 0.000870),
    "deepseek-chat": (0.000140, 0.000280),
    "deepseek-reasoner": (0.000140, 0.000280),
    "deepseek-coder": (0.000140, 0.000280),
    # Google Gemini Developer API standard text/image/video token prices.
    "gemini-3.1-pro-preview": (0.002000, 0.012000),
    "gemini-3.1-flash-lite-preview": (0.000250, 0.001500),
    "gemini-3.1-flash-lite": (0.000250, 0.001500),
    "gemini-3-flash-preview": (0.000500, 0.003000),
    "gemini-3-pro-image-preview": (0.002000, 0.012000),
    "gemini-2.5-pro": (0.001250, 0.010000),
    "gemini-2.5-flash-lite-preview": (0.000100, 0.000400),
    "gemini-2.5-flash-lite": (0.000100, 0.000400),
    "gemini-2.5-flash": (0.000300, 0.002500),
    "gemini-2.0-flash-lite": (0.000075, 0.000300),
    "gemini-2.0-flash": (0.000100, 0.000400),
    "gemini-1.5-flash": (0.000075, 0.000300),
    "gemini-1.5-pro": (0.001250, 0.005000),
    # Anthropic Claude 1P API base input/output token prices.
    "claude-opus-4-7": (0.005000, 0.025000),
    "claude-opus-4.7": (0.005000, 0.025000),
    "claude-opus-4-6": (0.005000, 0.025000),
    "claude-opus-4.6": (0.005000, 0.025000),
    "claude-opus-4-5": (0.005000, 0.025000),
    "claude-opus-4.5": (0.005000, 0.025000),
    "claude-opus-4-1": (0.015000, 0.075000),
    "claude-opus-4.1": (0.015000, 0.075000),
    "claude-opus-4": (0.015000, 0.075000),
    "claude-sonnet-4-6": (0.003000, 0.015000),
    "claude-sonnet-4.6": (0.003000, 0.015000),
    "claude-sonnet-4-5": (0.003000, 0.015000),
    "claude-sonnet-4.5": (0.003000, 0.015000),
    "claude-sonnet-4": (0.003000, 0.015000),
    "claude-3-7-sonnet": (0.003000, 0.015000),
    "claude-haiku-4-5": (0.001000, 0.005000),
    "claude-haiku-4.5": (0.001000, 0.005000),
    "claude-3-5-haiku": (0.000800, 0.004000),
    "claude-3-opus": (0.015000, 0.075000),
    "claude-3-haiku": (0.000250, 0.001250),
    # Local/open models are usually free at the API layer when served locally.
    "llama": (0.0, 0.0),
    "mistral": (0.0, 0.0),
    "qwen": (0.0, 0.0),
}


def get_price_per_1k(model: str) -> tuple[float, float]:
    """Return input/output USD per 1k tokens for a model."""
    lower = model.lower()
    for key, prices in _PRICE_TABLE.items():
        if key in lower:
            return prices
    return settings.llm_cost_per_1k_input_tokens, settings.llm_cost_per_1k_output_tokens


def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    input_price, output_price = get_price_per_1k(model)
    return round(
        (prompt_tokens / 1000) * input_price + (completion_tokens / 1000) * output_price,
        8,
    )
