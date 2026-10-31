import logging
from abc import ABC, abstractmethod
from typing import Any, cast

import requests
from openai import OpenAI
from requests.exceptions import RequestException

from backend.config import settings
from backend.utils.pricing import estimate_cost
from backend.utils.retry import with_retry
from backend.utils.schemas import TokenUsage

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Abstract interface shared by language model providers."""

    @abstractmethod
    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        """Generate a response for a prompt using a concrete provider.

        Args:
            prompt: Prompt text to send to the provider.

        Returns:
            Generated response text and the provider-reported token usage.
        """
        pass


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider for OpenAI-compatible chat completion APIs."""

    def __init__(self) -> None:
        """Initialize the provider with application settings."""
        self.client = OpenAI(
            api_key=settings.resolved_llm_api_key,
            base_url=settings.resolved_llm_base_url,
        )
        self.model_name = settings.resolved_llm_model

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        """Send a prompt to the configured LLM provider.

        Args:
            prompt: User prompt to submit.

        Returns:
            Generated response text and token usage. Provider errors are logged and returned as empty text with zero usage.
        """
        def _call() -> tuple[str, TokenUsage]:
            """Issue one provider request and normalize its response and token usage."""
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": settings.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                timeout=settings.resolved_llm_timeout_seconds,
            )
            text = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            prompt_tokens = (getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
            completion_tokens = (getattr(usage, "completion_tokens", 0) or 0) if usage else 0
            return text, TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost_usd=estimate_cost(
                    prompt_tokens,
                    completion_tokens,
                    self.model_name,
                ),
                llm_requests=1,
            )

        try:
            return with_retry(
                _call,
                max_attempts=settings.retry_max_attempts,
                base_delay=settings.retry_base_delay_seconds,
                max_delay=settings.retry_max_delay_seconds,
                label="llm/openai",
            )
        except Exception as e:
            logger.error(f"Error querying OpenAI-compatible API: {e}")
            return "", TokenUsage()


class GeminiProvider(BaseLLMProvider):
    """Provider for the Google Gemini generateContent API."""

    def __init__(self) -> None:
        """Initialize the provider with application settings."""
        self.api_key = settings.resolved_llm_api_key
        self.model_name = settings.resolved_llm_model
        self.base_url = settings.resolved_llm_base_url

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        """Send a prompt to the configured LLM provider.

        Args:
            prompt: User prompt to submit.

        Returns:
            Generated response text and token usage. Provider errors are logged and returned as empty text with zero usage.
        """
        url = f"{self.base_url.rstrip('/')}/{self.model_name}:generateContent?key={self.api_key}"

        payload: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": settings.system_prompt}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1},
        }

        def _call() -> tuple[str, TokenUsage]:
            """Issue one provider request and normalize its response and token usage."""
            response = requests.post(
                url, json=payload, timeout=settings.resolved_llm_timeout_seconds
            )
            response.raise_for_status()
            data = response.json()
            meta = data.get("usageMetadata", {})
            prompt_tokens = meta.get("promptTokenCount", 0) or 0
            completion_tokens = meta.get("candidatesTokenCount", 0) or 0
            total_tokens = meta.get("totalTokenCount", prompt_tokens + completion_tokens) or (
                prompt_tokens + completion_tokens
            )
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                response_text = cast(str, text)
            except (KeyError, IndexError):
                logger.error(f"Unexpected Gemini API response structure: {data}")
                response_text = ""
            return response_text, TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=estimate_cost(
                    prompt_tokens,
                    completion_tokens,
                    self.model_name,
                ),
                llm_requests=1,
            )

        try:
            return with_retry(
                _call,
                max_attempts=settings.retry_max_attempts,
                base_delay=settings.retry_base_delay_seconds,
                max_delay=settings.retry_max_delay_seconds,
                label="llm/gemini",
            )
        except RequestException as e:
            logger.error(f"Error querying Gemini API: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response details: {e.response.text}")
            return "", TokenUsage()
        except Exception as e:
            logger.error(f"Unexpected error querying Gemini API: {e}")
            return "", TokenUsage()


class OllamaProvider(BaseLLMProvider):
    """Provider for a locally hosted Ollama chat API."""

    def __init__(self) -> None:
        """Initialize the provider with application settings."""
        self.base_url = settings.resolved_llm_base_url
        self.model_name = settings.resolved_llm_model

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        """Send a prompt to the configured LLM provider.

        Args:
            prompt: User prompt to submit.

        Returns:
            Generated response text and token usage. Provider errors are logged and returned as empty text with zero usage.
        """
        url = f"{self.base_url.rstrip('/')}/api/chat"

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": settings.system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }

        def _call() -> tuple[str, TokenUsage]:
            """Issue one provider request and normalize its response and token usage."""
            response = requests.post(
                url, json=payload, timeout=settings.resolved_llm_timeout_seconds
            )
            response.raise_for_status()
            data = response.json()
            text = cast(str, data.get("message", {}).get("content", ""))
            prompt_tokens = data.get("prompt_eval_count", 0) or 0
            completion_tokens = data.get("eval_count", 0) or 0
            return text, TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost_usd=0.0,
                llm_requests=1,
            )

        try:
            return with_retry(
                _call,
                max_attempts=settings.retry_max_attempts,
                base_delay=settings.retry_base_delay_seconds,
                max_delay=settings.retry_max_delay_seconds,
                label="llm/ollama",
            )
        except RequestException as e:
            logger.error(f"Error querying Ollama API: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response details: {e.response.text}")
            return "", TokenUsage()
        except Exception as e:
            logger.error(f"Unexpected error querying Ollama API: {e}")
            return "", TokenUsage()


class LLMClient:
    """Facade that selects the configured LLM provider."""

    provider: BaseLLMProvider

    def __init__(self) -> None:
        """Initialize the provider with application settings."""
        provider_name = settings.resolved_llm_provider

        provider_map: dict[str, type[BaseLLMProvider]] = {
            "gemini": GeminiProvider,
            "ollama": OllamaProvider,
        }

        provider_class = provider_map.get(provider_name, OpenAICompatibleProvider)
        self.provider = provider_class()

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        """Send a prompt through the selected provider.

        Args:
            prompt: User prompt to submit.

        Returns:
            Generated response text and token usage.
        """
        return self.provider.get_answer(prompt)
