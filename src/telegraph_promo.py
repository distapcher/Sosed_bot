from __future__ import annotations

import json
import logging
from os import getenv

import httpx

from .promo import PROMO_DESCRIPTION, PROMO_TITLE, bot_telegram_url
from .stats import get_meta, set_meta

log = logging.getLogger("sosed.telegraph")

_API = "https://api.telegra.ph"
_META_TOKEN = "telegraph_access_token"
_META_URL = "telegraph_promo_url"


def _create_account() -> str:
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{_API}/createAccount",
            json={"short_name": "Sosed", "author_name": "Сосед"},
        )
        resp.raise_for_status()
        data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegraph createAccount failed: {data}")
    return str(data["result"]["access_token"])


def _build_page_nodes(bot_username: str) -> str:
    bot_url = bot_telegram_url(bot_username)
    nodes = [
        {"tag": "h3", "children": [PROMO_TITLE]},
        {"tag": "p", "children": [PROMO_DESCRIPTION]},
        {
            "tag": "p",
            "children": ["С чем помогаю:"],
        },
        {
            "tag": "ul",
            "children": [
                {"tag": "li", "children": ["Дом и квартира: сантехника, ремонт, уборка"]},
                {"tag": "li", "children": ["Авто: уход, расходники, мелкий ремонт"]},
                {"tag": "li", "children": ["Техника: стиралка, холодильник, инструмент"]},
            ],
        },
        {
            "tag": "p",
            "children": [
                {
                    "tag": "a",
                    "attrs": {"href": bot_url},
                    "children": ["🚀 Открыть бота в Telegram"],
                }
            ],
        },
    ]
    return json.dumps(nodes)


def _create_page(access_token: str, bot_username: str) -> str:
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{_API}/createPage",
            json={
                "access_token": access_token,
                "title": PROMO_TITLE,
                "author_name": "Сосед",
                "content": _build_page_nodes(bot_username),
                "return_content": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegraph createPage failed: {data}")
    return str(data["result"]["url"])


def get_channel_promo_url(db_path: str, bot_username: str) -> str:
    """
    HTTPS-страница на telegra.ph — в каналах Telegram даёт карточку превью.
  IP и http:// для превью в канале не работают.
    """
    env_url = getenv("TELEGRAPH_PROMO_URL", "").strip()
    if env_url:
        return env_url

    cached = get_meta(db_path, _META_URL)
    if cached:
        return cached

    token = get_meta(db_path, _META_TOKEN)
    if not token:
        token = _create_account()
        set_meta(db_path, _META_TOKEN, token)
        log.info("Telegraph account created")

    url = _create_page(token, bot_username)
    set_meta(db_path, _META_URL, url)
    log.info("Telegraph promo page: %s", url)
    return url
