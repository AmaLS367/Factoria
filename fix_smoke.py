import re

with open("scripts/smoke_llm_validation.py", "r") as f: code = f.read()
if "TokenUsage" not in code:
    code = code.replace("from backend.utils.schemas import LLMExtractionResponse", "from backend.utils.schemas import LLMExtractionResponse, TokenUsage")

patch = """class ScriptedLLM:
    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)
        self.calls = 0

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        self.calls += 1
        return self.answers.pop(0) if self.answers else "", TokenUsage()"""
code = re.sub(r"class ScriptedLLM:.*?(?=def main)", patch + "\n\n", code, flags=re.DOTALL)
code = code.replace("values, conf = agent.collect_item_with_confidence", "values, conf, _ = agent.collect_item_with_confidence")

with open("scripts/smoke_llm_validation.py", "w") as f: f.write(code)
