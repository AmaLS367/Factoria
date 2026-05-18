from typing import Any
from unittest.mock import MagicMock, patch

import requests
from clients.llm_client import GeminiProvider, LLMClient

from backend.utils.schemas import TokenUsage


@patch("clients.llm_client.settings")
@patch("clients.llm_client.OpenAI")
def test_openai_compatible_provider(mock_openai: Any, mock_settings: Any) -> None:
    # Setup mocks
    mock_settings.resolved_llm_provider = "openai-compatible"
    mock_settings.resolved_llm_api_key = "test_key"
    mock_settings.resolved_llm_base_url = "test_url"
    mock_settings.resolved_llm_model = "gpt-4o-mini"
    mock_settings.resolved_llm_timeout_seconds = 60
    mock_settings.system_prompt = "system"

    mock_client_instance = MagicMock()
    mock_openai.return_value = mock_client_instance
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="openai answer"))]
    mock_response.usage = MagicMock(prompt_tokens=1000, completion_tokens=500)
    mock_client_instance.chat.completions.create.return_value = mock_response

    # Test client instantiation
    client = LLMClient()
    assert client.provider.__class__.__name__ == "OpenAICompatibleProvider"

    # Test get_answer
    answer, usage = client.get_answer("user prompt")
    assert answer == "openai answer"
    assert usage == TokenUsage(
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        estimated_cost_usd=0.00045,
        llm_requests=1,
    )
    mock_client_instance.chat.completions.create.assert_called_once_with(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "system"},
            {"role": "user", "content": "user prompt"},
        ],
        temperature=0.1,
        timeout=60,
    )


@patch("clients.llm_client.settings")
@patch("clients.llm_client.OpenAI")
def test_openai_compatible_provider_error(mock_openai: Any, mock_settings: Any) -> None:
    mock_settings.resolved_llm_provider = "openai-compatible"
    mock_settings.resolved_llm_api_key = "test_key"
    mock_settings.resolved_llm_base_url = "test_url"
    mock_settings.resolved_llm_model = "test_model"
    mock_settings.resolved_llm_timeout_seconds = 60
    mock_settings.system_prompt = "system"

    mock_client_instance = MagicMock()
    mock_openai.return_value = mock_client_instance
    mock_client_instance.chat.completions.create.side_effect = Exception("API error")

    client = LLMClient()
    answer, usage = client.get_answer("prompt")
    assert answer == ""
    assert usage == TokenUsage()


@patch("clients.llm_client.settings")
@patch("clients.llm_client.requests")
def test_gemini_provider(mock_requests: Any, mock_settings: Any) -> None:
    mock_settings.resolved_llm_provider = "gemini"
    mock_settings.resolved_llm_api_key = "test_key"
    mock_settings.resolved_llm_base_url = "https://generativelanguage.googleapis.com/v1beta/models"
    mock_settings.resolved_llm_model = "gemini-1.5-flash"
    mock_settings.resolved_llm_timeout_seconds = 60
    mock_settings.system_prompt = "system"

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "gemini answer"}]}}],
        "usageMetadata": {
            "promptTokenCount": 1000,
            "candidatesTokenCount": 500,
            "totalTokenCount": 1500,
        },
    }
    mock_requests.post.return_value = mock_response

    client = LLMClient()
    assert client.provider.__class__.__name__ == "GeminiProvider"

    # Check default url logic
    assert isinstance(client.provider, GeminiProvider)
    assert client.provider.base_url == "https://generativelanguage.googleapis.com/v1beta/models"

    answer, usage = client.get_answer("user prompt")
    assert answer == "gemini answer"
    assert usage == TokenUsage(
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        estimated_cost_usd=0.000225,
        llm_requests=1,
    )

    mock_requests.post.assert_called_once()
    args, kwargs = mock_requests.post.call_args
    assert (
        args[0]
        == "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=test_key"
    )
    assert kwargs["json"]["system_instruction"]["parts"][0]["text"] == "system"
    assert kwargs["json"]["contents"][0]["parts"][0]["text"] == "user prompt"
    assert kwargs["timeout"] == 60


@patch("clients.llm_client.settings")
@patch("clients.llm_client.requests")
def test_gemini_provider_error(mock_requests: Any, mock_settings: Any) -> None:
    mock_settings.resolved_llm_provider = "gemini"
    mock_settings.resolved_llm_api_key = "test_key"
    mock_settings.resolved_llm_base_url = "https://generativelanguage.googleapis.com/v1beta/models"
    mock_settings.resolved_llm_model = "gemini-model"
    mock_settings.resolved_llm_timeout_seconds = 60
    mock_settings.system_prompt = "system"

    mock_requests.post.side_effect = requests.exceptions.RequestException("API error")

    client = LLMClient()
    answer, usage = client.get_answer("user prompt")
    assert answer == ""
    assert usage == TokenUsage()


@patch("clients.llm_client.settings")
@patch("clients.llm_client.requests")
def test_ollama_provider(mock_requests: Any, mock_settings: Any) -> None:
    mock_settings.resolved_llm_provider = "ollama"
    mock_settings.resolved_llm_api_key = ""
    mock_settings.resolved_llm_base_url = "http://localhost:11434"
    mock_settings.resolved_llm_model = "ollama-model"
    mock_settings.resolved_llm_timeout_seconds = 60
    mock_settings.system_prompt = "system"

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"content": "ollama answer"},
        "prompt_eval_count": 77,
        "eval_count": 33,
    }
    mock_requests.post.return_value = mock_response

    client = LLMClient()
    assert client.provider.__class__.__name__ == "OllamaProvider"

    answer, usage = client.get_answer("user prompt")
    assert answer == "ollama answer"
    assert usage == TokenUsage(
        prompt_tokens=77,
        completion_tokens=33,
        total_tokens=110,
        estimated_cost_usd=0.0,
        llm_requests=1,
    )

    mock_requests.post.assert_called_once()
    args, kwargs = mock_requests.post.call_args
    assert args[0] == "http://localhost:11434/api/chat"
    assert kwargs["json"]["model"] == "ollama-model"
    assert kwargs["json"]["messages"][0] == {"role": "system", "content": "system"}
    assert kwargs["json"]["messages"][1] == {"role": "user", "content": "user prompt"}
    assert kwargs["json"]["stream"] is False
    assert kwargs["timeout"] == 60


@patch("clients.llm_client.settings")
@patch("clients.llm_client.requests")
def test_ollama_provider_error(mock_requests: Any, mock_settings: Any) -> None:
    mock_settings.resolved_llm_provider = "ollama"
    mock_settings.resolved_llm_api_key = ""
    mock_settings.resolved_llm_base_url = "http://localhost:11434"
    mock_settings.resolved_llm_model = "ollama-model"
    mock_settings.resolved_llm_timeout_seconds = 60
    mock_settings.system_prompt = "system"

    mock_requests.post.side_effect = requests.exceptions.RequestException("API error")

    client = LLMClient()
    answer, usage = client.get_answer("user prompt")
    assert answer == ""
    assert usage == TokenUsage()


@patch("clients.llm_client.OpenAI")
@patch("clients.llm_client.settings")
def test_llm_client_fallback_to_openai_for_unknown_provider(
    mock_settings: Any, mock_openai: Any
) -> None:
    mock_settings.resolved_llm_provider = "unknown-provider"
    mock_settings.resolved_llm_api_key = "test_key"
    mock_settings.resolved_llm_base_url = "test_url"
    mock_settings.resolved_llm_model = "test_model"

    client = LLMClient()

    assert client.provider.__class__.__name__ == "OpenAICompatibleProvider"
    mock_openai.assert_called_once_with(api_key="test_key", base_url="test_url")
