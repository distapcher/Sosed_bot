from __future__ import annotations

from urllib.parse import quote

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions

from .promo import PROMO_DESCRIPTION, PROMO_TITLE, bot_telegram_url


def build_share_post_text(
    *,
    bot_username: str,
    bot_name: str | None = None,
    channel_link: str,
) -> str:
    display = bot_name.strip() if bot_name else "Сосед"
    tg_link = bot_telegram_url(bot_username)
    extra_tg = "" if channel_link.rstrip("/") == tg_link.rstrip("/") else f"\n\nВ Telegram: {tg_link}"
    return (
        f"🔧 {display} — {PROMO_TITLE}\n"
        "\n"
        f"{PROMO_DESCRIPTION}\n"
        "\n"
        "Для канала вставьте ссылку ниже (будет карточка с описанием):\n"
        f"👉 {channel_link}"
        f"{extra_tg}"
    )


def build_share_keyboard(
    *,
    bot_username: str,
    post_text: str,
    channel_link: str,
) -> InlineKeyboardMarkup:
    tg_link = bot_telegram_url(bot_username)
    share_dialog_url = (
        "https://t.me/share/url?"
        f"url={quote(channel_link, safe='')}&text={quote(post_text, safe='')}"
    )
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚀 Открыть бота", url=tg_link)],
            [InlineKeyboardButton("📤 Поделиться в Telegram", url=share_dialog_url)],
        ]
    )


def share_link_preview_options() -> LinkPreviewOptions:
    return LinkPreviewOptions(
        is_disabled=False,
        prefer_large_media=True,
        show_above_text=False,
    )
