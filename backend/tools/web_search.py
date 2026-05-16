import logging
from dataclasses import dataclass
from typing import Protocol, cast

import requests
from config import settings
from ddgs import DDGS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str

    def to_dict(self) -> dict[str, str]:
        return {"title": self.title, "url": self.url, "snippet": self.snippet}


class SearchProvider(Protocol):
    def search(self, query: str) -> list[SearchResult]:
        """Return normalized search results for the query."""


class TavilySearchProvider:
    def __init__(self, api_key: str, max_results: int, timeout_seconds: int) -> None:
        self.api_key = api_key
        self.max_results = max_results
        self.timeout_seconds = timeout_seconds

    def search(self, query: str) -> list[SearchResult]:
        response = requests.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "query": query,
                "search_depth": "basic",
                "include_answer": False,
                "include_raw_content": False,
                "max_results": self.max_results,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = cast(dict[str, object], response.json())
        return [
            SearchResult(
                title=_as_text(item.get("title")),
                url=_as_text(item.get("url")),
                snippet=_as_text(item.get("content")),
            )
            for item in _dict_list(payload.get("results"))
        ]


class BraveSearchProvider:
    def __init__(self, api_key: str, max_results: int, timeout_seconds: int) -> None:
        self.api_key = api_key
        self.max_results = max_results
        self.timeout_seconds = timeout_seconds

    def search(self, query: str) -> list[SearchResult]:
        params: dict[str, str | int] = {"q": query, "count": self.max_results}
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key,
            },
            params=params,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = cast(dict[str, object], response.json())
        web_payload = payload.get("web")
        if not isinstance(web_payload, dict):
            return []

        return [
            SearchResult(
                title=_as_text(item.get("title")),
                url=_as_text(item.get("url")),
                snippet=_as_text(item.get("description")),
            )
            for item in _dict_list(cast(dict[str, object], web_payload).get("results"))
        ]


class DdgsSearchProvider:
    def __init__(self, max_results: int, timeout_seconds: int, region: str) -> None:
        self.max_results = max_results
        self.timeout_seconds = timeout_seconds
        self.region = region

    def search(self, query: str) -> list[SearchResult]:
        with DDGS(timeout=self.timeout_seconds) as ddgs:
            raw_results = list(
                cast(
                    list[dict[str, object]],
                    ddgs.text(query, region=self.region, max_results=self.max_results),
                )
            )

        return [
            SearchResult(
                title=_as_text(item.get("title")),
                url=_as_text(item.get("href")),
                snippet=_as_text(item.get("body")),
            )
            for item in raw_results
        ]


class WebSearchTool:
    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        max_results: int | None = None,
        timeout_seconds: int | None = None,
        region: str | None = None,
        enabled: bool | None = None,
    ) -> None:
        self.enabled = settings.web_search_enabled if enabled is None else enabled
        self.provider_name = (provider or settings.web_search_provider).strip().lower()
        self.api_key = settings.web_search_api_key if api_key is None else api_key
        self.max_results = max_results or settings.web_search_max_results
        self.timeout_seconds = timeout_seconds or settings.web_search_timeout_seconds
        self.region = region or settings.web_search_region

    def search(self, query: str) -> list[SearchResult]:
        if not self.enabled:
            return []

        try:
            return self._provider().search(query)
        except Exception as exc:
            logger.warning("Web search failed for query %r: %s", query, exc)
            return []

    def _provider(self) -> SearchProvider:
        if self.provider_name == "tavily" and self.api_key:
            return TavilySearchProvider(self.api_key, self.max_results, self.timeout_seconds)
        if self.provider_name == "brave" and self.api_key:
            return BraveSearchProvider(self.api_key, self.max_results, self.timeout_seconds)

        if self.provider_name in {"tavily", "brave"} and not self.api_key:
            logger.info("WEB_SEARCH_API_KEY is empty; falling back to DDGS search")
        elif self.provider_name != "ddgs":
            logger.warning(
                "Unknown web search provider %r; falling back to DDGS",
                self.provider_name,
            )

        return DdgsSearchProvider(self.max_results, self.timeout_seconds, self.region)


def format_search_context(results: list[SearchResult]) -> str:
    if not results:
        return "No web search results were found."

    return "\n".join(
        f"{index}. {result.title}\nURL: {result.url}\nSnippet: {result.snippet}"
        for index, result in enumerate(results, start=1)
    )


def format_sources(results: list[SearchResult]) -> str:
    urls = [result.url for result in results if result.url]
    return "\n".join(dict.fromkeys(urls)) if urls else "Not found"


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [cast(dict[str, object], item) for item in value if isinstance(item, dict)]


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)
