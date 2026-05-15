import json
import logging
import re

logger = logging.getLogger(__name__)

def parse_answer(answer: str, fields: list[str]) -> dict[str, str]:
    """
    Parses LLM response as JSON. Falls back to 'Not found' for missing fields.
    """
    try:
        # Try to find JSON block if it's wrapped in markdown
        json_match = re.search(r"\{.*\}", answer, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = json.loads(answer)

        return {field: str(data.get(field, "Not found")) for field in fields}
    except Exception as e:
        logger.warning(f"Failed to parse JSON response: {e}. Raw answer: {answer[:100]}...")
        return {field: "Not found" for field in fields}
