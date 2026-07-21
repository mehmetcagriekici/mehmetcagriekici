# matching

Fit-scoring: job description + profile store → a match-strength score (requirements diffed against structured profile-store fields, not LLM self-reported confidence) + reasoning.

**Language: Python** — an internal module of the shared Python service (see tech stack in `../README.md`). Hybrid approach: structured field-diff plus embedding/keyword search runs against every sourced listing cheaply and deterministically, no LLM call. The LLM (local, CPU-only via Ollama) is reserved as a tiebreaker only for listings landing close to the auto-submit/review threshold — specifically for soft/inferred requirements (e.g. "strong communication skills") that don't reduce to a checkable profile-store field.

Planning stage — no code yet. See `../CLAUDE.md`.
