from pathlib import Path
from typing import Any

import pytest

from backend.agents.research_agent import ResearchAgent
from backend.config import settings
from backend.utils.schemas import TokenUsage


class ScriptedLLMClient:
    """LLM stub that returns a queued sequence of answers."""

    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)
        self.calls = 0

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        self.calls += 1
        if self.answers:
            return self.answers.pop(0), TokenUsage(
                prompt_tokens=10, completion_tokens=5, total_tokens=15
            )
        # Mimic a misbehaving provider that keeps emitting the same nonsense
        return "fallback-empty", TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)


class EmptySearchTool:
    def search(self, query: str) -> list[Any]:
        return []


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "agent_test.sqlite"))
    monkeypatch.setattr(settings, "cache_enabled", False)


def test_retries_after_invalid_response_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "llm_validation_max_attempts", 2)

    llm = ScriptedLLMClient(
        answers=[
            "garbage not json",
            '{"values": {"Name": "Widget"}, "confidence": {"Name": 0.8}}',
        ]
    )
    agent = ResearchAgent(llm_client=llm, search_tool=EmptySearchTool())

    values, conf, usage = agent.collect_item_with_confidence("item-1", ["Name"])

    assert llm.calls == 2
    assert values["Name"] == "Widget"
    assert conf["Name"] == 0.8
    assert usage == TokenUsage(prompt_tokens=20, completion_tokens=10, total_tokens=30)


def test_falls_back_to_lenient_parser_after_exhausting_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "llm_validation_max_attempts", 3)

    # All three attempts return legacy flat format — strict rejects it
    legacy = '{"Name": "WidgetFromLegacy"}'
    llm = ScriptedLLMClient(answers=[legacy, legacy, legacy])
    agent = ResearchAgent(llm_client=llm, search_tool=EmptySearchTool())

    values, conf, usage = agent.collect_item_with_confidence("item-2", ["Name"])

    # Three strict attempts, all failed, then lenient parser ran on last response
    assert llm.calls == 3
    # Lenient parser accepts legacy flat format — value extracted
    assert values["Name"] == "WidgetFromLegacy"
    assert conf["Name"] is None
    assert usage == TokenUsage(prompt_tokens=30, completion_tokens=15, total_tokens=45)


def test_no_retry_on_empty_llm_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_validation_max_attempts", 3)

    llm = ScriptedLLMClient(answers=[""])
    agent = ResearchAgent(llm_client=llm, search_tool=EmptySearchTool())

    values, conf, usage = agent.collect_item_with_confidence("item-3", ["Name"])

    assert llm.calls == 1
    assert values["Name"] == "Not found"
    assert conf["Name"] is None
    assert usage == TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)


def test_max_attempts_one_disables_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_validation_max_attempts", 1)

    # First (and only) call returns invalid output; no retry
    llm = ScriptedLLMClient(answers=["totally-not-json"])
    agent = ResearchAgent(llm_client=llm, search_tool=EmptySearchTool())

    values, _, usage = agent.collect_item_with_confidence("item-4", ["Name"])

    assert llm.calls == 1
    assert values["Name"] == "Not found"
    assert usage == TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)


def test_preserves_earlier_parseable_response_when_later_attempt_garbage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression test: a later malformed retry must not discard usable
    data extracted from an earlier attempt (Codex review feedback on PR #20).
    """
    monkeypatch.setattr(settings, "llm_validation_max_attempts", 2)

    # Attempt 1: legacy flat — strict fails, lenient yields data
    # Attempt 2: pure garbage — strict fails, lenient yields nothing
    llm = ScriptedLLMClient(answers=['{"Name": "Widget"}', "garbage"])
    agent = ResearchAgent(llm_client=llm, search_tool=EmptySearchTool())

    values, _, usage = agent.collect_item_with_confidence("item-regression", ["Name"])

    assert llm.calls == 2
    # Must preserve "Widget" from attempt 1, not regress to "Not found"
    assert values["Name"] == "Widget"
    assert usage == TokenUsage(prompt_tokens=20, completion_tokens=10, total_tokens=30)


def test_first_attempt_success_does_not_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_validation_max_attempts", 3)

    llm = ScriptedLLMClient(
        answers=['{"values": {"Name": "Widget"}, "confidence": {"Name": 0.95}}']
    )
    agent = ResearchAgent(llm_client=llm, search_tool=EmptySearchTool())

    values, conf, usage = agent.collect_item_with_confidence("item-5", ["Name"])

    assert llm.calls == 1
    assert values["Name"] == "Widget"
    assert conf["Name"] == 0.95
    assert usage == TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
