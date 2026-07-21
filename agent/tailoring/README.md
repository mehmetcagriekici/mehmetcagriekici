# tailoring

Generates a per-job resume variant and cover letter from profile-store facts. Reorders/rephrases/emphasizes only — never adds a fact not present in the profile store.

**Language: Python** — an internal module of the shared Python service (see tech stack in `../README.md`). Uses a local LLM via Ollama, CPU-only (no GPU), which caps realistic model size to roughly 7-8B quantized. The LLM's job is explicitly constrained to organizing/formatting content from `source_of_truth/profile.json` without hallucinating — same principle as the honesty rules in the root `CLAUDE.md`.

Planning stage — no code yet. See `../CLAUDE.md`.
