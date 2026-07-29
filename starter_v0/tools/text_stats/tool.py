from __future__ import annotations

import re
from typing import Any


def text_stats(text: str = "") -> dict[str, Any]:
    value = text or ""
    words = re.findall(r"\b[\wÀ-ỹ]+\b", value, flags=re.UNICODE)
    sentences = [part for part in re.split(r"[.!?]+", value) if part.strip()]
    word_count = len(words)
    return {
        "tool": "text_stats",
        "character_count": len(value),
        "word_count": word_count,
        "sentence_count": len(sentences),
        "reading_minutes": max(1, (word_count + 199) // 200) if word_count else 0,
    }
