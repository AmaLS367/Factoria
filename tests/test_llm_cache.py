from pathlib import Path
from typing import Any

import pytest

from backend.agents.research_agent import ResearchAgent
from backend.config import settings
from backend.utils.schemas import TokenUsage


class FakeLLMClient:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.call_count = 0

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        self.call_count += 1
        return self.answer, TokenUsage()


class FakeSearchTool:
    def search(self, query: str) -> list[Any]:
        return []


def test_llm_cache_key_changes_with_item_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "fresh_db.sqlite"))
    monkeypatch.setattr(settings, "cache_enabled", True)
    monkeypatch.setattr(settings, "cache_llm_enabled", True)

    llm1 = FakeLLMClient("")
    agent1 = ResearchAgent(llm_client=llm1, search_tool=FakeSearchTool())

    monkeypatch.setattr(settings, "item_label", "First Label")
    agent1 = ResearchAgent(llm_client=llm1, search_tool=FakeSearchTool())
    agent1.collect_item("item-1", ["field1"])
    assert llm1.call_count == 1

    # Run again with same label, should hit cache
    agent1.collect_item("item-1", ["field1"])
    assert llm1.call_count == 1  # No new calls

    # Change label, should miss cache
    monkeypatch.setattr(settings, "item_label", "Second Label")
    agent2 = ResearchAgent(llm_client=llm1, search_tool=FakeSearchTool())
    agent2.collect_item("item-1", ["field1"])
    assert llm1.call_count == 2  # New call made
