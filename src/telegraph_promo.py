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
_META_PATH = "telegraph_promo_path"


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


def _link_button_node(bot_url: str, label: str) -> dict:
    return {
        "tag": "p",
        "children": [
            {
                "tag": "strong",
                "children": [
                    {
                        "tag": "a",
                        "attrs": {"href": bot_url},
                        "children": [label],
                    }
                ],
            }
        ],
    }


def _build_page_nodes(bot_username: str) -> str:
    bot_url = bot_telegram_url(bot_username)
    nodes = [
        _link_button_node(bot_url, "▶️ ЗАПУСТИТЬ БОТА В TELEGRAM"),
        {"tag": "hr"},
        {"tag": "h3", "children": [PROMO_TITLE]},
        {"tag": "p", "children": [PROMO_DESCRIPTION]},
        {"tag": "p", "children": ["С чем помогаю:"]},
        {
            "tag": "ul",
            "children": [
                {"tag": "li", "children": ["Дом и квартира: сантехника, ремонт, уборка"]},
                {"tag": "li", "children": ["Авто: уход, расходники, мелкий ремонт"]},
                {"tag": "li", "children": ["Техника: стиралка, холодильник, инструмент"]},
            ],
        },
        {"tag": "hr"},
        _link_button_node(bot_url, f"🚀 Открыть @{bot_username}"),
    ]
    return json.dumps(nodes)


def _page_payload(bot_username: str) -> dict:
    bot_url = bot_telegram_url(bot_username)
    return {
        "title": PROMO_TITLE,
        "author_name": "Сосед",
        "author_url": bot_url,
        "content": _build_page_nodes(bot_username),
        "return_content": False,
    }


def _create_page(access_token: str, bot_username: str) -> tuple[str, str]:
    payload = {"access_token": access_token, **_page_payload(bot_username)}
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(f"{_API}/createPage", json=payload)
        resp.raise_for_status()
        data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegraph createPage failed: {data}")
    result = data["result"]
    return str(result["url"]), str(result["path"])


def _edit_page(access_token: str, path: str, bot_username: str) -> None:
    payload = {"access_token": access_token, "path": path, **_page_payload(bot_username)}
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(f"{_API}/editPage", json=payload)
        resp.raise_for_status()
        data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegraph editPage failed: {data}")


def _get_token(db_path: str) -> str:
    token = get_meta(db_path, _META_TOKEN)
    if not token:
        token = _create_account()
        set_meta(db_path, _META_TOKEN, token)
        log.info("Telegraph account created")
    return token


def sync_channel_promo_page(db_path: str, bot_username: str) -> str:
    """Создать или обновить статью Telegraph (кнопка-ссылка на бота в тексте)."""
    env_url = getenv("TELEGRAPH_PROMO_URL", "").strip()
    if env_url:
        return env_url

    token = _get_token(db_path)
    url = get_meta(db_path, _META_URL)
    path = get_meta(db_path, _META_PATH)

    if url and path:
        try:
            _edit_page(token, path, bot_username)
            log.info("Telegraph promo page updated: %s", url)
        except Exception:
            log.exception("Telegraph editPage failed")
        return url

    url, path = _create_page(token, bot_username)
    set_meta(db_path, _META_URL, url)
    set_meta(db_path, _META_PATH, path)
    log.info("Telegraph promo page created: %s", url)
    return url


def get_channel_promo_url(db_path: str, bot_username: str) -> str:
    return sync_channel_promo_page(db_path, bot_username)
