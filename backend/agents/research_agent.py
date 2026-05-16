from typing import Protocol

from clients.llm_client import LLMClient
from config import settings
from promts.generator import generate_prompt
from tools.web_search import SearchResult, WebSearchTool, format_search_context, format_sources
from utils.parse import parse_answer

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

    def collect_item(self, item_id: str, fields: list[str] | None = None) -> dict[str, str]:
        output_fields = ensure_sources_field(fields or settings.target_fields)
        query = build_search_query(item_id, settings.item_label, output_fields)
        search_results = self.search_tool.search(query)

        prompt = generate_prompt(
            item_id=item_id,
            item_label=settings.item_label,
            fields=output_fields,
            web_context=format_search_context(search_results),
        )
        raw_response = self.llm_client.get_answer(prompt)
        parsed = parse_answer(raw_response, output_fields)

        if parsed.get(SOURCES_FIELD) in {None, "", "Not found"}:
            parsed[SOURCES_FIELD] = format_sources(search_results)

        return {k: v if v is not None else "" for k, v in parsed.items()}


def ensure_sources_field(fields: list[str]) -> list[str]:
    if SOURCES_FIELD in fields:
        return fields
    return [*fields, SOURCES_FIELD]


def build_search_query(item_id: str, item_label: str, fields: list[str]) -> str:
    searchable_fields = [field for field in fields if field != SOURCES_FIELD]
    return f"{item_label} {item_id} technical information {' '.join(searchable_fields)}"
