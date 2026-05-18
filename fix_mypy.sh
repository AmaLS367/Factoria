#!/bin/bash
cat << 'PY_EOF' > fix_script.py
import re

# 5. backend/agents/research_agent.py
with open("backend/agents/research_agent.py", "r") as f: code = f.read()
code = code.replace("from backend.utils.schemas import LLMResponseValidationError", "from backend.utils.schemas import LLMResponseValidationError, TokenUsage")
code = code.replace("def get_answer(self, prompt: str) -> str:", "def get_answer(self, prompt: str) -> tuple[str, \"TokenUsage\"]:")
code = code.replace(
    "def collect_item_with_confidence(\n        self, item_id: str, fields: list[str] | None = None\n    ) -> tuple[dict[str, str], dict[str, float | None]]:",
    "def collect_item_with_confidence(\n        self, item_id: str, fields: list[str] | None = None\n    ) -> tuple[dict[str, str], dict[str, float | None], TokenUsage]:"
)
code = code.replace(
    "def collect_item_with_confidence(self, item_id: str, fields: list[str] | None = None) -> tuple[dict[str, str], dict[str, float | None]]:",
    "def collect_item_with_confidence(self, item_id: str, fields: list[str] | None = None) -> tuple[dict[str, str], dict[str, float | None], TokenUsage]:"
)

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
            try:
                last_raw, attempt_usage = self.llm_client.get_answer(prompt)
                accumulated_usage = accumulated_usage + attempt_usage
                if not last_raw:"""

code = re.sub(r"        if use_cache and cache_key:.*?last_raw = self.llm_client.get_answer\(prompt\).*?if not last_raw:", patch1, code, flags=re.DOTALL)

patch2 = """                        if use_cache and cache_key:
                            set_cache("llm", cache_key, last_raw, ttl_days=settings.cache_llm_ttl_days)
                        return self._finalize_values(values, search_results, output_fields), confidence, accumulated_usage"""
code = re.sub(r"                        if use_cache and cache_key:\s+set_cache\(\"llm\", cache_key, last_raw, ttl_days=settings.cache_llm_ttl_days\)\s+return self\._finalize_values\(values, search_results, output_fields\), confidence", patch2, code, flags=re.DOTALL)

patch3 = """        fallback_values, fallback_conf = parse_answer(last_raw, output_fields)
        return self._finalize_values(fallback_values, search_results, output_fields), fallback_conf, accumulated_usage"""
code = re.sub(r"        fallback_values, fallback_conf = parse_answer\(last_raw, output_fields\)\s+return self\._finalize_values\(fallback_values, search_results, output_fields\), fallback_conf", patch3, code, flags=re.DOTALL)

patch4 = """    def collect_item(self, item_id: str, fields: list[str] | None = None) -> dict[str, str]:
        values, _, _usage = self.collect_item_with_confidence(item_id, fields)
        return values"""
code = re.sub(r"    def collect_item\(self, item_id: str, fields: list\[str\] \| None = None\) -> dict\[str, str\]:\s+values, _ = self\.collect_item_with_confidence\(item_id, fields\)\s+return values", patch4, code, flags=re.DOTALL)
with open("backend/agents/research_agent.py", "w") as f: f.write(code)

with open("tests/test_research_agent.py", "r") as f: code = f.read()
if "TokenUsage" not in code:
    code = code.replace("from backend.utils.schemas import LLMExtractionResponse", "from backend.utils.schemas import LLMExtractionResponse, TokenUsage")
patch_fake_client = """class FakeLLMClient:
    def __init__(self) -> None:
        self._responses: list[str] = []

    def set_responses(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        response = self._responses.pop(0) if self._responses else ""
        return response, TokenUsage()"""
code = re.sub(r"class FakeLLMClient:.*?(?=class FakeSearchTool:)", patch_fake_client + "\n\n\n", code, flags=re.DOTALL)
code = code.replace("class ScriptedLLMClient:", "from backend.utils.schemas import TokenUsage\nclass ScriptedLLMClient:")
code = code.replace("def get_answer(self, prompt: str) -> str:", "def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:")
code = code.replace("return response", "return response, TokenUsage()")
code = code.replace('return "{}"', 'return "{}", TokenUsage()')
code = code.replace('return \'{"values": {"Name": "Valid Name"}}\'', 'return \'{"values": {"Name": "Valid Name"}}\', TokenUsage()')
code = code.replace("values, conf = agent.collect_item_with_confidence", "values, conf, _ = agent.collect_item_with_confidence")
code = code.replace("values, confidence = agent.collect_item_with_confidence", "values, confidence, _ = agent.collect_item_with_confidence")
with open("tests/test_research_agent.py", "w") as f: f.write(code)

with open("scripts/smoke_llm_validation.py", "r") as f: code = f.read()
if "TokenUsage" not in code:
    code = code.replace('from backend.utils.schemas import LLMExtractionResponse', 'from backend.utils.schemas import LLMExtractionResponse, TokenUsage')
code = code.replace('def get_answer(self, prompt: str) -> str:', 'def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:')
code = code.replace('return response', 'return response, TokenUsage()')
code = code.replace("values, conf = agent.collect_item_with_confidence", "values, conf, _ = agent.collect_item_with_confidence")
with open("scripts/smoke_llm_validation.py", "w") as f: f.write(code)

with open("backend/api/routes.py", "r") as f: code = f.read()
code = code.replace("values, conf = agent.collect_item_with_confidence", "values, conf, _ = agent.collect_item_with_confidence")
with open("backend/api/routes.py", "w") as f: f.write(code)

PY_EOF
python fix_script.py
rm fix_script.py
