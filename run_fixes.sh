#!/bin/bash
cat << 'PY_EOF' > fix_script.py
import re

with open("backend/agents/research_agent.py", "r") as f: code = f.read()
code = code.replace("accumulated_usage = accumulated_usage + attempt_usage", "")

patch1 = """        accumulated_usage = TokenUsage()

        if use_cache and cache_key:
            cached = get_cache("llm", cache_key)
            if cached:
                logger.info(f"LLM cache hit for {item_id}")
                try:
                    last_raw = cached
                    values, confidence = parse_answer_strict(last_raw, output_fields)
                    if values:
                        return self._finalize_values(values, search_results, output_fields), confidence, accumulated_usage
                except LLMResponseValidationError:
                    logger.warning(f"Cached LLM result for {item_id} is invalid; re-fetching.")

        last_raw = ""
        best_fallback: tuple[dict[str, str], dict[str, float | None]] | None = None
        for attempt in range(1, settings.llm_validation_max_attempts + 1):
            last_raw, attempt_usage = self.llm_client.get_answer(prompt)
            accumulated_usage = accumulated_usage + attempt_usage
            if not last_raw:"""

code = re.sub(r"        if use_cache and cache_key:.*?last_raw, attempt_usage = self.llm_client.get_answer\(prompt\)\n\s+if not last_raw:", patch1, code, flags=re.DOTALL)

with open("backend/agents/research_agent.py", "w") as f: f.write(code)

with open("tests/test_research_agent.py", "r") as f: code = f.read()

patch_fake_client = """class FakeLLMClient:
    def __init__(self) -> None:
        self._responses: list[str] = []

    def set_responses(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        response = self._responses.pop(0) if self._responses else ""
        return response, TokenUsage()"""
code = re.sub(r"class FakeLLMClient:.*?(?=class FakeSearchTool:)", patch_fake_client + "\n\n\n", code, flags=re.DOTALL)
with open("tests/test_research_agent.py", "w") as f: f.write(code)

with open("scripts/smoke_llm_validation.py", "r") as f: code = f.read()
if "TokenUsage" not in code:
    code = code.replace("from backend.utils.schemas import LLMExtractionResponse", "from backend.utils.schemas import LLMExtractionResponse, TokenUsage")
patch_smoke = """class ScriptedLLM:
    def __init__(self, answers: list[str]) -> None:
        self.answers = answers
        self.calls = 0

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        self.calls += 1
        ans = self.answers.pop(0) if self.answers else ""
        return ans, TokenUsage()"""
code = re.sub(r"class ScriptedLLM:.*?(?=def main)", patch_smoke + "\n\n", code, flags=re.DOTALL)
code = code.replace("values, conf = agent.collect_item_with_confidence", "values, conf, _ = agent.collect_item_with_confidence")
with open("scripts/smoke_llm_validation.py", "w") as f: f.write(code)

PY_EOF
python fix_script.py
rm fix_script.py
