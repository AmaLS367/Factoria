with open("scripts/smoke_llm_validation.py", "r") as f: code = f.read()
code = code.replace("from backend.utils.schemas import LLMExtractionResponse", "from backend.utils.schemas import LLMExtractionResponse, TokenUsage")
code = code.replace("def get_answer(self, prompt: str) -> str:", "def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:")
code = code.replace("return self.answers.pop(0) if self.answers else \"\"", "return self.answers.pop(0) if self.answers else \"\", TokenUsage()")
code = code.replace("values, conf = agent.collect_item_with_confidence(", "values, conf, _ = agent.collect_item_with_confidence(")
with open("scripts/smoke_llm_validation.py", "w") as f: f.write(code)

with open("backend/agents/research_agent.py", "r") as f: code = f.read()
code = code.replace(
    'return self._finalize_values(values, search_results, output_fields), confidence\n',
    'return self._finalize_values(values, search_results, output_fields), confidence, accumulated_usage\n'
)
with open("backend/agents/research_agent.py", "w") as f: f.write(code)

with open("backend/api/routes.py", "r") as f: code = f.read()
code = code.replace("values, conf = agent.collect_item_with_confidence(", "values, conf, _ = agent.collect_item_with_confidence(")
with open("backend/api/routes.py", "w") as f: f.write(code)

with open("tests/test_research_agent.py", "r") as f: code = f.read()
code = code.replace("class ScriptedLLMClient:", "from backend.utils.schemas import TokenUsage\nclass ScriptedLLMClient:")
code = code.replace("def get_answer(self, prompt: str) -> str:", "def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:")
code = code.replace("return response", "return response, TokenUsage()")
code = code.replace("values, conf = agent.collect_item_with_confidence(", "values, conf, _ = agent.collect_item_with_confidence(")
code = code.replace("values, confidence = agent.collect_item_with_confidence(", "values, confidence, _ = agent.collect_item_with_confidence(")
with open("tests/test_research_agent.py", "w") as f: f.write(code)
