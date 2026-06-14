"""Typed configuration loaded from environment / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # ── Meta WhatsApp Cloud API ──
    wa_verify_token: str = "change-me-verify"
    wa_app_secret: str = ""
    wa_access_token: str = ""
    wa_phone_number_id: str = ""
    wa_graph_version: str = "v21.0"

    # ── FluxVAI backend ──
    fluxvai_base_url: str = "http://localhost:8001"
    bot_service_secret: str = ""

    # ── This service ──
    bot_host: str = "0.0.0.0"
    bot_port: int = 8090
    bot_db_path: str = "./data/bot.sqlite3"

    # ── Telegram (long-polling; no tunnel needed) ──
    telegram_bot_token: str = ""
    telegram_bot_port: int = 8091
    telegram_db_path: str = "./data/telegram.sqlite3"

    # ── Generation polling ──
    poll_interval_secs: float = 5.0
    poll_timeout_secs: float = 120.0

    log_level: str = "INFO"

    @property
    def graph_base(self) -> str:
        return f"https://graph.facebook.com/{self.wa_graph_version}"

    @property
    def messages_url(self) -> str:
        return f"{self.graph_base}/{self.wa_phone_number_id}/messages"

    @property
    def telegram_api(self) -> str:
        return f"https://api.telegram.org/bot{self.telegram_bot_token}"

    @property
    def telegram_file_api(self) -> str:
        return f"https://api.telegram.org/file/bot{self.telegram_bot_token}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
