from __future__ import annotations

import logging

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, User
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from .config import Settings, load_settings
from .llm import ChatMsg, build_client, chat_completion
from .memory import InMemoryHistory
from .payments import configure_yookassa, create_subscription_payment
from .prompts import SYSTEM_PROMPT_RU, USER_HINT
from .stats import (
    calc_cost_usd,
    get_paid_until,
    init_db,
    record_usage,
    save_pending_payment,
    touch_user,
    user_has_access,
)
from .text_utils import split_reply
from .welcome import build_welcome_keyboard, build_welcome_text

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


def _format_paid_until(paid_until: str | None) -> str:
    if not paid_until:
        return "нет активной подписки"
    return paid_until.replace("T", " ").replace("+00:00", " UTC")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message
    settings: Settings = context.application.bot_data["settings"]
    user = update.effective_user
    _track_user(settings, user)

    has_access = False
    paid_until = None
    if user is not None:
        has_access = user_has_access(
            settings.stats_db_path,
            telegram_user_id=user.id,
            free_user_ids=settings.free_telegram_user_ids,
        )
        paid_until = get_paid_until(settings.stats_db_path, user.id)

    text = build_welcome_text(
        settings,
        has_access=has_access,
        paid_until=paid_until,
    )
    keyboard = build_welcome_keyboard()

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


async def handle_pay_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    settings: Settings = context.application.bot_data["settings"]
    _track_user(settings, user)

    if not settings.payment_enabled:
        await message.reply_text(
            "Подписка скоро будет доступна. А пока пиши — Сосед на связи."
        )
        return

    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        await message.reply_text(
            "Оплата пока не настроена на сервере. Напиши владельцу бота."
        )
        return

    if user_has_access(
        settings.stats_db_path,
        telegram_user_id=user.id,
        free_user_ids=settings.free_telegram_user_ids,
    ):
        paid_until = get_paid_until(settings.stats_db_path, user.id)
        await message.reply_text(
            f"У тебя уже есть доступ до {_format_paid_until(paid_until)}. "
            "Если продлить — оплати ещё раз, дни добавятся."
        )

    try:
        created = create_subscription_payment(settings, telegram_user_id=user.id)
        save_pending_payment(
            settings.stats_db_path,
            payment_id=created.payment_id,
            telegram_user_id=user.id,
            amount_rub=created.amount_rub,
            access_days=settings.payment_access_days,
        )
    except Exception:
        log.exception("Failed to create YooKassa payment")
        await message.reply_text(
            "Не вышло выставить счёт. Попробуй через минутку или напиши владельцу бота."
        )
        return

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="💳 Оплатить подписку", url=created.confirmation_url)]]
    )
    await message.reply_text(
        f"Сумма: {created.amount_rub:.0f} ₽ · срок: {settings.payment_access_days} дн.\n\n"
        "Жми кнопку ниже — после оплаты доступ включится автоматически.",
        reply_markup=keyboard,
    )


async def on_pay_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    await handle_pay_request(update, context)


async def cmd_pay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_pay_request(update, context)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message
    settings: Settings = context.application.bot_data["settings"]
    user = update.effective_user
    if user is None:
        return

    _track_user(settings, user)

    if not settings.payment_enabled:
        await update.message.reply_text("Оплата выключена — пользуйся на здоровье, сосед.")
        return

    if user.id in settings.free_telegram_user_ids:
        await update.message.reply_text("Тебе всё открыто — ты в списке своих.")
        return

    paid_until = get_paid_until(settings.stats_db_path, user.id)
    if user_has_access(
        settings.stats_db_path,
        telegram_user_id=user.id,
        free_user_ids=settings.free_telegram_user_ids,
    ):
        await update.message.reply_text(
            f"Доступ есть, сосед. Действует до: {_format_paid_until(paid_until)}."
        )
        return

    await update.message.reply_text(
        f"Доступа пока нет. Оформи через /pay — {settings.payment_amount_rub:.0f} ₽ "
        f"на {settings.payment_access_days} дн."
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
    user = update.effective_user

    chat_id = update.effective_chat.id if update.effective_chat else 0
    user_id = _track_user(settings, user, increment_messages=1)
    user_text = update.message.text.strip()

    if (
        settings.payment_enabled
        and user_id is not None
        and not user_has_access(
            settings.stats_db_path,
            telegram_user_id=user_id,
            free_user_ids=settings.free_telegram_user_ids,
        )
    ):
        await update.message.reply_text(
            f"Сосед, без подписки в советы не лезу — хозяйство тоже не бесплатное.\n\n"
            f"/start — кнопка «Оплатить подписку» ({settings.payment_amount_rub:.0f} ₽, "
            f"{settings.payment_access_days} дн.)\n"
            "/status — проверить срок"
        )
        return

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

    if settings.payment_enabled:
        if settings.yookassa_shop_id and settings.yookassa_secret_key:
            configure_yookassa(settings)
            log.info("YooKassa payments enabled")
        else:
            log.warning("PAYMENT_ENABLED=true but YooKassa credentials are missing")

    client = build_client(settings)
    log.info("LLM: base_url=%s model=%s", settings.openai_base_url, settings.openai_model)
    log.info("Stats DB: %s", settings.stats_db_path)
    mem = InMemoryHistory(max_messages=settings.max_history_messages)

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data["settings"] = settings
    app.bot_data["llm_client"] = client
    app.bot_data["mem"] = mem

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_pay_button, pattern="^pay_subscription$"))
    app.add_handler(CommandHandler("pay", cmd_pay))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("Sosed bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
