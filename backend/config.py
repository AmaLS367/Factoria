from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Settings
    openai_api_key: str = ""
    openai_base_url: str = "https://api.deepseek.com/v1"
    model_name: str = "deepseek-chat"

    # Web Search Settings
    web_search_enabled: bool = True
    web_search_provider: str = "tavily"
    web_search_api_key: str = ""
    web_search_max_results: int = 5
    web_search_timeout_seconds: int = 10
    web_search_region: str = "wt-wt"

    # Project Settings
    input_file: str = "input/input.xlsx"
    output_file: str = "results/output.xlsx"
    sheet_name: str = "Task1"
    column_name: str = "Item ID"
    batch_size: int = 5

    # Data Collection Settings
    item_label: str = "spare part"
    target_fields: list[str] = [
        "Name",
        "Description",
        "Weight",
        "Dimensions",
        "Material",
        "Manufacturer",
        "Country of Origin",
    ]

    system_prompt: str = (
        "You are a highly professional data extraction expert. "
        "Your task is to provide accurate technical information about requested items. "
        "Return the data strictly in JSON format."
    )

    # SQLite
    db_path: str = "results/database.sqlite"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
