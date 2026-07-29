---
name: text_stats
track: bonus
kind: local_analyzer
requires_env: []
inputs: [text]
outputs: [character_count, word_count, sentence_count, reading_minutes]
side_effect: false
---
# text_stats

Calculates transparent length statistics for supplied research text. Reading time
uses a fixed estimate of 200 words per minute.
