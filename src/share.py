from __future__ import annotations

from urllib.parse import quote

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions

from .promo import PROMO_DESCRIPTION, PROMO_TITLE, bot_telegram_url, promo_page_url


def _share_link(*, bot_username: str, public_promo_base_url: str) -> str:
    """Для каналов лучше promo-страница с Open Graph, не голый t.me."""
    if public_promo_base_url:
        return promo_page_url(public_promo_base_url)
    return bot_telegram_url(bot_username)


def build_share_post_text(
    *,
    bot_username: str,
    bot_name: str | None = None,
    public_promo_base_url: str = "",
) -> str:
    display = bot_name.strip() if bot_name else "Сосед"
    main_link = _share_link(bot_username=bot_username, public_promo_base_url=public_promo_base_url)
    tg_link = bot_telegram_url(bot_username)
    extra_tg = "" if main_link == tg_link else f"\n\nВ Telegram: {tg_link}"
    return (
        f"🔧 {display} — {PROMO_TITLE}\n"
        "\n"
        f"{PROMO_DESCRIPTION}\n"
        "\n"
        f"👉 {main_link}"
        f"{extra_tg}"
    )


def build_share_keyboard(
    *,
    bot_username: str,
    post_text: str,
    public_promo_base_url: str = "",
) -> InlineKeyboardMarkup:
    tg_link = bot_telegram_url(bot_username)
    preview_link = _share_link(
        bot_username=bot_username,
        public_promo_base_url=public_promo_base_url,
    )
    share_dialog_url = (
        "https://t.me/share/url?"
        f"url={quote(preview_link, safe='')}&text={quote(post_text, safe='')}"
    )
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚀 Открыть бота", url=tg_link)],
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
