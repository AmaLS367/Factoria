def generate_prompt(
    item_id: str,
    item_label: str,
    fields: list[str],
    web_context: str | None = None,
) -> str:
    fields_str = ", ".join(fields)
    prompt = (
        f"Provide technical information for the {item_label} with ID '{item_id}'. "
        f"Collect the following fields: {fields_str}. "
        "If some information is missing, use 'Not found'. "
        "Return ONLY a JSON object with exactly two keys:\n"
        '  "values": an object where keys match the requested fields exactly,\n'
        '  "confidence": an object mapping each field to a float from 0.0 to 1.0 '
        "indicating how confident you are in each value "
        "(1.0 = certain, 0.0 = guessed or not found).\n"
        'If the "Sources" field is requested, fill it in "values" with newline-separated '
        "URLs used for the answer, and set its confidence to 1.0.\n"
        'Example: {"values": {"Name": "Widget X", "Weight": "2.5 kg"}, '
        '"confidence": {"Name": 0.95, "Weight": 0.6}}'
    )

    if web_context:
        prompt += (
            "\n\nUse this web search context as the primary evidence. "
            "Do not invent values that are not supported by the context.\n"
            f"{web_context}"
        )

    return prompt
