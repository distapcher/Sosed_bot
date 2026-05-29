from __future__ import annotations


def split_reply(text: str, max_chars: int) -> list[str]:
    """Split long plain-text reply into Telegram-sized chunks."""
    text = text.strip()
    if not text:
        return []
    if max_chars <= 0:
        return [text]
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        remaining = remaining.lstrip()
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        window = remaining[:max_chars]
        split_at = -1
        for sep in ("\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "):
            idx = window.rfind(sep)
            if idx >= int(max_chars * 0.4):
                split_at = idx + len(sep)
                break

        if split_at <= 0:
            split_at = max_chars

        part = remaining[:split_at].rstrip()
        if not part:
            part = remaining[:max_chars]
            split_at = max_chars

        chunks.append(part)
        remaining = remaining[split_at:]

    return chunks
