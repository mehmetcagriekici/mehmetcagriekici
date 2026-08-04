# tailoring

Generates a per-job resume variant and cover letter from profile-store facts, plus free-text/behavioral screening-question answers. Reorders/rephrases/emphasizes only — never adds a fact not present in `source_of_truth/`.

**Pipeline role: Application Generator (decided 2026-07-22).** Second stage of `Data -> Hybrid Search -> Application Generator -> Application Controller -> Application API`. Runs **unconditionally** on every posting that clears `matching/`'s single `hybrid_search` step — it has no say in fit, only in generation. Its output goes to `review_gate/` (the Application Controller) for a honesty/relevance check before anything reaches `form_automation/` (the Application API).

**Generator input (decided 2026-08-04, supersedes the id-resolution design in `matching/README.md`'s Types section):** the Generator consumes the top-N `(id, content)` `Document` pairs exactly as `hybrid_search` returns them — no separate resolve-by-id step back to a structured `source_of_truth` record. This holds cleanly because `document_builder` already builds one `Document` per *atomic* fact (`content` is `json.dumps` of that single fact, not a bundle of several), so the flattened form loses no structure worth resolving. N itself isn't a parameter this module owns — it's whatever fact set cleared `matching/`'s threshold for that posting (count varies per posting; see `../matching/README.md`).

**Three separate LLM calls, not one (decided 2026-08-04):** one Ollama call each for the resume, the cover letter, and free-text/screening-question form-field answers (the `application` prompt) — not a single combined call. All three share the same `system` prompt (general rules and safety, including the prompt-injection framing for raw job-posting text — see the Prompt injection defense section of `../CLAUDE.md`) and differ only in the `user`-role content prompt. Deterministic screening questions (visa, salary, EEO, etc.) skip the LLM entirely and are answered directly from structured fields in `source_of_truth/` — only the generative side (resume, cover letter, free-text/behavioral answers) goes through these calls.

**Language: Python** — internal module of the shared Python service (see tech stack in `../README.md`). Local LLM via Ollama, CPU-only, capping realistic model size to roughly 7-8B quantized (current scratch default: `gemma3`, see `llm/README.md`).

Behavioral answers draw on `projects-detail.json` and `general-stories.json` (see `../source_of_truth/README.md`) for real incident-level material rather than extrapolating from feature bullets. For known weak spots in the profile (in-progress degree, no professional experience, GPA, sponsorship need), generation draws on `known-gaps.json` — no special-casing needed, since gap facts are indexed into `source_of_truth` like everything else and naturally surface in `hybrid_search`'s top-N whenever a posting's own language actually touches that gap (e.g. an experience-years requirement pulls in the "no professional experience" fact on its own). No caching for now — every answer regenerates fresh each time.

**Output format: PDF** (decided 2026-07-26), via the same LaTeX->PDF workflow as the root cover-letter process. The LLM itself returns JSON (decided 2026-08-04 — see `prompts/README.md`'s Output format note, `write/README.md`), which `write/` escapes and maps into `resume_template.tex` / `cover_template.tex` before compiling — the resume fills a fixed macro structure (`\project{name}{tech}{dates}` plus a summary/skills section), the cover letter is genuinely freeform prose within a style shell (header, date, greeting, closing) since it doesn't reduce to a repeatable structural pattern. **One page is a hard constraint** on every generated document: compile once, check the page count, no auto-retry. On overflow, the user is emailed immediately (same approve/reject mechanism as a `review_gate/` routing, bypassing the Controller's honesty/relevance check since overflow isn't a content question) — see `../CLAUDE.md` for the full decision history.

## Submodules

- `llm/` — Ollama client wrapper. See `llm/README.md`.
- `prompts/` — builds the four prompt strings (one system, three user) fed into `llm/`, each instructing the model to return JSON. See `prompts/README.md`.
- `write/` — parses each call's JSON output and turns it into its final artifact (compiled PDF, or form-field answers handed to `form_automation/`). See `write/README.md`.
- `resume_template.tex` / `cover_template.tex` — the LaTeX style shells described above. Current content is a stale placeholder snapshot, not target output — see `../CLAUDE.md` for the full typography/spacing decisions.

Scratch/prototype code — module boundaries and prompt formats are still settling. See `../CLAUDE.md`.
