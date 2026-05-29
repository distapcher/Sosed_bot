from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class UserStats:
    telegram_user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    first_seen_at: str
    last_seen_at: str
    message_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


@dataclass(frozen=True)
class SummaryStats:
    user_count: int
    message_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def init_db(db_path: str) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with _connect(db_path) as conn:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS users (
                telegram_user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_usage_events_user_id
                ON usage_events(telegram_user_id);
            CREATE INDEX IF NOT EXISTS idx_usage_events_created_at
                ON usage_events(created_at);
            """
        )


@contextmanager
def _connect(db_path: str):
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def touch_user(
    db_path: str,
    *,
    telegram_user_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    increment_messages: int = 0,
) -> None:
    now = _now_iso()
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO users (
                telegram_user_id, username, first_name, last_name,
                first_seen_at, last_seen_at, message_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                last_seen_at = excluded.last_seen_at,
                message_count = users.message_count + excluded.message_count
            """,
            (
                telegram_user_id,
                username,
                first_name,
                last_name,
                now,
                now,
                increment_messages,
            ),
        )


def record_usage(
    db_path: str,
    *,
    telegram_user_id: int,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
) -> None:
    total_tokens = prompt_tokens + completion_tokens
    now = _now_iso()

    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO usage_events (
                telegram_user_id, created_at,
                prompt_tokens, completion_tokens, total_tokens, cost_usd
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (telegram_user_id, now, prompt_tokens, completion_tokens, total_tokens, cost_usd),
        )
        conn.execute(
            """
            UPDATE users SET
                prompt_tokens = prompt_tokens + ?,
                completion_tokens = completion_tokens + ?,
                total_tokens = total_tokens + ?,
                cost_usd = cost_usd + ?,
                last_seen_at = ?
            WHERE telegram_user_id = ?
            """,
            (
                prompt_tokens,
                completion_tokens,
                total_tokens,
                cost_usd,
                now,
                telegram_user_id,
            ),
        )


def get_summary(db_path: str) -> SummaryStats:
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS user_count,
                COALESCE(SUM(message_count), 0) AS message_count,
                COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                COALESCE(SUM(total_tokens), 0) AS total_tokens,
                COALESCE(SUM(cost_usd), 0) AS cost_usd
            FROM users
            """
        ).fetchone()

    return SummaryStats(
        user_count=int(row["user_count"]),
        message_count=int(row["message_count"]),
        prompt_tokens=int(row["prompt_tokens"]),
        completion_tokens=int(row["completion_tokens"]),
        total_tokens=int(row["total_tokens"]),
        cost_usd=float(row["cost_usd"]),
    )


def get_users(db_path: str) -> list[UserStats]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                telegram_user_id, username, first_name, last_name,
                first_seen_at, last_seen_at, message_count,
                prompt_tokens, completion_tokens, total_tokens, cost_usd
            FROM users
            ORDER BY last_seen_at DESC
            """
        ).fetchall()

    return [
        UserStats(
            telegram_user_id=int(row["telegram_user_id"]),
            username=row["username"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            first_seen_at=str(row["first_seen_at"]),
            last_seen_at=str(row["last_seen_at"]),
            message_count=int(row["message_count"]),
            prompt_tokens=int(row["prompt_tokens"]),
            completion_tokens=int(row["completion_tokens"]),
            total_tokens=int(row["total_tokens"]),
            cost_usd=float(row["cost_usd"]),
        )
        for row in rows
    ]


def calc_cost_usd(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    input_price_per_1m: float,
    output_price_per_1m: float,
) -> float:
    return (prompt_tokens / 1_000_000 * input_price_per_1m) + (
        completion_tokens / 1_000_000 * output_price_per_1m
    )
