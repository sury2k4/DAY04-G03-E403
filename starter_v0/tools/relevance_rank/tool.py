from __future__ import annotations

import re
from typing import Any


def _terms(value: str) -> set[str]:
    return {term.lower() for term in re.findall(r"[\wÀ-ỹ]+", value or "") if len(term) > 1}


def rank_relevance(items: list[dict[str, Any]] | None = None, query: str = "", top_k: int = 5) -> dict[str, Any]:
    query_terms = _terms(query)
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, item in enumerate(items or []):
        haystack = _terms(f"{item.get('title', '')} {item.get('summary', '')}")
        score = len(query_terms & haystack)
        enriched = dict(item)
        enriched["relevance_score"] = score
        scored.append((score, index, enriched))
    scored.sort(key=lambda value: (-value[0], value[1]))
    limit = max(0, top_k)
    ranked = [item for _, _, item in scored[:limit]]
    return {"tool": "relevance_rank", "query": query, "items": ranked, "item_count": len(ranked)}
