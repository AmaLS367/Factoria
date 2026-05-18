#!/bin/bash
# Fix tests/test_api.py pytest import
sed -i '1i import pytest' tests/test_api.py

# Fix research agent assignment return type
cat << 'PY_EOF' > patch_ra.py
import re
with open("backend/agents/research_agent.py", "r") as f:
    code = f.read()

code = code.replace(
    'return self._finalize_values(values, search_results, output_fields), confidence',
    'return self._finalize_values(values, search_results, output_fields), confidence, accumulated_usage'
)
code = code.replace(
    'return self._finalize_values(fallback_values, search_results, output_fields), {}',
    'return self._finalize_values(fallback_values, search_results, output_fields), {}, accumulated_usage'
)

with open("backend/agents/research_agent.py", "w") as f:
    f.write(code)
PY_EOF
python patch_ra.py

# Fix Mock LLM clients in scripts/smoke_llm_validation.py and tests
cat << 'PY_EOF' > patch_smoke.py
import re
with open("scripts/smoke_llm_validation.py", "r") as f:
    code = f.read()

code = code.replace('from backend.utils.schemas import LLMExtractionResponse', 'from backend.utils.schemas import LLMExtractionResponse, TokenUsage')
code = code.replace('def get_answer(self, prompt: str) -> str:', 'def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:')
code = code.replace('return response', 'return response, TokenUsage()')
with open("scripts/smoke_llm_validation.py", "w") as f:
    f.write(code)
PY_EOF
python patch_smoke.py

cat << 'PY_EOF' > patch_api_routes.py
import re
with open("backend/api/routes.py", "r") as f:
    code = f.read()
code = code.replace('values, conf = agent.collect_item_with_confidence(', 'values, conf, _ = agent.collect_item_with_confidence(')
with open("backend/api/routes.py", "w") as f:
    f.write(code)
PY_EOF
python patch_api_routes.py

cat << 'PY_EOF' > patch_tests_llm_cache.py
import re
with open("tests/test_llm_cache.py", "r") as f:
    code = f.read()
code = code.replace('FakeLLMClient()', 'FakeLLMClient("")')
code = code.replace('.calls ', '.call_count ')
with open("tests/test_llm_cache.py", "w") as f:
    f.write(code)
PY_EOF
python patch_tests_llm_cache.py

cat << 'PY_EOF' > patch_tests_ra.py
import re
with open("tests/test_research_agent.py", "r") as f:
    code = f.read()
code = code.replace('class ScriptedLLMClient:', 'from backend.utils.schemas import TokenUsage\nclass ScriptedLLMClient:')
code = code.replace('def get_answer(self, prompt: str) -> str:', 'def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:')
code = code.replace('return response', 'return response, TokenUsage()')
with open("tests/test_research_agent.py", "w") as f:
    f.write(code)
PY_EOF
python patch_tests_ra.py

rm patch_*.py
