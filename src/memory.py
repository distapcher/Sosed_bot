from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class HistoryItem:
    role: str
    content: str


class InMemoryHistory:
    """
    Simple per-chat memory. For production, replace with Redis/DB.
    """

    def __init__(self, *, max_messages: int) -> None:
        self._max_messages = max_messages
        self._by_chat: dict[int, deque[HistoryItem]] = defaultdict(deque)

    def append(self, chat_id: int, role: str, content: str) -> None:
        q = self._by_chat[chat_id]
        q.append(HistoryItem(role=role, content=content))
        while len(q) > self._max_messages:
            q.popleft()

    def get(self, chat_id: int) -> list[HistoryItem]:
        return list(self._by_chat.get(chat_id, deque()))

    def clear(self, chat_id: int) -> None:
        self._by_chat.pop(chat_id, None)

