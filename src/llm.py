from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from .config import Settings


@dataclass(frozen=True)
class ChatMsg:
    role: str  # "system" | "user" | "assistant"
    content: str


def build_client(settings: Settings) -> OpenAI:
    return OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


def chat_completion(
    client: OpenAI,
    *,
    settings: Settings,
    messages: list[ChatMsg],
    max_output_tokens: int | None = None,
) -> str:
    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": m.role, "content": m.content} for m in messages],
        max_tokens=max_output_tokens or settings.max_output_tokens,
        temperature=0.8,
    )
    content = resp.choices[0].message.content
    return (content or "").strip()

