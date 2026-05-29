#!/usr/bin/env python3
"""Проверка отправки сообщения в Telegram с сервера.

Usage (на VPS в папке проекта):
  export $(grep -v '^#' .env | xargs)
  python scripts/telegram_ping.py YOUR_TELEGRAM_USER_ID
"""

from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv
from telegram import Bot

from src.config import load_settings
from src.telegram_io import build_telegram_request, send_message_retry


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/telegram_ping.py CHAT_ID")
        sys.exit(1)

    chat_id = int(sys.argv[1])
    load_dotenv()
    settings = load_settings()
    bot = Bot(settings.telegram_bot_token, request=build_telegram_request())

    me = await bot.get_me()
    print(f"Bot: @{me.username}")

    msg = await send_message_retry(bot, chat_id, "Тест от Соседа: связь с Telegram работает.")
    print(f"Sent message_id={msg.message_id}")


if __name__ == "__main__":
    asyncio.run(main())
