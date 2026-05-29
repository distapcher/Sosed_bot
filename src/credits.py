from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# callback_data для будущей оплаты
TOPUP_CALLBACK_50 = "topup:50"
TOPUP_CALLBACK_100 = "topup:100"


def is_usage_limit_reached(*, usage_cost_usd: float, balance_usd: float, limit_usd: float) -> bool:
    """Лимит исчерпан, если накопленный расход минус оплаченный баланс >= лимита."""
    if limit_usd <= 0:
        return False
    spent = usage_cost_usd - balance_usd
    return spent >= limit_usd - 1e-9


def build_paywall_text(*, limit_usd: float) -> str:
    limit_str = f"{limit_usd:.2f}".rstrip("0").rstrip(".")
    return (
        f"Сосед, бесплатный лимит на этом этапе кончился — "
        f"примерно на {limit_str} $ токенов (вход + выход) уже ушло.\n\n"
        "Пополни кредиты, чтобы продолжить советоваться:"
    )


def build_topup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("50 ₽", callback_data=TOPUP_CALLBACK_50),
                InlineKeyboardButton("100 ₽", callback_data=TOPUP_CALLBACK_100),
            ],
        ]
    )
