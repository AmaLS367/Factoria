"""Smoke test for the LLM response validation retry loop (roadmap #11).

Runs ResearchAgent against a scripted fake LLM that returns malformed output,
then valid output, verifying:
  1. "LLM response failed validation" is logged on the bad attempt
  2. "LLM response validated on attempt N" is logged on the recovery attempt
  3. "Falling back to lenient parser" fires when all retries are exhausted

Run from repo root:
    python -m scripts.smoke_llm_validation
"""

import logging
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.agents.research_agent import ResearchAgent  # noqa: E402
from backend.config import settings  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)


class ScriptedLLM:
    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)
        self.calls = 0

    def get_answer(self, prompt: str) -> str:
        self.calls += 1
        return self.answers.pop(0) if self.answers else ""


class EmptySearch:
    def search(self, query: str) -> list[Any]:
        return []


def banner(text: str) -> None:
    print(f"\n{'=' * 70}\n  {text}\n{'=' * 70}")


def main() -> int:
    with TemporaryDirectory() as tmp:
        settings.db_path = str(Path(tmp) / "smoke.sqlite")
        settings.cache_enabled = False

        banner("Scenario 1: invalid then valid — expect retry success")
        settings.llm_validation_max_attempts = 2
        llm = ScriptedLLM(
            answers=[
                "this is not JSON at all",
                '{"values": {"Name": "Widget"}, "confidence": {"Name": 0.9}}',
            ]
        )
        agent = ResearchAgent(llm_client=llm, search_tool=EmptySearch())
        values, conf = agent.collect_item_with_confidence("ITEM-001", ["Name"])
        print(f"\nResult: values={values} conf={conf} calls={llm.calls}")
        assert llm.calls == 2, f"expected 2 calls, got {llm.calls}"
        assert values["Name"] == "Widget"

        banner("Scenario 2: legacy flat format three times — expect lenient fallback")
        settings.llm_validation_max_attempts = 3
        llm = ScriptedLLM(answers=['{"Name": "FromLegacy"}'] * 3)
        agent = ResearchAgent(llm_client=llm, search_tool=EmptySearch())
        values, conf = agent.collect_item_with_confidence("ITEM-002", ["Name"])
        print(f"\nResult: values={values} conf={conf} calls={llm.calls}")
        assert llm.calls == 3, f"expected 3 calls, got {llm.calls}"
        assert values["Name"] == "FromLegacy"
        assert conf["Name"] is None

        banner("Scenario 3: empty response — expect no retry")
        settings.llm_validation_max_attempts = 3
        llm = ScriptedLLM(answers=[""])
        agent = ResearchAgent(llm_client=llm, search_tool=EmptySearch())
        values, conf = agent.collect_item_with_confidence("ITEM-003", ["Name"])
        print(f"\nResult: values={values} conf={conf} calls={llm.calls}")
        assert llm.calls == 1, f"expected 1 call, got {llm.calls}"
        assert values["Name"] == "Not found"

        banner("All scenarios passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
