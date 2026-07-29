---
name: detect_language
track: bonus
kind: local_analyzer
requires_env: []
inputs: [text]
outputs: [language, confidence]
side_effect: false
---
# detect_language

Provides a lightweight deterministic language hint for Vietnamese, English, or
unknown text. It is a routing aid, not a translation or a certified language detector.
