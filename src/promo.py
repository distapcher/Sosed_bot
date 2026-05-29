from __future__ import annotations

PROMO_TITLE = "Сосед бот — ИИ советник по дому, авто и технике"
PROMO_DESCRIPTION = (
    "По-соседски и с юмором подскажет по ремонту, сантехнике, авто и бытовой технике, "
    "а также по любым хозяйственным и жизненным вопросам. Напиши в личку — поболтаем."
)


def bot_telegram_url(bot_username: str) -> str:
    return f"https://t.me/{bot_username}"


def promo_page_url(public_base: str) -> str:
    return f"{public_base.rstrip('/')}/promo"


def promo_image_url(public_base: str) -> str:
    return f"{public_base.rstrip('/')}/static/og-card.png"
