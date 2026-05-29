from __future__ import annotations

from dataclasses import dataclass
from os import getenv


def _int(name: str, default: int) -> int:
    raw = getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as e:
        raise ValueError(f"Env var {name} must be int, got {raw!r}") from e


def _int_env(*names: str, default: int) -> int:
    for name in names:
        raw = getenv(name)
        if raw is not None and raw != "":
            return _int(name, default)
    return default


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    max_history_messages: int
    max_output_tokens: int
    max_message_chars: int


def load_settings() -> Settings:
    telegram_bot_token = getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not telegram_bot_token:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN in environment")

    openai_api_key = getenv("OPENAI_API_KEY", "").strip()
    if not openai_api_key:
        raise ValueError("Missing OPENAI_API_KEY in environment")

    openai_base_url = getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
    openai_model = getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    if not openai_model:
        raise ValueError("OPENAI_MODEL must not be empty")

    return Settings(
        telegram_bot_token=telegram_bot_token,
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        openai_model=openai_model,
        max_history_messages=_int("MAX_HISTORY_MESSAGES", 12),
        max_output_tokens=_int("MAX_OUTPUT_TOKENS", 600),
        max_message_chars=_int_env("MAX_MESSAGE_CHARS", "MAX_REPLY_CHARS", default=1000),
    )

