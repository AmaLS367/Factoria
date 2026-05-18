from backend.config import settings

_PRICE_TABLE: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.000150, 0.000600),
    "gpt-4o": (0.002500, 0.010000),
    "gpt-4-turbo": (0.010000, 0.030000),
    "gpt-4": (0.030000, 0.060000),
    "gpt-3.5-turbo": (0.000500, 0.001500),
    "deepseek-chat": (0.000270, 0.001100),
    "deepseek-coder": (0.000270, 0.001100),
    "gemini-2.0-flash": (0.000075, 0.000300),
    "gemini-1.5-flash": (0.000075, 0.000300),
    "gemini-1.5-pro": (0.001250, 0.005000),
    "llama": (0.0, 0.0),
    "mistral": (0.0, 0.0),
    "qwen": (0.0, 0.0),
}


def get_price_per_1k(model: str) -> tuple[float, float]:
    """Return (input_usd_per_1k, output_usd_per_1k) for model, or config fallback."""
    lower = model.lower()
    for key, prices in _PRICE_TABLE.items():
        if key in lower:
            return prices
    return settings.llm_cost_per_1k_input_tokens, settings.llm_cost_per_1k_output_tokens


def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    inp, out = get_price_per_1k(model)
    return round((prompt_tokens / 1000) * inp + (completion_tokens / 1000) * out, 8)
