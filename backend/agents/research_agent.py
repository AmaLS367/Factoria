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
from backend.utils.parse import parse_answer

logger = logging.getLogger(__name__)

SOURCES_FIELD = "Sources"


class AnswerClient(Protocol):
    def get_answer(self, prompt: str) -> str:
        """Return an LLM answer for the prompt."""


class SearchTool(Protocol):
    def search(self, query: str) -> list[SearchResult]:
        """Return web search results for the query."""


class ResearchAgent:
    def __init__(
        self,
        llm_client: AnswerClient | None = None,
        search_tool: SearchTool | None = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()
        self.search_tool = search_tool or WebSearchTool()

    def collect_item_with_confidence(
        self, item_id: str, fields: list[str] | None = None
    ) -> tuple[dict[str, str], dict[str, float | None]]:
        output_fields = ensure_sources_field(fields or settings.target_fields)
        query = build_search_query(item_id, settings.item_label, output_fields)
        search_results = self.search_tool.search(query)

        prompt = generate_prompt(
            item_id=item_id,
            item_label=settings.item_label,
            fields=output_fields,
            web_context=format_search_context(search_results),
        )

        use_cache = settings.cache_enabled and settings.cache_llm_enabled
        provider = settings.resolved_llm_provider
        model = settings.resolved_llm_model

        values = None
        confidence: dict[str, float | None] | None = None
        cache_key = None

        if use_cache:
            payload = {
                "item_id": item_id,
                "item_label": settings.item_label,
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
                    # Legacy cache flat format
                    values = {str(k): str(v) for k, v in cached_parsed.items()}
                    confidence = {k: None for k in values}

        if values is None or confidence is None:
            raw_response = self.llm_client.get_answer(prompt)
            values, confidence = parse_answer(raw_response, output_fields)

            if use_cache and cache_key is not None:
                has_extracted_data = any(
                    v not in {None, "", "Not found"}
                    for k, v in values.items()
                    if k != SOURCES_FIELD
                )

                if has_extracted_data:
                    logger.info(f"LLM extract cache miss for item: {item_id}")
                    set_cache(
                        cache_key=cache_key,
                        kind="llm_extract",
                        provider=provider,
                        model=model,
                        payload={"values": values, "confidence": confidence},
                        ttl_days=settings.cache_llm_ttl_days,
                    )

        if values.get(SOURCES_FIELD) in {None, "", "Not found"}:
            values[SOURCES_FIELD] = format_sources(search_results)

        final_values = {k: v if v is not None else "" for k, v in values.items()}
        return final_values, confidence

    def collect_item(self, item_id: str, fields: list[str] | None = None) -> dict[str, str]:
        values, _ = self.collect_item_with_confidence(item_id, fields)
        return values


def ensure_sources_field(fields: list[str]) -> list[str]:
    if SOURCES_FIELD in fields:
        return fields
    return [*fields, SOURCES_FIELD]


def build_search_query(item_id: str, item_label: str, fields: list[str]) -> str:
    searchable_fields = [field for field in fields if field != SOURCES_FIELD]
    return f"{item_label} {item_id} technical information {' '.join(searchable_fields)}"
