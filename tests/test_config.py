from backend.config import Settings


def test_config_fallback_to_openai_defaults() -> None:
    settings = Settings(openai_api_key="old_key", openai_base_url="old_url", model_name="old_model")

    assert settings.resolved_llm_provider == "openai-compatible"
    assert settings.resolved_llm_api_key == "old_key"
    assert settings.resolved_llm_base_url == "old_url"
    assert settings.resolved_llm_model == "old_model"
    assert settings.resolved_llm_timeout_seconds == 60


def test_config_llm_vars_take_precedence() -> None:
    settings = Settings(
        openai_api_key="old_key",
        openai_base_url="old_url",
        model_name="old_model",
        llm_provider="gemini",
        llm_api_key="new_key",
        llm_base_url="new_url",
        llm_model="new_model",
        llm_timeout_seconds=120,
    )

    assert settings.resolved_llm_provider == "gemini"
    assert settings.resolved_llm_api_key == "new_key"
    assert settings.resolved_llm_base_url == "new_url"
    assert settings.resolved_llm_model == "new_model"
    assert settings.resolved_llm_timeout_seconds == 120


def test_config_ollama_default_url() -> None:
    settings = Settings(llm_provider="ollama")

    assert settings.resolved_llm_provider == "ollama"
    assert settings.resolved_llm_base_url == "http://localhost:11434"
