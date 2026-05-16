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
        "Return ONLY a JSON object where keys match the requested fields exactly. "
        "If the Sources field is requested, fill it with source URLs used for the answer."
    )

    if web_context:
        prompt += (
            "\n\nUse this web search context as the primary evidence. "
            "Do not invent values that are not supported by the context.\n"
            f"{web_context}"
        )

    return prompt
