from __future__ import annotations

import re
from typing import Any


def extract_quotes(text: str = "", keywords: list[str] | None = None, max_quotes: int = 5) -> dict[str, Any]:
    terms = [term.strip().lower() for term in (keywords or []) if term.strip()]
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text or "") if part.strip()]
    quotes = [sentence for sentence in sentences if any(term in sentence.lower() for term in terms)]
    quotes = quotes[:max(0, max_quotes)]
    return {"tool": "quote_extract", "quotes": quotes, "quote_count": len(quotes)}
