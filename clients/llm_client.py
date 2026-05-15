from openai import OpenAI
from config import settings
import logging

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model_name = settings.model_name

    def get_answer(self, prompt: str) -> str:
        """
        Отправляет промпт к LLM и возвращает текстовый ответ.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Ты технический эксперт по автомобильным запчастям. Выдавай информацию строго по запрошенным пунктам."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1, # Низкая температура для большей фактологичности
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Ошибка при запросе к API: {e}")
            return ""
