import logging
from typing import Protocol

from backend.clients.llm_client import LLMClient
from backend.config import settings
from backend.promts.generator import generate_prompt
from backend.tools.web_search import (
    SearchResult,
    WebSearchTool,
    format_search_context,
    format_sources,
)
from backend.utils.cache import get_cache, make_cache_key, set_cache
from backend.utils.parse import parse_answer, parse_answer_strict
from backend.utils.schemas import LLMResponseValidationError, TokenUsage

logger = logging.getLogger(__name__)

SOURCES_FIELD = "Sources"


class AnswerClient(Protocol):
    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        """Return an LLM answer and token usage for the prompt."""


class SearchTool(Protocol):
    def search(self, query: str) -> list[SearchResult]:
        """Return web search results for the query."""


class ResearchAgent:
    def __init__(
        self,
        llm_client: AnswerClient | None = None,
        search_tool: SearchTool | None = None,
        item_label: str | None = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()
        self.search_tool = search_tool or WebSearchTool()
        self.item_label = item_label or settings.item_label

    def collect_item_with_confidence(
        self, item_id: str, fields: list[str] | None = None
    ) -> tuple[dict[str, str], dict[str, float | None], TokenUsage]:
        output_fields = ensure_sources_field(fields or settings.target_fields)
        query = build_search_query(item_id, self.item_label, output_fields)
        search_results = self.search_tool.search(query)

        prompt = generate_prompt(
            item_id=item_id,
            item_label=self.item_label,
            fields=output_fields,
            web_context=format_search_context(search_results),
        )

        use_cache = settings.cache_enabled and settings.cache_llm_enabled
        provider = settings.resolved_llm_provider
        model = settings.resolved_llm_model

        values: dict[str, str] | None = None
        confidence: dict[str, float | None] | None = None
        cache_key: str | None = None
        accumulated_usage = TokenUsage()

        if use_cache:
            values, confidence, cache_key = self._get_from_cache(
                item_id, output_fields, search_results, provider, model
            )

        if values is None or confidence is None:
            values, confidence, attempt_usage = self._execute_llm_retry_loop(
                item_id, prompt, output_fields
            )
            accumulated_usage = accumulated_usage + attempt_usage

            if use_cache and cache_key is not None:
                self._save_to_cache(cache_key, provider, model, values, confidence)

        if values.get(SOURCES_FIELD) in {None, "", "Not found"}:
            values[SOURCES_FIELD] = format_sources(search_results)

        final_values = {k: v if v is not None else "" for k, v in values.items()}
        return final_values, confidence, accumulated_usage

    def _get_from_cache(
        self,
        item_id: str,
        output_fields: list[str],
        search_results: list[SearchResult],
        provider: str,
        model: str,
    ) -> tuple[dict[str, str] | None, dict[str, float | None] | None, str]:
        payload = {
            "item_id": item_id,
            "item_label": self.item_label,
            "target_fields": output_fields,
            "search_context": [r.to_dict() for r in search_results],
            "prompt_version": "extract_v1",
            "system_prompt": settings.system_prompt,
        }

        cache_key = make_cache_key("llm_extract", provider, model, payload)
        cached_parsed = get_cache(cache_key)

        if cached_parsed is not None and isinstance(cached_parsed, dict):
            logger.info(f"LLM extract cache hit for item: {item_id}")
            if "values" in cached_parsed and "confidence" in cached_parsed:
                values = {str(k): str(v) for k, v in cached_parsed["values"].items()}
                confidence = {
                    str(k): float(v) if v is not None else None
                    for k, v in cached_parsed["confidence"].items()
                }
            else:
                values = {str(k): str(v) for k, v in cached_parsed.items()}
                confidence = {k: None for k in values}
            return values, confidence, cache_key

        return None, None, cache_key

    def _execute_llm_retry_loop(
        self, item_id: str, prompt: str, output_fields: list[str]
    ) -> tuple[dict[str, str], dict[str, float | None], TokenUsage]:
        max_attempts = max(1, settings.llm_validation_max_attempts)
        last_raw = ""
        best_fallback: tuple[dict[str, str], dict[str, float | None]] | None = None
        accumulated_usage = TokenUsage()

        values: dict[str, str] | None = None
        confidence: dict[str, float | None] | None = None

        for attempt in range(1, max_attempts + 1):
            last_raw, attempt_usage = self.llm_client.get_answer(prompt)
            accumulated_usage = accumulated_usage + attempt_usage

            if not last_raw:
                logger.warning(f"LLM returned empty response for {item_id}; skipping retry")
                break

            try:
                values, confidence = parse_answer_strict(last_raw, output_fields)
                if attempt > 1:
                    logger.info(f"LLM response validated on attempt {attempt} for {item_id}")
                break
            except LLMResponseValidationError as e:
                logger.warning(
                    f"LLM response failed validation"
                    f" (attempt {attempt}/{max_attempts}) for {item_id}: {e}"
                )

                if best_fallback is None:
                    lenient_values, lenient_conf = parse_answer(last_raw, output_fields)
                    if any(
                        v not in {None, "", "Not found"}
                        for k, v in lenient_values.items()
                        if k != SOURCES_FIELD
                    ):
                        best_fallback = (lenient_values, lenient_conf)

        if values is None or confidence is None:
            if best_fallback is not None:
                logger.warning(f"Using parseable result from earlier attempt for {item_id}")
                values, confidence = best_fallback
            else:
                logger.warning(f"Falling back to lenient parser for {item_id}")
                values, confidence = parse_answer(last_raw, output_fields)

        return values, confidence, accumulated_usage

    def _save_to_cache(
        self,
        cache_key: str,
        provider: str,
        model: str,
        values: dict[str, str],
        confidence: dict[str, float | None],
    ) -> None:
        has_extracted_data = any(
            v not in {None, "", "Not found"} for k, v in values.items() if k != SOURCES_FIELD
        )

        if has_extracted_data:
            logger.info(f"LLM extract cache miss for item: {cache_key[:10]}...")
            set_cache(
                cache_key=cache_key,
                kind="llm_extract",
                provider=provider,
                model=model,
                payload={"values": values, "confidence": confidence},
                ttl_days=settings.cache_llm_ttl_days,
            )

    def collect_item(self, item_id: str, fields: list[str] | None = None) -> dict[str, str]:
        values, _, _usage = self.collect_item_with_confidence(item_id, fields)
        return values


def ensure_sources_field(fields: list[str]) -> list[str]:
    if SOURCES_FIELD in fields:
        return fields
    return [*fields, SOURCES_FIELD]


def build_search_query(item_id: str, item_label: str, fields: list[str]) -> str:
    searchable_fields = [field for field in fields if field != SOURCES_FIELD]
    return f"{item_label} {item_id} technical information {' '.join(searchable_fields)}"
