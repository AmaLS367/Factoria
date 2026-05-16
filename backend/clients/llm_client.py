import logging
from abc import ABC, abstractmethod
from typing import Any, cast

import requests
from config import settings
from openai import OpenAI
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    @abstractmethod
    def get_answer(self, prompt: str) -> str:
        pass


class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=settings.resolved_llm_api_key,
            base_url=settings.resolved_llm_base_url,
        )
        self.model_name = settings.resolved_llm_model

    def get_answer(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": settings.system_prompt,
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for more factual responses
                timeout=settings.resolved_llm_timeout_seconds,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Error querying OpenAI-compatible API: {e}")
            return ""


class GeminiProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.api_key = settings.resolved_llm_api_key
        self.model_name = settings.resolved_llm_model
        self.base_url = settings.resolved_llm_base_url

    def get_answer(self, prompt: str) -> str:
        url = f"{self.base_url.rstrip('/')}/{self.model_name}:generateContent?key={self.api_key}"

        payload: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": settings.system_prompt}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1},
        }

        try:
            response = requests.post(
                url, json=payload, timeout=settings.resolved_llm_timeout_seconds
            )
            response.raise_for_status()
            data = response.json()

            # Navigate the Gemini response structure
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return cast(str, text)
            except (KeyError, IndexError):
                logger.error(f"Unexpected Gemini API response structure: {data}")
                return ""

        except RequestException as e:
            logger.error(f"Error querying Gemini API: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response details: {e.response.text}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error querying Gemini API: {e}")
            return ""


class OllamaProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.base_url = settings.resolved_llm_base_url
        self.model_name = settings.resolved_llm_model

    def get_answer(self, prompt: str) -> str:
        url = f"{self.base_url.rstrip('/')}/api/chat"

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": settings.system_prompt,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }

        try:
            response = requests.post(
                url, json=payload, timeout=settings.resolved_llm_timeout_seconds
            )
            response.raise_for_status()
            data = response.json()
            return cast(str, data.get("message", {}).get("content", ""))
        except RequestException as e:
            logger.error(f"Error querying Ollama API: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response details: {e.response.text}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error querying Ollama API: {e}")
            return ""


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

    def get_answer(self, prompt: str) -> str:
        """
        Sends a prompt to the LLM and returns the text response.
        """
        return self.provider.get_answer(prompt)
