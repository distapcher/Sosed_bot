from __future__ import annotations

import logging

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from .config import load_settings
from .llm import ChatMsg, build_client, chat_completion
from .memory import InMemoryHistory
from .prompts import SYSTEM_PROMPT_RU, USER_HINT
from .text_utils import split_reply

log = logging.getLogger("sosed")


def _safe_markdown(text: str) -> str:
    # We keep it simple: no formatting to avoid Telegram markdown pitfalls.
    return text


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message
    await update.message.reply_text(
        "Здорово, сосед. Я тут по хозяйству подскажу — пиши, что стряслось.",
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message
    mem: InMemoryHistory = context.application.bot_data["mem"]
    chat_id = update.effective_chat.id if update.effective_chat else 0
    mem.clear(chat_id)
    await update.message.reply_text("Ладно, сосед, начнём с чистого листа. Что делаем?")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    settings = context.application.bot_data["settings"]
    client = context.application.bot_data["llm_client"]
    mem: InMemoryHistory = context.application.bot_data["mem"]

    chat_id = update.effective_chat.id if update.effective_chat else 0
    user_text = update.message.text.strip()

    # Save user message
    mem.append(chat_id, "user", user_text)

    history = mem.get(chat_id)
    msgs: list[ChatMsg] = [ChatMsg(role="system", content=SYSTEM_PROMPT_RU)]
    msgs.append(ChatMsg(role="user", content=USER_HINT))
    for h in history:
        msgs.append(ChatMsg(role=h.role, content=h.content))

    try:
        answer = chat_completion(client, settings=settings, messages=msgs)
    except Exception as e:
        log.exception("LLM call failed: %s", e)
        await update.message.reply_text(
            "Ох, сосед, мозги мои сейчас как лампочка в подъезде — моргнули и потухли. "
            "Попробуй ещё раз через минутку."
        )
        return

    if not answer:
        answer = "Сосед, я тут задумался… а конкретнее можно? Что именно надо сделать?"

    mem.append(chat_id, "assistant", answer)

    for part in split_reply(answer, settings.max_message_chars):
        await update.message.reply_text(_safe_markdown(part))


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    settings = load_settings()
    client = build_client(settings)
    log.info("LLM: base_url=%s model=%s", settings.openai_base_url, settings.openai_model)
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

