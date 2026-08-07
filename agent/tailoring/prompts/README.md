# prompts

Builds the four prompt strings fed into `llm/client.py`'s `llm_ollama` — one shared system prompt, three call-specific user prompts.

**Output format: JSON for all three calls.** Each user prompt instructs the model to return a JSON object of fields, not raw markup or freeform text — `write/` parses that JSON and maps fields into a Jinja2 HTML template (or, for `application.py`, hands the JSON straight to `form_automation/`). Escaping is Jinja2's job at render time, not a manual per-field step or the model's concern.

## Files

- `system_prompt.py` — rules shared identically across all three calls: the honesty constraint (organize/format/select from `source_of_truth` content only, never invent), the prompt-injection framing that wraps raw job-posting text as labeled untrusted data, and the JSON-output instruction.
- `resume.py` — user prompt for the resume call, built from the top-N `(id, content)` Documents `hybrid_search` returns plus the one-page and template-structure constraints for `write/templates/resume.html`. `RESUME_SCHEMA`:
  - `summary` — matches `profile.json`'s `summary` string.
  - `skills` — an object keyed by category (not a flat array), matching how each skill fact is actually indexed, so the template's grouped Skills section can be reconstructed from what the model is given.
  - `projects[]` — `name`/`dates`/`tech`/`description`/`bullets`, plus `status` and `repo` (real project facts carry both).
  - `certifications[]` — each cert is its own fact; the resume's Training & Certificates section is LLM-filled from these rather than hardcoded.
  - **Deliberately excluded:** education and professional-experience facts. Both can legitimately surface in a posting's top-N matches, but the resume template has no section for them — this candidate's gaps there (GPA, in-progress degree, no professional experience) belong in the cover letter's mandatory `gaps` field instead. The prompt explicitly tells the model not to place such facts in the resume, since they can appear in its input.
- `cover_letter.py` — user prompt for the cover letter call. Same top-N input, plus hard rules (mandatory gaps paragraph, one page) and soft style rules (3-4 short paragraphs, no generic-enthusiasm filler, match the posting's tone where direct — see `../../CLAUDE.md`). `COVER_LETTER_SCHEMA`: `opening`/`experience`/`gaps` (omitted when no mismatch applies)/`closing`.
- `application.py` — user prompt for free-text/behavioral screening-question answers. Deterministic questions (visa, salary, EEO) never reach this — answered directly from `source_of_truth/`. Returns JSON keyed by field id: `{field_id: answer}`; each question may carry an optional `max_length`.

Status: all four written, still scratch/prototype wording — not yet exercised against a real model. See `../README.md`.
