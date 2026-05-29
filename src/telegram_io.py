from __future__ import annotations

import asyncio
import logging

from telegram import Bot, Message
from telegram.error import NetworkError, TimedOut
from telegram.request import HTTPXRequest

log = logging.getLogger("sosed.telegram")


def build_telegram_request() -> HTTPXRequest:
    """Longer timeouts for slow VPS / Docker networks."""
    return HTTPXRequest(
        connect_timeout=60.0,
        read_timeout=90.0,
        write_timeout=90.0,
        pool_timeout=60.0,
    )


async def _send_with_retry(
    send_coro_factory,
    *,
    attempts: int = 5,
) -> Message:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await send_coro_factory()
        except (TimedOut, NetworkError) as err:
            last_error = err
            log.warning("Telegram send attempt %s/%s failed: %s", attempt, attempts, err)
            if attempt < attempts:
                await asyncio.sleep(3 * attempt)
    assert last_error is not None
    raise last_error


async def reply_text_retry(
    message: Message,
    text: str,
    *,
    attempts: int = 5,
) -> Message:
    return await _send_with_retry(lambda: message.reply_text(text), attempts=attempts)


async def send_message_retry(
    bot: Bot,
    chat_id: int,
    text: str,
    *,
    attempts: int = 5,
) -> Message:
    return await _send_with_retry(
        lambda: bot.send_message(chat_id=chat_id, text=text),
        attempts=attempts,
    )
