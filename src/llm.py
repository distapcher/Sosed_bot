from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from .config import Settings


@dataclass(frozen=True)
class ChatMsg:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True)
class ChatResult:
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


def build_client(settings: Settings) -> OpenAI:
    return OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=60.0,
    )


def chat_completion(
    client: OpenAI,
    *,
    settings: Settings,
    messages: list[ChatMsg],
    max_output_tokens: int | None = None,
) -> ChatResult:
    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": m.role, "content": m.content} for m in messages],
        max_tokens=max_output_tokens or settings.max_output_tokens,
        temperature=0.8,
    )
    content = (resp.choices[0].message.content or "").strip()
    usage = resp.usage
    prompt_tokens = int(usage.prompt_tokens or 0) if usage else 0
    completion_tokens = int(usage.completion_tokens or 0) if usage else 0
    total_tokens = int(usage.total_tokens or prompt_tokens + completion_tokens) if usage else 0

    return ChatResult(
        content=content,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
