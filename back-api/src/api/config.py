"""Settings for the pipeline API."""

from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always resolve .env relative to this file (back-api/src/api/config.py)
# so it works regardless of the working directory
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://arhiax:arhiax@localhost:5432/arhiax_dx"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    governance_api_url: str = "http://localhost:8088"
    app_url: str = "http://localhost:3000"
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    specs_path: str = "../back/specs"
    ledger_path: str = "../back/var/evidence-ledger.jsonl"
    hic_webhook_url: str = ""
    whatsapp_business_webhook: str = ""
    dxpro_url: str = "http://localhost:8310"
    dxpro_api_key: str = ""


settings = Settings()
