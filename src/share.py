from __future__ import annotations

from urllib.parse import quote

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions

from .promo import PROMO_DESCRIPTION, PROMO_TITLE, bot_telegram_url


def build_share_post_text(*, bot_username: str, bot_name: str | None = None) -> str:
    link = bot_telegram_url(bot_username)
    return (
        f"🔧 {PROMO_TITLE}\n"
        "\n"
        f"{PROMO_DESCRIPTION}\n"
        f"\n👉 {link}"
    )


def build_share_keyboard(*, bot_username: str, post_text: str) -> InlineKeyboardMarkup:
    link = bot_telegram_url(bot_username)
    share_dialog_url = (
        "https://t.me/share/url?"
        f"url={quote(link, safe='')}&text={quote(post_text, safe='')}"
    )
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚀 Запустить бота", url=link)],
            [InlineKeyboardButton("📤 Поделиться в Telegram", url=share_dialog_url)],
        ]
    )


def share_link_preview_options() -> LinkPreviewOptions:
    return LinkPreviewOptions(
        is_disabled=False,
        prefer_large_media=True,
        show_above_text=False,
    )
