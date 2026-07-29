from __future__ import annotations

from typing import Any


VI_MARKERS = {" và ", " của ", " không ", " những ", " được ", " trong ", " là "}
EN_MARKERS = {" the ", " and ", " of ", " with ", " is ", " are ", " from "}


def detect_language(text: str = "") -> dict[str, Any]:
    value = f" {(text or '').lower()} "
    vi_score = sum(marker in value for marker in VI_MARKERS)
    en_score = sum(marker in value for marker in EN_MARKERS)
    if vi_score > en_score and vi_score > 0:
        language, confidence = "vi", min(0.99, 0.6 + vi_score * 0.08)
    elif en_score > vi_score and en_score > 0:
        language, confidence = "en", min(0.99, 0.6 + en_score * 0.08)
    else:
        language, confidence = "unknown", 0.2
    return {"tool": "detect_language", "language": language, "confidence": round(confidence, 2)}
