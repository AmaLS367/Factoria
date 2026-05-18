import logging
from abc import ABC, abstractmethod
from typing import Any, cast

import requests
from openai import OpenAI

from backend.config import settings
from backend.utils.pricing import estimate_cost
from backend.utils.retry import with_retry
from backend.utils.schemas import TokenUsage

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    @abstractmethod
    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        pass


class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=settings.resolved_llm_api_key,
            base_url=settings.resolved_llm_base_url,
        )
        self.model_name = settings.resolved_llm_model

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        def _call() -> tuple[str, TokenUsage]:
            try:
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
                usage = response.usage
                pt = (usage.prompt_tokens or 0) if usage else 0
                ct = (usage.completion_tokens or 0) if usage else 0
                cost = estimate_cost(pt, ct, self.model_name)
                return text, TokenUsage(
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    total_tokens=pt + ct,
                    estimated_cost_usd=cost,
                )
            except Exception:
                return "", TokenUsage()

        try:
            return with_retry(
                _call,
                max_attempts=settings.retry_max_attempts,
                base_delay=settings.retry_base_delay_seconds,
                max_delay=settings.retry_max_delay_seconds,
                label="llm/openai",
            )
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return "", TokenUsage()


class GeminiProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.api_key = settings.resolved_llm_api_key
        self.model_name = settings.resolved_llm_model
        self.base_url = settings.resolved_llm_base_url

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        url = f"{self.base_url.rstrip('/')}/{self.model_name}:generateContent?key={self.api_key}"

        payload: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": settings.system_prompt}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1},
        }

        def _call() -> tuple[str, TokenUsage]:
            try:
                response = requests.post(
                    url, json=payload, timeout=settings.resolved_llm_timeout_seconds
                )
                response.raise_for_status()
                data = response.json()
                meta = data.get("usageMetadata", {})
                pt = meta.get("promptTokenCount", 0) or 0
                ct = meta.get("candidatesTokenCount", 0) or 0
                cost = estimate_cost(pt, ct, self.model_name)
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    text = cast(str, text)
                except (KeyError, IndexError):
                    logger.error(f"Unexpected Gemini API response structure: {data}")
                    text = ""
                return text, TokenUsage(
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    total_tokens=meta.get("totalTokenCount", pt + ct) or (pt + ct),
                    estimated_cost_usd=cost,
                )
            except Exception:
                return "", TokenUsage()

        try:
            return with_retry(
                _call,
                max_attempts=settings.retry_max_attempts,
                base_delay=settings.retry_base_delay_seconds,
                max_delay=settings.retry_max_delay_seconds,
                label="llm/gemini",
            )
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return "", TokenUsage()


class OllamaProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.base_url = settings.resolved_llm_base_url
        self.model_name = settings.resolved_llm_model

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
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
            try:
                response = requests.post(
                    url, json=payload, timeout=settings.resolved_llm_timeout_seconds
                )
                response.raise_for_status()
                data = response.json()
                text = cast(str, data.get("message", {}).get("content", ""))
                pt = data.get("prompt_eval_count", 0) or 0
                ct = data.get("eval_count", 0) or 0
                return text, TokenUsage(
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    total_tokens=pt + ct,
                    estimated_cost_usd=0.0,
                )
            except Exception:
                return "", TokenUsage()

        try:
            return with_retry(
                _call,
                max_attempts=settings.retry_max_attempts,
                base_delay=settings.retry_base_delay_seconds,
                max_delay=settings.retry_max_delay_seconds,
                label="llm/ollama",
            )
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return "", TokenUsage()


class LLMClient:
    provider: BaseLLMProvider

    def __init__(self) -> None:
        provider_name = settings.resolved_llm_provider

        provider_map: dict[str, type[BaseLLMProvider]] = {
            "gemini": GeminiProvider,
            "ollama": OllamaProvider,
        }

        provider_class = provider_map.get(provider_name, OpenAICompatibleProvider)
        self.provider = provider_class()

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        """
        Sends a prompt to the LLM and returns the text response.
        """
        return self.provider.get_answer(prompt)
