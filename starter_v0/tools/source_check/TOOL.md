---
name: source_check
track: team
kind: local_analyzer
requires_env: []
inputs: [url, title, published_date]
outputs: [score, rating, signals, domain]
side_effect: false
---
# source_check

Performs a transparent, deterministic first-pass quality check for a supplied
web source. It scores URL-level signals such as HTTPS, recognizable publication
type, suspicious host patterns, title availability, and publication-date
availability.

This tool does not prove that a claim is true. Its result must be presented as a
screening aid, and important claims should still be corroborated with primary
sources.
