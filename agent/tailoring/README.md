# tailoring

Generates a per-job resume, cover letter, and free-text/behavioral screening-question answers from `source_of_truth/` facts. Reorders/rephrases/emphasizes only — never adds a fact that isn't in `source_of_truth/`.

**Pipeline role: Application Generator.** Second stage of `Data -> Hybrid Search -> Application Generator -> Application Controller -> Application API`. Runs on postings that cleared `matching/`'s `hybrid_search`, highest `matching_fact_count` first, until the run's submitted-application cap — it has no say in fit or order. Its output goes to `review_gate/` (honesty/relevance check) before anything reaches `form_automation/`.

**Generator input:** the top-N `(id, content)` `Document` pairs exactly as `hybrid_search` returns them — no separate resolve-by-id step, since each `Document`'s `content` is already the full serialized atomic fact (see `../matching/README.md`'s Types section). N isn't a parameter this module owns — it's whatever fact set cleared `matching/`'s threshold for that posting.

**Three separate LLM calls:** one Ollama call each for the resume, the cover letter, and free-text/screening-question answers — not one combined call. All three share a system prompt (honesty rules, prompt-injection framing for raw posting text) and differ only in the user-role content. Deterministic screening questions (visa, salary, EEO) skip the LLM entirely, answered directly from `source_of_truth/`.

**Language: Python**, internal module of the shared Python service (see `../README.md`). Local LLM via Ollama, CPU-only (current default: `qwen2.5:14b`, JSON-schema-constrained output, see `llm/README.md`).

Behavioral answers draw on `projects-detail.json` and `general-stories.json` for incident-level material. Known gaps (degree, experience, GPA, sponsorship) are **not** left to search ranking or to the LLM (option (b) and the "raise a gap only if the posting asks" rule, both decided 2026-09-30 — see `../CLAUDE.md`): `generate()` takes `known-gaps.json`'s full list as its own `known_gaps` argument, and `gaps/gaps.py`'s `decide_gaps()` decides in plain code, before any LLM call, which ones the posting asks about. Only those reach the cover-letter call; the decisions (with reasons) land in `GenerateResult.gap_decisions` for the review email. Search still decides fit and picks the top-N facts, but facts the gap rules govern — `known_gap:*`, `education` (holds the GPA), `professional_experience`, and the `job_preference:*` screening answers — are dropped from the resume and cover-letter prompts, so search can't put an unasked-for gap back in. The application call keeps every fact, since a free-text answer about experience or education still has to be honest. No caching — every answer regenerates fresh.

## Output

**Format: PDF**, via Playwright print-to-PDF. The LLM returns JSON (see `prompts/README.md`); `write_resume()`/`write_cover_letter()` in `write/write.py` take that JSON string directly, validate it against `pydantic` models, fill a Jinja2 HTML template (autoescape handles escaping), and render. The resume fills a fixed structure (one block per project plus summary/skills); the cover letter is freeform prose within a style shell (header, date, greeting, closing).

The application call's `{field_id: answer}` response is handled the same way minus rendering: `parse_application_answers()` (also in `write/write.py`) validates structurally via `pydantic.TypeAdapter(dict[str, str])`, checks the answers against the questions asked (exact `field_id`s, `"not provided"`, `max_length` — see `write/README.md`) and returns `ParseResult(answers, error)`. `form_automation/` (not built) is the intended consumer of `.answers`.

**One page is a hard constraint** on every generated document — content renders first, free to flow past one page, then the rendered PDF's page count is checked via `pypdf` (Playwright's `page.pdf()` doesn't report a count the way `pdflatex` did). Overflow doesn't get clipped with CSS — that would silently truncate content — it returns `WriteResult(path=..., error=WriteError.OVERFLOW, content=...)` instead, keeping both the file and the parsed text for review. Routing that overflow to the user (email + approve/reject, bypassing the Controller since it's not a content question) isn't built yet — see `../CLAUDE.md`.

## Orchestration

`generate.py`'s `generate(facts, job_posting, personal, questions, known_gaps, output_dir) -> GenerateResult` calls the LLM once per call (no retry on any failure), passes each raw response to `write_resume()`/`write_cover_letter()`/`parse_application_answers()`, and aborts the remaining steps as soon as one fails — an LLM failure, a failed render, or a broken response (`INVALID_JSON`/`VALIDATION_ERROR`) all stop the sequence rather than, say, spending the single Ollama slot on a cover letter for an application whose resume is already dead. `OVERFLOW` does *not* stop it: that content is real and goes to the user for approve/reject. Output files go to `output_dir/<stem>_resume.pdf` / `<stem>_cover_letter.pdf`, where `<stem>` is `filename_stem(job_posting["id"])` — the ID reduced to `[A-Za-z0-9_-]`, since it's outside data and must not be able to escape `output_dir` (`tracking/` should reuse the same function for its per-application files). `GenerateResult(resume, cover_letter, application, gap_decisions)` distinguishes "never reached" (`None`) from "reached and failed" (a result with `.error` set); `gap_decisions` is filled before any LLM call.

Failures are caught explicitly by type, not with a blanket `except Exception` or implicit `None` checks: `OllamaError` (from `llm_ollama()`, see `llm/README.md`) → `WriteError.LLM_FAILURE`; `playwright.async_api.Error`/`pypdf.errors.PyPdfError` during rendering → `WriteError.RENDER_FAILURE`. Anything else propagates as a real exception rather than being absorbed into a result that would look like a normal failure.

The `questions` list for the application call is supplied by the caller — `generate()` doesn't source it itself; that's `form_automation/`'s job (reading the actual application form), and it doesn't exist yet.

## Submodules

- `generate.py` — orchestrates `llm/`, `prompts/`, and `write/` for all three calls. See Orchestration above.
- `llm/` — Ollama client wrapper. See `llm/README.md`.
- `prompts/` — builds the four prompt strings (one system, three user), each instructing JSON output. See `prompts/README.md`.
- `write/` — parses each call's JSON output into its final artifact (rendered PDF, or form-field answers for `form_automation/`). See `write/README.md`.
- `gaps/` — decides in plain code which known gaps the posting asks about, before any LLM call. See `gaps/README.md`.
- `write/templates/` — Jinja2 HTML/CSS templates (`resume.html`, `cover_letter.html`, shared `_style.html`/`_macros.html` partials), visually mirroring the project's established design (`#2656A6` accent, same header/section layout).

Status: in progress — Ollama client (JSON-schema output, `qwen2.5:14b`), all three prompts, code-decided gaps, and Playwright rendering with one-page detection are built and exercised in live runs against local Ollama; no committed test suite; review-routing on overflow is not yet wired. Scratch/prototype code — module boundaries and prompt formats are still settling. See `../CLAUDE.md`.
