from __future__ import annotations

from urllib.parse import quote

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions


def build_share_post_text(*, bot_username: str, bot_name: str | None = None) -> str:
    title = bot_name.strip() if bot_name else "Сосед"
    link = f"https://t.me/{bot_username}"
    return (
        f"🔧 {title} — ИИ-сосед по дому, авто и технике\n"
        "\n"
        "Подскажет по ремонту, сантехнике, авто и бытовой технике — "
        "по шагам, по-соседски, иногда с шуткой.\n"
        "\n"
        "Дом, машина, инструмент в сарае — пиши, разберём.\n"
        "\n"
        f"👉 {link}"
    )


def build_share_keyboard(*, bot_username: str, post_text: str) -> InlineKeyboardMarkup:
    link = f"https://t.me/{bot_username}"
    # Нативное окно «Поделиться» в Telegram (текст + ссылка с превью бота)
    share_dialog_url = (
        "https://t.me/share/url?"
        f"url={quote(link, safe='')}&text={quote(post_text, safe='')}"
    )
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚀 Открыть бота", url=link)],
            [InlineKeyboardButton("📤 Поделиться в Telegram", url=share_dialog_url)],
        ]
    )


def share_link_preview_options() -> LinkPreviewOptions:
    """Превью карточки t.me/... с описанием из BotFather."""
    return LinkPreviewOptions(
        is_disabled=False,
        prefer_large_media=True,
        show_above_text=False,
    )
