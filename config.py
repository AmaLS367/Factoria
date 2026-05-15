from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    openai_api_key: str = ""
    openai_base_url: str = "https://api.deepseek.com/v1" # Default to deepseek
    model_name: str = "deepseek-chat"
    
    # Project Settings
    input_file: str = "input/input.xlsx"
    output_file: str = "results/output.xlsx"
    sheet_name: str = "Task1"
    column_name: str = "Part Number"
    batch_size: int = 1
    
    # SQLite
    db_path: str = "results/database.sqlite"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
