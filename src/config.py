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


def _float(name: str, default: float) -> float:
    raw = getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as e:
        raise ValueError(f"Env var {name} must be float, got {raw!r}") from e


def _int_env(*names: str, default: int) -> int:
    for name in names:
        raw = getenv(name)
        if raw is not None and raw != "":
            return _int(name, default)
    return default


def _bool(name: str, default: bool = False) -> bool:
    raw = getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _csv_ints(name: str) -> frozenset[int]:
    raw = getenv(name, "").strip()
    if not raw:
        return frozenset()
    result: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            result.add(int(part))
    return frozenset(result)


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    max_history_messages: int
    max_output_tokens: int
    max_message_chars: int
    stats_db_path: str
    admin_user: str
    admin_password: str
    web_host: str
    web_port: int
    cost_input_per_1m_usd: float
    cost_output_per_1m_usd: float
    payment_enabled: bool
    yookassa_shop_id: str
    yookassa_secret_key: str
    payment_amount_rub: float
    payment_access_days: int
    payment_description: str
    payment_return_url: str
    public_base_url: str
    free_telegram_user_ids: frozenset[int]


def load_settings(*, require_admin_password: bool = False) -> Settings:
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

    admin_password = getenv("ADMIN_PASSWORD", "").strip()
    if require_admin_password and not admin_password:
        raise ValueError("Missing ADMIN_PASSWORD in environment (required for web dashboard)")

    bot_username = getenv("TELEGRAM_BOT_USERNAME", "").strip().lstrip("@")
    payment_return_url = getenv("PAYMENT_RETURN_URL", "").strip()
    if not payment_return_url and bot_username:
        payment_return_url = f"https://t.me/{bot_username}"

    public_base_url = getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")

    return Settings(
        telegram_bot_token=telegram_bot_token,
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        openai_model=openai_model,
        max_history_messages=_int("MAX_HISTORY_MESSAGES", 12),
        max_output_tokens=_int("MAX_OUTPUT_TOKENS", 600),
        max_message_chars=_int_env("MAX_MESSAGE_CHARS", "MAX_REPLY_CHARS", default=1000),
        stats_db_path=getenv("STATS_DB_PATH", "/data/stats.db").strip(),
        admin_user=getenv("ADMIN_USER", "admin").strip() or "admin",
        admin_password=admin_password,
        web_host=getenv("WEB_HOST", "0.0.0.0").strip() or "0.0.0.0",
        web_port=_int("WEB_PORT", 8080),
        cost_input_per_1m_usd=_float("COST_INPUT_PER_1M_USD", 0.27),
        cost_output_per_1m_usd=_float("COST_OUTPUT_PER_1M_USD", 1.10),
        payment_enabled=_bool("PAYMENT_ENABLED", default=False),
        yookassa_shop_id=getenv("YOOKASSA_SHOP_ID", "").strip(),
        yookassa_secret_key=getenv("YOOKASSA_SECRET_KEY", "").strip(),
        payment_amount_rub=_float("PAYMENT_AMOUNT_RUB", 199.0),
        payment_access_days=_int("PAYMENT_ACCESS_DAYS", 30),
        payment_description=getenv("PAYMENT_DESCRIPTION", "Доступ к боту Сосед").strip(),
        payment_return_url=payment_return_url,
        public_base_url=public_base_url,
        free_telegram_user_ids=_csv_ints("FREE_TELEGRAM_USER_IDS"),
    )
