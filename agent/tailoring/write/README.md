# write

Takes each call's raw `llm_ollama` output string and turns it into that call's final artifact.

For the resume and cover letter calls, that means filling the generated content into `../resume_template.tex` / `../cover_template.tex` and compiling to PDF via `pdflatex` — same one-page hard-constraint, compile-once-no-retry enforcement described in `../README.md` (overflow emails the user directly rather than retrying). For the application call, the string maps to form-field answers consumed by `form_automation/` rather than compiled to anything.

Currently an empty stub (`write.py`) — not yet implemented. See `../README.md`.
