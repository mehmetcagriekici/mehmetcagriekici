# prompts

Builds the four prompt strings fed into `llm/ollama.py`'s `llm_ollama(user_prompt, system_prompt, model)` — one shared system prompt, three call-specific user prompts (decided 2026-08-04 — see `../README.md`).

- `system_prompt.py` — general rules and safety, shared identically across all three calls: the honesty constraint (organize/format/select from `source_of_truth` content only, never invent a fact — same principle as the root repo's `CLAUDE.md` honesty rules), and the prompt-injection framing that wraps raw job-posting text as labeled untrusted data rather than instructions (see the Prompt injection defense section of `../../CLAUDE.md`).
- `resume.py` — user prompt for the resume call. Built from the top-N `(id, content)` Documents `hybrid_search` returns for the posting (see `../README.md`'s Generator input note) plus the one-page and template-structure constraints for `../resume_template.tex`.
- `cover_letter.py` — user prompt for the cover letter call. Same top-N input, plus the cover letter's hard rules (mandatory gaps paragraph, one page) and soft style rules (3-4 short paragraphs, no generic-enthusiasm filler, match the posting's tone where direct) — see the Cover letter section of `../../CLAUDE.md`.
- `application.py` — user prompt for free-text/behavioral screening-question answers (e.g. "tell me about a time you solved a bug"). Deterministic screening questions (visa, salary, EEO, etc.) never reach this — they're answered directly from structured `source_of_truth/` fields, no LLM involved.

All four are currently empty stubs — content not yet written. See `../README.md`.
