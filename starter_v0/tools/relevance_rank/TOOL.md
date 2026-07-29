---
name: relevance_rank
track: bonus
kind: local_analyzer
requires_env: []
inputs: [items, query, top_k]
outputs: [items, item_count]
side_effect: false
---
# relevance_rank

Ranks already-collected items by the number of query terms appearing in their
title and summary. It does not fetch new data; ties preserve original order.
