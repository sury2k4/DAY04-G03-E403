from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


HIGH_TRUST_SUFFIXES = (".gov", ".gov.vn", ".edu", ".edu.vn")
SUSPICIOUS_HOST_MARKERS = ("blogspot.", "wordpress.com", "medium.com")


def check_source_quality(
    url: str,
    title: str = "",
    published_date: str = "",
) -> dict[str, Any]:
    """Return explainable URL-level source-quality signals without fetching."""
    parsed = urlparse((url or "").strip())
    host = (parsed.hostname or "").lower()
    signals: list[dict[str, Any]] = []
    score = 50

    def add(signal: str, points: int, detail: str) -> None:
        nonlocal score
        score += points
        signals.append({"signal": signal, "points": points, "detail": detail})

    if parsed.scheme not in {"http", "https"} or not host:
        return {
            "error": "invalid_url",
            "message": "Provide an absolute http(s) URL.",
            "url": url,
        }

    add("https", 10 if parsed.scheme == "https" else -15, parsed.scheme.upper())
    if host.endswith(HIGH_TRUST_SUFFIXES):
        add("institutional_domain", 20, host)
    elif any(marker in host for marker in SUSPICIOUS_HOST_MARKERS):
        add("user_publishing_platform", -10, host)
    else:
        add("domain_present", 5, host)

    add("title_available", 8 if title.strip() else -5, "provided" if title.strip() else "missing")
    add(
        "publication_date_available",
        7 if published_date.strip() else -5,
        published_date.strip() or "missing",
    )

    score = max(0, min(100, score))
    rating = "strong" if score >= 80 else "moderate" if score >= 60 else "weak"
    return {
        "tool": "source_check",
        "url": url,
        "domain": host,
        "score": score,
        "rating": rating,
        "signals": signals,
        "caveat": "URL-level screening only; corroborate important claims with primary sources.",
    }
