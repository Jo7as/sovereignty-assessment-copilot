from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    database_url: str
    # KI für die Zuordnung (Stufe 2). Ohne Schlüssel bleibt es beim Textvergleich.
    openrouter_api_key: str | None = None
    # Festgelegt von Jonas am 19.10.2026. Umschaltbar über OPENROUTER_MODEL in der .env
    openrouter_model: str = "deepseek/deepseek-v4.1-flash"
    # Adresse der Oberfläche. Nur von dort dürfen Browser die API aufrufen.
    frontend_origin: str = "http://localhost:3000"


settings = Settings()
