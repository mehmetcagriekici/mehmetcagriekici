# write

Takes each call's JSON output (decided 2026-08-04 — see `prompts/README.md`'s Output format note) and turns it into that call's final artifact.

For the resume and cover letter calls: parse the JSON, escape each string field for LaTeX (`&`, `%`, `$`, `#`, `_`, `{`, `}`, `~`, `^`, `\`) — deterministic code's job, not the model's, precisely to avoid an unescaped character breaking `pdflatex` compilation outright — then map the escaped fields into `../resume_template.tex` / `../cover_template.tex` (e.g. one `\project{name}{tech}{dates}{bullets}` call per resume JSON array entry) and compile to PDF via `pdflatex`. Same one-page hard-constraint, compile-once-no-retry enforcement described in `../README.md` (overflow emails the user directly rather than retrying) — a hard compile failure from bad LaTeX would need to route the same way, though that's not yet explicitly decided.

For the application call, the JSON (`{field_id: answer}`) is handed to `form_automation/` directly — no LaTeX, no PDF.

Currently an empty stub (`write.py`) — not yet implemented. See `../README.md`.
