from __future__ import annotations

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .config import Settings


def build_welcome_text(settings: Settings, *, has_access: bool, paid_until: str | None) -> str:
    price_block = ""
    if settings.payment_enabled:
        price_block = (
            f"\n📌 <b>Подписка — {settings.payment_amount_rub:.0f} ₽ "
            f"на {settings.payment_access_days} дн.</b>\n"
        )

    access_block = ""
    if has_access and paid_until:
        shown = escape(paid_until.replace("T", " ").replace("+00:00", " UTC"))
        access_block = f"\n✅ <b>Подписка до:</b> {shown}\n"

    return (
        "🔥 <b>Сосед — подскажу по дому, машине и технике</b>\n"
        f"{price_block}"
        "\n"
        "Гремит, течёт, не заводится — пиши. Разберём по шагам, без занудства, "
        "по-соседски, иногда с шуткой.\n"
        "\n"
        "<b>С чем помогаю:</b>\n"
        "✅ Дом и квартира: кран, розетка, мебель, уборка, кухня, мелкий ремонт\n"
        "✅ Авто: уход, расходники, что стучит, подготовка к сезону\n"
        "✅ Мото, велосипед, газонокосилка, бензопила — что в сарае лежит\n"
        "✅ Бытовая техника: стиралка, холодильник, плита, пылесос\n"
        "✅ Инструмент и крепёж — что взять и куда не промахнуться\n"
        "✅ Когда можно самому, а когда лучше мастеру — скажу честно\n"
        f"{access_block}"
        "\n"
        "💡 <b>Напиши, что случилось</b> — накидаю план.\n"
        "/reset — начать разговор сначала."
    )


def build_welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="💳 Оплатить подписку", callback_data="pay_subscription")]]
    )
