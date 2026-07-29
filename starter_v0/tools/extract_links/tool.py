from __future__ import annotations

import re
from typing import Any


URL_RE = re.compile(r"https?://[^\s<>\"']+")


def extract_links(text: str = "") -> dict[str, Any]:
    links: list[str] = []
    seen: set[str] = set()
    for match in URL_RE.findall(text or ""):
        link = match.rstrip(".,;:!?)]}")
        if link not in seen:
            seen.add(link)
            links.append(link)
    return {"tool": "extract_links", "links": links, "link_count": len(links)}
