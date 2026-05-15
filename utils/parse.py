import re


def parse_answer(answer: str) -> dict[str, str]:
    fields = {
        "Name": "Not found",
        "Description": "Not found",
        "Weight": "Not found",
        "Cross-references": "Not found",
        "Material": "Not found",
        "Dimensions": "Not found",
        "Applicability": "Not found",
        "Interchangeability": "Not found",
    }

    for key in fields:
        match = re.search(rf"{key}:\s*(.*)", answer, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            fields[key] = value

    return fields
