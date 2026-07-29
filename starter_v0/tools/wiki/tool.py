from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

from tools._shared import TIMEOUT, err


HEADERS = {"User-Agent": "AI20k-Day04-Research-Agent/1.0 (educational lab)"}


def wiki_summary(topic: str = "", lang: str = "vi") -> dict[str, Any]:
    """Look up a topic on Wikipedia and return the lead summary.

    Uses the public Wikipedia REST API (no API key). Falls back to English
    if the page does not exist in the requested language.
    """
    try:
        if not topic.strip():
            raise ValueError("topic must not be empty")
        languages = [lang] + (["en"] if lang != "en" else [])
        last_status = None
        for language in languages:
            url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{quote(topic.strip())}"
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            last_status = response.status_code
            if response.status_code == 404:
                continue
            response.raise_for_status()
            data = response.json()
            page_url = (data.get("content_urls") or {}).get("desktop", {}).get("page")
            items = [{
                "title": data.get("title"),
                "url": page_url,
                "source": f"{language}.wikipedia.org",
                "summary": data.get("extract"),
                "description": data.get("description"),
            }]
            return {"tool": "wiki_summary", "topic": topic, "lang": language, "items": items}
        return {
            "tool": "wiki_summary",
            "topic": topic,
            "lang": lang,
            "items": [],
            "message": f"No Wikipedia page found for {topic!r} (last status {last_status})",
        }
    except Exception as exc:
        return err("wiki_summary", exc)
