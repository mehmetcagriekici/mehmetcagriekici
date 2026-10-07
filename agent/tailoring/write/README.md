# write

Takes each LLM call's JSON output and turns it into that call's final artifact.

## Resume and cover letter

`write_resume(llm_response, personal, output_path)` and `write_cover_letter(llm_response, personal, output_path, gaps_expected, company=None)` (`output_path` required — no default filename, so nothing lands in the process's working directory by accident) in `write.py` take the raw JSON string from `llm/client.py`, `json.loads()` it, validate against a `pydantic` model (`Resume`/`CoverLetter`, mirroring `RESUME_SCHEMA`/`COVER_LETTER_SCHEMA` — see `prompts/README.md`), fill a Jinja2 HTML/CSS template (`templates/resume.html` / `templates/cover_letter.html`, plus shared `templates/_style.html` / `templates/_macros.html` partials), and render to PDF via Playwright print-to-PDF.

**Templating: Jinja2 with autoescape** — escaping (`<`, `>`, `&`, quotes) is handled by the templating engine, not by hand; verified against LLM-shaped input containing `<`/`&`. `personal` is `profile.json`'s `personal` block, shared across both documents' headers. One template block per `projects[]` entry (`repo` linked off the last bullet, `status` folded into the name when present); `skills` grouped by category into one line each (`_category_label()` maps known keys like `ai_ml`/`devops` to `AI/ML`/`DevOps`, since the raw keys don't title-case cleanly); `certifications[]` filling a Training & Certificates section.

**Return type: `WriteResult(path: str | None, error: WriteError | None, content: Resume | CoverLetter | None)`.** `content` is the parsed model whenever the response validated — the review email and `tracking/` need the full text, and the PDF is deleted once the application concludes, so the text can't be recovered from the file later. `WriteError.INVALID_JSON`/`VALIDATION_ERROR` mean the LLM response was unusable — no real content to show (`path` and `content` both `None`), so this can't route through the review-email design. `WriteError.OVERFLOW` means the opposite: valid content that's simply too long — the case the review-email design exists for — so it carries both `content` and `path` (the file stays on disk until the user answers). `WriteError.RENDER_FAILURE` and `WriteError.LLM_FAILURE` are never raised by `write.py` itself — Playwright/pypdf errors and `OllamaError` propagate as real exceptions, and `generate.py` catches them at the call site and constructs the `WriteResult` there, since a caller may want to handle infrastructure trouble (e.g. abort the whole run) differently than a resolvable failure.

**One-page enforcement:** render first with content free to flow past one page, then check the rendered PDF's page count via `pypdf` (Playwright's `page.pdf()` doesn't report a count the way `pdflatex` did). Rendering never clips overflow with CSS — that would silently truncate content, and a resume cut off mid-sentence must never ship unnoticed. A page count other than 1 returns `WriteResult(path=output_path, error=WriteError.OVERFLOW, content=...)`. Routing that onward to the user isn't built yet — that's `review_gate/`'s job.

## Cover letter gaps paragraph

`CoverLetter.gaps` is present exactly when at least one known gap applies to the posting — decided in code before the LLM runs (`../gaps/`). `cover_letter_schema(gaps_expected)` makes it a required field or removes it from the schema entirely, and `write_cover_letter(..., gaps_expected, ...)` re-checks the parsed letter: a missing gaps paragraph when one is expected, or one present when none is, is a `VALIDATION_ERROR` (so a model that ignores the schema can neither drop a gap nor volunteer one).

## Placeholder text ("not provided")

The system prompt tells the model to answer `"not provided"` when the facts don't cover something — legitimate in application form answers, but in a resume or cover letter it would be printed onto the page as-is. So the prompt limits it to form answers (optional resume/cover-letter fields are left out instead), and the models enforce it independently: `OptionalText` fields (`status`, `repo`, `verification_url`, `gaps`) turn a placeholder or empty string into `None`, so the template skips them; `RequiredText` fields (`summary`, `opening`, project `name`, each bullet and skill, ...) reject one as a `VALIDATION_ERROR`. These validators don't change the JSON schema sent to Ollama.

## Application answers

`parse_application_answers(llm_response, questions)` hands the JSON (`{field_id: answer}`) to `form_automation/` directly — no template, no PDF, no page-count check. No `pydantic` model with named fields, since `field_id`s are posting-specific rather than a fixed schema — validated structurally via `pydantic.TypeAdapter(dict[str, str])` instead, against exactly what `prompts/application.py`'s prompt promises. Same `json.loads()`-then-validate flow and the same `INVALID_JSON`/`VALIDATION_ERROR` distinction, returned as `ParseResult(answers: dict[str, str] | None, error: WriteError | None, flagged: dict[str, WriteError])`. `WriteError.OVERFLOW` doesn't apply here.

On top of that, answers are checked against the `questions` they were generated for: keys that don't exactly match the real `field_id`s are a `VALIDATION_ERROR` (the structured-output schema already forces them — see `../llm/README.md` — this guards against a model that doesn't honor it). Then per field: a `"not provided"`/empty answer is `UNANSWERED`, one over its `max_length` is `ANSWER_TOO_LONG` (checked here rather than in the schema, since constrained decoding would silently cut the answer off mid-sentence). Either keeps `.answers` intact, lists each offending field in `.flagged`, and sets `.error` (`ANSWER_TOO_LONG` wins if both occur) — the application needs human review before anything is submitted. `form_automation/` (not yet built) is the intended consumer of `.answers`.

## Test coverage

No committed test suite (tests are the user's to write). Behavior described above was checked with throwaway scripts during development — mocked LLM responses for each `WriteError` path, real Chromium rendering for overflow — not with tests in the repo.

See `../README.md`.
