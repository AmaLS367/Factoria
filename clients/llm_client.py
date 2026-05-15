import logging

from openai import OpenAI

from config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model_name = settings.model_name

    def get_answer(self, prompt: str) -> str:
        """
        Sends a prompt to the LLM and returns the text response.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a technical expert in automotive spare parts. "
                            "Provide information strictly according to the requested points."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for more factual responses
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Error querying API: {e}")
            return ""
