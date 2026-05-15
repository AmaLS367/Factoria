def generate_prompt(part_number: str) -> str:
    return (
        f"Provide technical information for the spare part with number {part_number}: exact name, "
        f"description, weight, cross-references, material, dimensions, applicability, and interchangeability. "
        f"If something is unknown, write 'Not found'. No advertising, be precise and use a bulleted list."
    )
