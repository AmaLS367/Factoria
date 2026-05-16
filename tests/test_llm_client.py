from typing import Any
from unittest.mock import MagicMock, patch

import requests
from clients.llm_client import GeminiProvider, LLMClient


@patch("clients.llm_client.settings")
@patch("clients.llm_client.OpenAI")
def test_openai_compatible_provider(mock_openai: Any, mock_settings: Any) -> None:
    # Setup mocks
    mock_settings.resolved_llm_provider = "openai-compatible"
    mock_settings.resolved_llm_api_key = "test_key"
    mock_settings.resolved_llm_base_url = "test_url"
    mock_settings.resolved_llm_model = "test_model"
    mock_settings.resolved_llm_timeout_seconds = 60
    mock_settings.system_prompt = "system"

    mock_client_instance = MagicMock()
    mock_openai.return_value = mock_client_instance
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="openai answer"))]
    mock_client_instance.chat.completions.create.return_value = mock_response

    # Test client instantiation
    client = LLMClient()
    assert client.provider.__class__.__name__ == "OpenAICompatibleProvider"

    # Test get_answer
    answer = client.get_answer("user prompt")
    assert answer == "openai answer"
    mock_client_instance.chat.completions.create.assert_called_once_with(
        model="test_model",
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
    answer = client.get_answer("prompt")
    assert answer == ""


@patch("clients.llm_client.settings")
@patch("clients.llm_client.requests")
def test_gemini_provider(mock_requests: Any, mock_settings: Any) -> None:
    mock_settings.resolved_llm_provider = "gemini"
    mock_settings.resolved_llm_api_key = "test_key"
    mock_settings.resolved_llm_base_url = "https://generativelanguage.googleapis.com/v1beta/models"
    mock_settings.resolved_llm_model = "gemini-model"
    mock_settings.resolved_llm_timeout_seconds = 60
    mock_settings.system_prompt = "system"

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "gemini answer"}]}}]
    }
    mock_requests.post.return_value = mock_response

    client = LLMClient()
    assert client.provider.__class__.__name__ == "GeminiProvider"

    # Check default url logic
    assert isinstance(client.provider, GeminiProvider)
    assert client.provider.base_url == "https://generativelanguage.googleapis.com/v1beta/models"

    answer = client.get_answer("user prompt")
    assert answer == "gemini answer"

    mock_requests.post.assert_called_once()
    args, kwargs = mock_requests.post.call_args
    assert (
        args[0]
        == "https://generativelanguage.googleapis.com/v1beta/models/gemini-model:generateContent?key=test_key"
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
    answer = client.get_answer("user prompt")
    assert answer == ""


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
    mock_response.json.return_value = {"message": {"content": "ollama answer"}}
    mock_requests.post.return_value = mock_response

    client = LLMClient()
    assert client.provider.__class__.__name__ == "OllamaProvider"

    answer = client.get_answer("user prompt")
    assert answer == "ollama answer"

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
    answer = client.get_answer("user prompt")
    assert answer == ""
