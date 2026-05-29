from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .config import Settings


def build_welcome_text(settings: Settings, *, has_access: bool, paid_until: str | None) -> str:
    price_block = ""
    if settings.payment_enabled:
        price_block = (
            f"\n📌 <b>Подписка: {settings.payment_amount_rub:.0f} ₽ "
            f"на {settings.payment_access_days} дн.</b>\n"
        )

    access_block = ""
    if has_access and paid_until:
        shown = paid_until.replace("T", " ").replace("+00:00", " UTC")
        access_block = f"\n✅ <b>Твоя подписка активна до:</b> {shown}\n"

    return (
        "🔥 <b>Сосед — твой советчик по хозяйству и быту!</b>\n"
        f"{price_block}"
        "\n"
        "🏠 <b>Чем помогу?</b>\n"
        "✅ Ремонт, сантехника, электрика — по шагам и без паники\n"
        "✅ Уборка, стирка, кухня — бытовые лайфхаки от «быстро» до «надёжно»\n"
        "✅ Мебель, инструмент, мелкий монтаж — что взять и как не накосячить\n"
        "✅ Безопасность: когда можно самому, а когда лучше мастера\n"
        "✅ Ответы с юмором, как сосед с лестничной клетки — но по делу\n"
        f"{access_block}"
        "\n"
        "💡 <b>Напиши, что стряслось</b> — разберём и сделаем план.\n"
        "Команда /reset — начать разговор с чистого листа."
    )


def build_welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="💳 Оплатить подписку", callback_data="pay_subscription")]]
    )
