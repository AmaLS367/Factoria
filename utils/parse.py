import re

def parse_answer(answer: str) -> dict:
    fields = {
        "Название": "Не найдено",
        "Описание": "Не найдено",
        "Вес": "Не найдено",
        "Кросс-номера": "Не найдено",
        "Материал": "Не найдено",
        "Размеры": "Не найдено",
        "Применяемость": "Не найдено",
        "Взаимозаменяемость": "Не найдено",
    }

    for key in fields:
        match = re.search(rf"{key}:\s*(.*)", answer, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            fields[key] = value

    return fields
