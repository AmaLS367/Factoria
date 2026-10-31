import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, cast

import requests
from ddgs import DDGS

from backend.config import settings
from backend.utils.cache import get_cache, make_cache_key, set_cache
from backend.utils.retry import with_retry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    """Normalized web search result containing a title, URL, and snippet."""

    title: str
    url: str
    snippet: str

    def to_dict(self) -> dict[str, str]:
        """Serialize this result.

        Returns:
            Dictionary with title, url, and snippet keys.
        """
        return {"title": self.title, "url": self.url, "snippet": self.snippet}


class SearchProvider(Protocol):
    """Protocol for implementations that return normalized search results."""

    def search(self, query: str) -> list[SearchResult]:
        """Return normalized search results for the query."""


class ApiSearchProvider(ABC):
    """Base class for API-based search providers requiring an API key."""

    def __init__(self, api_key: str, max_results: int, timeout_seconds: int) -> None:
        """Configure an API provider.

        Args:
            api_key: Credential sent with provider requests.
            max_results: Maximum results requested from the API.
            timeout_seconds: HTTP request timeout.
        """
        self.api_key = api_key
        self.max_results = max_results
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def search(self, query: str) -> list[SearchResult]:
        """Return normalized search results for the query."""


class TavilySearchProvider(ApiSearchProvider):
    """Search provider backed by the Tavily API."""

    def search(self, query: str) -> list[SearchResult]:
        """Search for a query and normalize the provider response.

        Args:
            query: Search phrase sent to the provider.

        Returns:
            Normalized results returned by Tavily.
        """
        def _call_api() -> requests.Response:
            """Send one HTTP search request and return its successful response."""
            res = requests.post(
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
            res.raise_for_status()
            return res

        response = with_retry(
            _call_api,
            max_attempts=settings.retry_max_attempts,
            base_delay=settings.retry_base_delay_seconds,
            max_delay=settings.retry_max_delay_seconds,
            label="search/tavily",
        )
        payload = cast(dict[str, object], response.json())
        return [
            SearchResult(
                title=_as_text(item.get("title")),
                url=_as_text(item.get("url")),
                snippet=_as_text(item.get("content")),
            )
            for item in _dict_list(payload.get("results"))
        ]


class BraveSearchProvider(ApiSearchProvider):
    """Search provider backed by the Brave Search API."""

    def search(self, query: str) -> list[SearchResult]:
        """Search for a query and normalize the provider response.

        Args:
            query: Search phrase sent to the provider.

        Returns:
            Normalized results returned by Brave Search.
        """
        params: dict[str, str | int] = {"q": query, "count": self.max_results}

        def _call_api() -> requests.Response:
            """Send one HTTP search request and return its successful response."""
            res = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self.api_key,
                },
                params=params,
                timeout=self.timeout_seconds,
            )
            res.raise_for_status()
            return res

        response = with_retry(
            _call_api,
            max_attempts=settings.retry_max_attempts,
            base_delay=settings.retry_base_delay_seconds,
            max_delay=settings.retry_max_delay_seconds,
            label="search/brave",
        )
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
    """Search provider backed by the DuckDuckGo search package."""

    def __init__(self, max_results: int, timeout_seconds: int, region: str) -> None:
        """Configure DuckDuckGo search limits.

        Args:
            max_results: Maximum results requested for each query.
            timeout_seconds: Search request timeout.
            region: DuckDuckGo region code.
        """
        self.max_results = max_results
        self.timeout_seconds = timeout_seconds
        self.region = region

    def search(self, query: str) -> list[SearchResult]:
        """Search for a query and normalize the provider response.

        Args:
            query: Search phrase sent to the provider.

        Returns:
            Normalized results returned by DuckDuckGo.
        """
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
    """Search facade that applies settings, caching, and provider fallback."""

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        max_results: int | None = None,
        timeout_seconds: int | None = None,
        region: str | None = None,
        enabled: bool | None = None,
    ) -> None:
        """Resolve search settings and optional per-instance overrides.

        Args:
            provider: Search provider name; defaults to the configured provider.
            api_key: Provider credential; defaults to the configured search key.
            max_results: Maximum results per query; defaults to the configured limit.
            timeout_seconds: Request timeout; defaults to the configured timeout.
            region: Search region; defaults to the configured region.
            enabled: Whether searching is enabled; defaults to the configured flag.
        """
        self.enabled = settings.web_search_enabled if enabled is None else enabled
        self.provider_name = (provider or settings.web_search_provider).strip().lower()
        self.api_key = settings.web_search_api_key if api_key is None else api_key
        self.max_results = max_results or settings.web_search_max_results
        self.timeout_seconds = timeout_seconds or settings.web_search_timeout_seconds
        self.region = region or settings.web_search_region

    def search(self, query: str) -> list[SearchResult]:
        """Search using the selected provider, optionally caching successful results.

        Args:
            query: Search phrase sent to the provider.

        Returns:
            Normalized results, or an empty list when disabled or when any search error occurs.
        """
        if not self.enabled:
            return []

        try:
            if not settings.cache_enabled or not settings.cache_web_search_enabled:
                return self._provider().search(query)

            provider_instance = self._provider()
            provider_name = provider_instance.__class__.__name__
            payload = {
                "query": query,
                "region": self.region,
                "max_results": self.max_results,
            }
            cache_key = make_cache_key("web_search", provider_name, "N/A", payload)

            cached_results = get_cache(cache_key)
            if cached_results is not None:
                logger.info(f"Web search cache hit for query: {query}")
                return [SearchResult(**cast(dict[str, str], r)) for r in cached_results]

            logger.info(f"Web search cache miss for query: {query}")
            results = provider_instance.search(query)

            if results:
                results_dict = [r.to_dict() for r in results]
                set_cache(
                    cache_key=cache_key,
                    kind="web_search",
                    provider=provider_name,
                    model="N/A",
                    payload=results_dict,
                    ttl_days=settings.cache_web_search_ttl_days,
                )

            return results
        except Exception as exc:
            logger.warning("Web search failed for query %r: %s", query, exc)
            return []

    def _provider(self) -> SearchProvider:
        """Instantiate the selected provider, falling back to DDGS if needed.

        Returns:
            Search provider configured with the current limits and credentials.
        """
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
    """Format results as numbered evidence for an LLM prompt.

    Args:
        results: Search results to include.

    Returns:
        Formatted evidence text, or a no-results message.
    """
    if not results:
        return "No web search results were found."

    return "\n".join(
        f"{index}. {result.title}\nURL: {result.url}\nSnippet: {result.snippet}"
        for index, result in enumerate(results, start=1)
    )


def format_sources(results: list[SearchResult]) -> str:
    """Join unique non-empty result URLs.

    Args:
        results: Search results whose URLs should be retained.

    Returns:
        Newline-separated URLs, or ``Not found`` when none are available.
    """
    urls = [result.url for result in results if result.url]
    return "\n".join(dict.fromkeys(urls)) if urls else "Not found"


def _dict_list(value: object) -> list[dict[str, object]]:
    """Filter a possibly malformed API value to dictionary elements.

    Args:
        value: Value returned by a search API.

    Returns:
        Dictionary elements if value is a list; otherwise an empty list.
    """
    if not isinstance(value, list):
        return []
    return [cast(dict[str, object], item) for item in value if isinstance(item, dict)]


def _as_text(value: object) -> str:
    """Convert an API value to a string, mapping ``None`` to an empty string.

    Args:
        value: Value returned by a search API.

    Returns:
        String representation or an empty string.
    """
    if value is None:
        return ""
    return str(value)
