# tailoring

Generates a per-job resume variant and cover letter from profile-store facts. Reorders/rephrases/emphasizes only — never adds a fact not present in the profile store.

**Language: Python** — an internal module of the shared Python service (see tech stack in `../README.md`). Uses a local LLM via Ollama, CPU-only (no GPU), which caps realistic model size to roughly 7-8B quantized. The LLM's job is explicitly constrained to organizing/formatting content from `source_of_truth/` without hallucinating — same principle as the honesty rules in the root `CLAUDE.md`.

Also generates free-text/behavioral screening-question answers (e.g. "tell me about a time you solved a bug") — deterministic screening questions (visa, salary, EEO, etc.) skip the LLM entirely and are answered directly from structured fields in `source_of_truth/`. Behavioral answers draw on the planned projects-detail and general-stories files (see `../source_of_truth/README.md`) for real incident-level material rather than extrapolating from feature bullets. For known weak spots in the profile (in-progress degree, no professional experience, GPA, sponsorship need), generation draws on the hand-maintained known-gaps file to stay in line with the manual workflow's honesty stance — name the gap directly, never gloss over it. No caching for now — every answer regenerates fresh from `source_of_truth/` each time.

Planning stage — no code yet. See `../CLAUDE.md`.
