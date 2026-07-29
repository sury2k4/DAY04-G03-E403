---
name: wiki
track: core
kind: live_api
provider: Wikipedia REST API
requires_env: []
inputs: [topic, lang]
outputs: [items]
side_effect: false
---
# wiki

Looks up a topic on Wikipedia and returns the lead summary (title, URL,
extract). No API key needed. Tries the requested language first (default
`vi`) and falls back to English when the page does not exist.

Use when the user asks for a definition, background, or "X là gì/là ai"
style questions about a concept, person, or organization. Do NOT use for
breaking news (use `lookup` with `topic=news`) or social media posts.

Smoke test:

```bash
python -c "from pathlib import Path; from env_loader import load_lab_env; load_lab_env(Path.cwd()); from tools import TOOL_FUNCTIONS as T; r=T['wiki']('OpenAI'); items=r.get('items') or []; print({'error':r.get('error'), 'item_count':len(items), 'first_title':items[0].get('title') if items else None})"
```
