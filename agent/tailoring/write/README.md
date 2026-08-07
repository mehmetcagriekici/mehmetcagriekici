# write

Takes each LLM call's JSON output and turns it into that call's final artifact.

## Resume and cover letter

`write_resume(llm_response, personal, output_path)` and `write_cover_letter(llm_response, personal, company, output_path)` in `write.py` take the raw JSON string from `llm/client.py`, `json.loads()` it, validate against a `pydantic` model (`Resume`/`CoverLetter`, mirroring `RESUME_SCHEMA`/`COVER_LETTER_SCHEMA` — see `prompts/README.md`), fill a Jinja2 HTML/CSS template (`templates/resume.html` / `templates/cover_letter.html`, plus shared `templates/_style.html` / `templates/_macros.html` partials), and render to PDF via Playwright print-to-PDF.

**Templating: Jinja2 with autoescape** — escaping (`<`, `>`, `&`, quotes) is handled by the templating engine, not by hand; verified against LLM-shaped input containing `<`/`&`. `personal` is `profile.json`'s `personal` block, shared across both documents' headers. One template block per `projects[]` entry (`repo` linked off the last bullet, `status` folded into the name when present); `skills` grouped by category into one line each (`_category_label()` maps known keys like `ai_ml`/`devops` to `AI/ML`/`DevOps`, since the raw keys don't title-case cleanly); `certifications[]` filling a Training & Certificates section.

**Return type: `WriteResult(path: str | None, error: WriteError | None)`.** `WriteError.INVALID_JSON`/`VALIDATION_ERROR` mean the LLM response was unusable — no real content to show, so this can't route through the review-email design. `WriteError.OVERFLOW` means the opposite: valid content that's simply too long — the case the review-email design exists for. `WriteError.RENDER_FAILURE` and `WriteError.LLM_FAILURE` are never raised by `write.py` itself — Playwright/pypdf errors and `OllamaError` propagate as real exceptions, and `generate.py` catches them at the call site and constructs the `WriteResult` there, since a caller may want to handle infrastructure trouble (e.g. abort the whole run) differently than a resolvable failure.

**One-page enforcement:** render first with content free to flow past one page, then check the rendered PDF's page count via `pypdf` (Playwright's `page.pdf()` doesn't report a count the way `pdflatex` did). Rendering never clips overflow with CSS — that would silently truncate content, and a resume cut off mid-sentence must never ship unnoticed. A page count other than 1 returns `WriteResult(path=None, error=WriteError.OVERFLOW)`. Routing that onward to the user isn't built yet — that's `review_gate/`'s job.

## Application answers

`parse_application_answers(llm_response)` hands the JSON (`{field_id: answer}`) to `form_automation/` directly — no template, no PDF, no page-count check. No `pydantic` model with named fields, since `field_id`s are posting-specific rather than a fixed schema — validated structurally via `pydantic.TypeAdapter(dict[str, str])` instead, against exactly what `prompts/application.py`'s prompt promises. Same `json.loads()`-then-validate flow and the same `INVALID_JSON`/`VALIDATION_ERROR` distinction, returned as `ParseResult(answers: dict[str, str] | None, error: WriteError | None)`. `WriteError.OVERFLOW` doesn't apply here. `form_automation/` (not yet built) is the intended consumer of `.answers`.

## Test coverage

`write_resume`/`write_cover_letter`: valid JSON with `<`/`&`-bearing strings and real contact data rendering to one page; syntactically invalid JSON; valid JSON missing a required field; valid JSON that overflows one page — each asserted independently. `parse_application_answers`: a valid `{field_id: answer}` dict; invalid JSON syntax; a non-string answer value and a non-dict payload.

See `../README.md`.
