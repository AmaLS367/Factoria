import json
import sys
from typing import Any, cast

import cli
import main as batch_main
import pytest
import requests
from agents.research_agent import ResearchAgent, ensure_sources_field
from promts.generator import generate_prompt
from tools import web_search
from tools.web_search import SearchResult, WebSearchTool


class DummyResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.payload


class FakeLlmClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def get_answer(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return json.dumps({"Name": "Widget", "Sources": "Not found"})


class FakeSearchTool:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def search(self, query: str) -> list[SearchResult]:
        self.queries.append(query)
        return [
            SearchResult(
                title="Widget datasheet",
                url="https://example.com/widget",
                snippet="Official widget data",
            )
        ]


def test_web_search_falls_back_to_ddgs_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_search(self: web_search.DdgsSearchProvider, query: str) -> list[SearchResult]:
        assert query == "ABC-123"
        return [SearchResult(title="Result", url="https://example.com", snippet="Snippet")]

    monkeypatch.setattr(web_search.DdgsSearchProvider, "search", fake_search)

    results = WebSearchTool(provider="tavily", api_key="", enabled=True).search("ABC-123")

    assert results == [SearchResult(title="Result", url="https://example.com", snippet="Snippet")]


def test_tavily_provider_normalizes_results(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(*args: object, **kwargs: object) -> DummyResponse:
        assert kwargs["headers"] == {"Authorization": "Bearer key"}
        return DummyResponse(
            {
                "results": [
                    {
                        "title": "Part page",
                        "url": "https://example.com/part",
                        "content": "Part details",
                    }
                ]
            }
        )

    monkeypatch.setattr(requests, "post", fake_post)

    results = web_search.TavilySearchProvider("key", 5, 10).search("part")

    assert results == [
        SearchResult(
            title="Part page",
            url="https://example.com/part",
            snippet="Part details",
        )
    ]


def test_brave_provider_normalizes_results(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(*args: object, **kwargs: object) -> DummyResponse:
        assert kwargs["headers"] == {
            "Accept": "application/json",
            "X-Subscription-Token": "key",
        }
        return DummyResponse(
            {
                "web": {
                    "results": [
                        {
                            "title": "Part result",
                            "url": "https://example.com/brave",
                            "description": "Brave snippet",
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr(requests, "get", fake_get)

    results = web_search.BraveSearchProvider("key", 5, 10).search("part")

    assert results == [
        SearchResult(
            title="Part result",
            url="https://example.com/brave",
            snippet="Brave snippet",
        )
    ]


def test_ddgs_provider_normalizes_results(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDdgs:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        def __enter__(self) -> "FakeDdgs":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def text(
            self,
            query: str,
            region: str,
            max_results: int,
        ) -> list[dict[str, object]]:
            assert query == "part"
            assert region == "wt-wt"
            assert max_results == 5
            return [{"title": "DDGS", "href": "https://example.com/ddgs", "body": "Body"}]

    monkeypatch.setattr(web_search, "DDGS", FakeDdgs)

    results = web_search.DdgsSearchProvider(5, 10, "wt-wt").search("part")

    assert results == [
        SearchResult(title="DDGS", url="https://example.com/ddgs", snippet="Body")
    ]


def test_prompt_includes_web_context_and_sources_field() -> None:
    prompt = generate_prompt(
        item_id="ABC-123",
        item_label="spare part",
        fields=["Name", "Sources"],
        web_context="1. Source\nURL: https://example.com\nSnippet: details",
    )

    assert "Use this web search context as the primary evidence" in prompt
    assert "Sources" in prompt
    assert "https://example.com" in prompt


def test_cli_search_mode_outputs_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FakeWebSearchTool:
        def search(self, query: str) -> list[SearchResult]:
            assert "ABC-123" in query
            return [SearchResult(title="Title", url="https://example.com", snippet="Text")]

    monkeypatch.setattr(cli, "WebSearchTool", FakeWebSearchTool)
    monkeypatch.setattr(sys, "argv", ["cli.py", "--search", "ABC-123"])

    cli.main()

    output = json.loads(capsys.readouterr().out)
    assert output == [{"title": "Title", "url": "https://example.com", "snippet": "Text"}]


def test_research_agent_searches_before_llm() -> None:
    llm_client = FakeLlmClient()
    search_tool = FakeSearchTool()

    result = ResearchAgent(llm_client=llm_client, search_tool=search_tool).collect_item(
        "ABC-123",
        ["Name"],
    )

    assert search_tool.queries
    assert "ABC-123" in search_tool.queries[0]
    assert "https://example.com/widget" in llm_client.prompts[0]
    assert result["Sources"] == "https://example.com/widget"


def test_failed_search_does_not_block_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_search(self: web_search.DdgsSearchProvider, query: str) -> list[SearchResult]:
        raise TimeoutError("network timeout")

    monkeypatch.setattr(web_search.DdgsSearchProvider, "search", failing_search)

    result = ResearchAgent(
        llm_client=FakeLlmClient(),
        search_tool=WebSearchTool(provider="ddgs", enabled=True),
    ).collect_item("ABC-123", ["Name"])

    assert result["Name"] == "Widget"
    assert result["Sources"] == "Not found"


def test_batch_main_uses_research_agent_and_persists_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_module = cast(Any, batch_main)
    saved: list[tuple[str, ...]] = []
    initialized_fields: list[str] = []

    class FakeResearchAgent:
        def collect_item(self, item_id: str, fields: list[str] | None = None) -> dict[str, str]:
            assert fields == ["Name", "Sources"]
            return {"Name": f"Name {item_id}", "Sources": "https://example.com"}

    monkeypatch.setattr(batch_module.settings, "target_fields", ["Name"])
    monkeypatch.setattr(batch_module.settings, "column_name", "Part Number")
    monkeypatch.setattr(batch_module.settings, "batch_size", 10)
    monkeypatch.setattr(
        batch_module.pd,
        "read_excel",
        lambda *args, **kwargs: batch_module.pd.DataFrame({"Part Number": ["ABC-123"]}),
    )
    monkeypatch.setattr(batch_main, "ResearchAgent", FakeResearchAgent)
    monkeypatch.setattr(batch_main, "detail_exists", lambda item_id: False)
    monkeypatch.setattr(batch_main, "init_db", lambda fields: initialized_fields.extend(fields))
    monkeypatch.setattr(batch_main, "save_results_bulk", lambda data, fields: saved.extend(data))
    monkeypatch.setattr(batch_main, "fetch_all", lambda: None)
    monkeypatch.setattr(batch_main, "format_output_excel", lambda filepath, df: None)

    batch_main.main()

    assert initialized_fields == ensure_sources_field(["Name"])
    assert saved == [("ABC-123", "Name ABC-123", "https://example.com")]
