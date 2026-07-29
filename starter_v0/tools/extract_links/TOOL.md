---
name: extract_links
track: bonus
kind: local_analyzer
requires_env: []
inputs: [text]
outputs: [links, link_count]
side_effect: false
---
# extract_links

Extracts unique HTTP/HTTPS links from text while preserving their first-seen order.
Useful after fetching or receiving a long research note.
