def generate_prompt(item_id: str, item_label: str, fields: list[str]) -> str:
    fields_str = ", ".join(fields)
    return (
        f"Provide technical information for the {item_label} with ID '{item_id}'. "
        f"Collect the following fields: {fields_str}. "
        "If some information is missing, use 'Not found'. "
        "Return ONLY a JSON object where keys match the requested fields exactly."
    )
