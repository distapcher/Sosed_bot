from __future__ import annotations

import logging

from dotenv import load_dotenv
from telegram import Update, User
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from .config import Settings, load_settings
from .llm import ChatMsg, build_client, chat_completion
from .memory import InMemoryHistory
from .prompts import SYSTEM_PROMPT_RU, USER_HINT
from .stats import calc_cost_usd, init_db, record_usage, touch_user
from .text_utils import split_reply

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
    assert update.message
    settings: Settings = context.application.bot_data["settings"]
    _track_user(settings, update.effective_user)
    await update.message.reply_text(
        "Здорово, сосед. Я тут по хозяйству подскажу — пиши, что стряслось.",
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message
    settings: Settings = context.application.bot_data["settings"]
    mem: InMemoryHistory = context.application.bot_data["mem"]
    chat_id = update.effective_chat.id if update.effective_chat else 0
    _track_user(settings, update.effective_user)
    mem.clear(chat_id)
    await update.message.reply_text("Ладно, сосед, начнём с чистого листа. Что делаем?")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    settings: Settings = context.application.bot_data["settings"]
    client = context.application.bot_data["llm_client"]
    mem: InMemoryHistory = context.application.bot_data["mem"]

    chat_id = update.effective_chat.id if update.effective_chat else 0
    user_id = _track_user(settings, update.effective_user, increment_messages=1)
    user_text = update.message.text.strip()

    mem.append(chat_id, "user", user_text)

    history = mem.get(chat_id)
    msgs: list[ChatMsg] = [ChatMsg(role="system", content=SYSTEM_PROMPT_RU)]
    msgs.append(ChatMsg(role="user", content=USER_HINT))
    for h in history:
        msgs.append(ChatMsg(role=h.role, content=h.content))

    try:
        result = chat_completion(client, settings=settings, messages=msgs)
    except Exception as e:
        log.exception("LLM call failed: %s", e)
        await update.message.reply_text(
            "Ох, сосед, мозги мои сейчас как лампочка в подъезде — моргнули и потухли. "
            "Попробуй ещё раз через минутку."
        )
        return

    answer = result.content or "Сосед, я тут задумался… а конкретнее можно? Что именно надо сделать?"

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
        await update.message.reply_text(_safe_markdown(part))


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    settings = load_settings()
    init_db(settings.stats_db_path)
    client = build_client(settings)
    log.info("LLM: base_url=%s model=%s", settings.openai_base_url, settings.openai_model)
    log.info("Stats DB: %s", settings.stats_db_path)
    mem = InMemoryHistory(max_messages=settings.max_history_messages)

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data["settings"] = settings
    app.bot_data["llm_client"] = client
    app.bot_data["mem"] = mem

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("Sosed bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
