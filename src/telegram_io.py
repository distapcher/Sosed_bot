from __future__ import annotations

import asyncio
import logging

from telegram import Message
from telegram.error import NetworkError, TimedOut
from telegram.request import HTTPXRequest

log = logging.getLogger("sosed.telegram")


def build_telegram_request() -> HTTPXRequest:
    """Longer timeouts for slow VPS networks."""
    return HTTPXRequest(
        connect_timeout=60.0,
        read_timeout=90.0,
        write_timeout=90.0,
        pool_timeout=60.0,
    )


async def reply_text_retry(
    message: Message,
    text: str,
    *,
    attempts: int = 3,
) -> Message:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await message.reply_text(text)
        except (TimedOut, NetworkError) as err:
            last_error = err
            log.warning("Telegram send attempt %s/%s failed: %s", attempt, attempts, err)
            if attempt < attempts:
                await asyncio.sleep(2 * attempt)
    assert last_error is not None
    raise last_error
