from __future__ import annotations

import logging

from dotenv import load_dotenv
from telegram import Update, User
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import Settings, load_settings
from .credits import build_paywall_text, build_topup_keyboard, is_usage_limit_reached
from .llm import ChatMsg, build_client, chat_completion
from .memory import InMemoryHistory
from .prompts import SYSTEM_PROMPT_RU, USER_HINT
from .stats import calc_cost_usd, get_user_usage_usd, init_db, record_usage, touch_user
from .text_utils import split_reply
from .telegram_io import build_telegram_request, reply_text_retry, send_message_retry
from .share import build_share_keyboard, build_share_post_text, share_link_preview_options
from .welcome import build_welcome_text

log = logging.getLogger("sosed")


def _safe_markdown(text: str) -> str:
    return text


def _track_user(settings: Settings, user: User | None, *, increment_messages: int = 0) -> int | None:
    if user is None:
        return None

    touch_user(
        settings.stats_db_path,
        telegram_user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        increment_messages=increment_messages,
    )
    return user.id


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    log.info("cmd_start chat_id=%s user_id=%s", chat_id, user.id if user else None)

    try:
        settings: Settings = context.application.bot_data["settings"]
        try:
            _track_user(settings, user)
        except Exception:
            log.exception("stats touch_user failed in /start")

        # Короткий ответ первым — быстрее доходит при плохой сети
        await send_message_retry(context.bot, chat_id, "Здорово, сосед. На связи 👋")
        await send_message_retry(context.bot, chat_id, build_welcome_text())
        log.info("cmd_start: welcome sent to chat_id=%s", chat_id)
    except Exception:
        log.exception("cmd_start failed")
        try:
            await send_message_retry(
                context.bot,
                chat_id,
                "Сосед тут, но связь барахлит. Напиши ещё раз через минуту.",
            )
        except Exception:
            log.exception("cmd_start fallback reply failed")


async def cmd_share(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    me = await context.bot.get_me()
    username = me.username
    if not username:
        await reply_text_retry(
            update.message,
            "Не могу получить адрес бота. Попробуй позже.",
        )
        return

    post_text = build_share_post_text(bot_username=username, bot_name=me.first_name)
    await reply_text_retry(
        update.message,
        post_text,
        reply_markup=build_share_keyboard(bot_username=username, post_text=post_text),
        link_preview_options=share_link_preview_options(),
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message
    settings: Settings = context.application.bot_data["settings"]
    mem: InMemoryHistory = context.application.bot_data["mem"]
    chat_id = update.effective_chat.id if update.effective_chat else 0
    _track_user(settings, update.effective_user)
    mem.clear(chat_id)
    await reply_text_retry(update.message, "Ладно, сосед, начнём с чистого листа. Что делаем?")


async def _send_usage_limit_message(
    update: Update,
    settings: Settings,
    *,
    user_id: int,
) -> None:
    assert update.message
    usage_cost, balance = get_user_usage_usd(settings.stats_db_path, user_id)
    log.info(
        "usage limit reached user_id=%s cost=%.6f balance=%.6f limit=%.4f",
        user_id,
        usage_cost,
        balance,
        settings.free_usage_limit_usd,
    )
    await reply_text_retry(
        update.message,
        build_paywall_text(limit_usd=settings.free_usage_limit_usd),
        reply_markup=build_topup_keyboard(),
    )


async def on_topup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer("Оплата скоро подключим — пока это заглушка.")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    settings: Settings = context.application.bot_data["settings"]
    client = context.application.bot_data["llm_client"]
    mem: InMemoryHistory = context.application.bot_data["mem"]
    user = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else 0
    user_text = update.message.text.strip()

    try:
        user_id = _track_user(settings, user, increment_messages=0)

        if user_id is not None:
            usage_cost, balance = get_user_usage_usd(settings.stats_db_path, user_id)
            if is_usage_limit_reached(
                usage_cost_usd=usage_cost,
                balance_usd=balance,
                limit_usd=settings.free_usage_limit_usd,
            ):
                await _send_usage_limit_message(update, settings, user_id=user_id)
                return

        _track_user(settings, user, increment_messages=1)

        mem.append(chat_id, "user", user_text)

        history = mem.get(chat_id)
        system_content = f"{SYSTEM_PROMPT_RU}\n\n{USER_HINT}"
        msgs: list[ChatMsg] = [ChatMsg(role="system", content=system_content)]
        for h in history:
            msgs.append(ChatMsg(role=h.role, content=h.content))

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        try:
            result = chat_completion(client, settings=settings, messages=msgs)
        except Exception as e:
            log.exception("LLM call failed: %s", e)
            await reply_text_retry(
                update.message,
                "Ох, сосед, мозги мои сейчас как лампочка в подъезде — моргнули и потухли. "
                "Попробуй ещё раз через минутку.",
            )
            return

        answer = result.content or (
            "Сосед, я тут задумался… а конкретнее можно? Что именно надо сделать?"
        )

        if user_id is not None and result.total_tokens > 0:
            cost = calc_cost_usd(
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                input_price_per_1m=settings.cost_input_per_1m_usd,
                output_price_per_1m=settings.cost_output_per_1m_usd,
            )
            record_usage(
                settings.stats_db_path,
                telegram_user_id=user_id,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                cost_usd=cost,
            )

        mem.append(chat_id, "assistant", answer)

        for part in split_reply(answer, settings.max_message_chars):
            await reply_text_retry(update.message, _safe_markdown(part))
    except Exception:
        log.exception("on_text failed for chat_id=%s", chat_id)
        await reply_text_retry(
            update.message,
            "Сосед, что-то у меня внутри хрустнуло. Попробуй ещё раз или /reset.",
        )


async def _on_startup(app: Application) -> None:
    log.info("Post-init: ожидаем подключение к Telegram (медленная сеть — это нормально)")


async def _on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Unhandled bot error: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Сосед, сбой на линии. Попробуй /start или напиши ещё раз."
            )
        except Exception:
            pass


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    settings = load_settings()
    init_db(settings.stats_db_path)
    client = build_client(settings)
    log.info("LLM: base_url=%s model=%s", settings.openai_base_url, settings.openai_model)
    log.info("Stats DB: %s", settings.stats_db_path)
    log.info("Free usage limit: $%.4f per user", settings.free_usage_limit_usd)
    mem = InMemoryHistory(max_messages=settings.max_history_messages)

    # Таймауты только в HTTPXRequest — нельзя дублировать через .connect_timeout() и т.д.
    tg_request = build_telegram_request()
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .request(tg_request)
        .get_updates_request(build_telegram_request())
        .post_init(_on_startup)
        .build()
    )
    app.bot_data["settings"] = settings
    app.bot_data["llm_client"] = client
    app.bot_data["mem"] = mem

    app.add_error_handler(_on_error)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("share", cmd_share))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CallbackQueryHandler(on_topup_callback, pattern="^topup:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("Sosed bot starting polling (bootstrap_retries=-1 for slow network)")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        bootstrap_retries=-1,
    )


if __name__ == "__main__":
    main()
