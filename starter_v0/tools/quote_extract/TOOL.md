---
name: quote_extract
track: bonus
kind: local_analyzer
requires_env: []
inputs: [text, keywords, max_quotes]
outputs: [quotes, quote_count]
side_effect: false
---
# quote_extract

Returns sentences from supplied text that contain at least one requested keyword.
This helps surface evidence without inventing or rewriting source content.
