"""Application settings loaded from environment / .env."""
from __future__ import annotations

import os
import sys
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


PLACEHOLDER_SECRETS = {
    "",
    "change-this-to-a-long-random-string-in-production",
    "CHANGE_ME",
    "changeme",
}


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/ai_receptionist.db"
    secret_key: str = "change-this-to-a-long-random-string-in-production"
    admin_username: str = ""
    admin_password: str = ""
    https_only: bool = False
    setup_token: str = ""

    # Opt-in public product demo. False unless explicitly enabled.
    demo_mode: bool = False
    demo_seed: str = "review-demo-v1"
    demo_max_sessions: int = 200

    ai_base_url: str = ""
    ai_api_key: Optional[str] = None
    ai_model: str = ""

    business_name: str = "My Business"
    business_timezone: str = "Asia/Dhaka"

    # Rate limits (overridable via env)
    login_max_attempts: int = 10
    login_window_sec: int = 300
    chat_max_attempts: int = 30
    chat_window_sec: int = 60
    chat_message_max_length: int = 2000

    # Pagination defaults
    page_size: int = 25

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def _testing() -> bool:
    return os.environ.get("FRONTDESK_TESTING", "").strip().lower() in {"1", "true", "yes"}


def secret_key_is_placeholder(value: str | None = None) -> bool:
    key = settings.secret_key if value is None else value
    return (key or "").strip() in PLACEHOLDER_SECRETS


def admin_password_is_unset() -> bool:
    return not (settings.admin_password or "").strip() or settings.admin_password.strip() in {
        "CHANGE_ME",
        "change-me",
        "admin123",
    }


def enforce_secret_key() -> None:
    """Refuse to start with an empty or placeholder SECRET_KEY outside tests."""
    if _testing():
        return
    if secret_key_is_placeholder():
        msg = (
            "SECRET_KEY is empty or still the placeholder value. "
            "Generate one with:\n"
            '  python -c "import secrets; print(secrets.token_urlsafe(48))"\n'
            "Then set SECRET_KEY in .env (or the process environment) and restart. "
            "For automated tests set FRONTDESK_TESTING=1."
        )
        print(msg, file=sys.stderr)
        raise SystemExit(msg)


settings = Settings()
