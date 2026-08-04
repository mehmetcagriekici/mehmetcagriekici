# write

Takes each call's JSON output (decided 2026-08-04 — see `prompts/README.md`'s Output format note) and turns it into that call's final artifact.

For the resume and cover letter calls: parse the JSON, escape each string field for LaTeX (`&`, `%`, `$`, `#`, `_`, `{`, `}`, `~`, `^`, `\`) — deterministic code's job, not the model's, precisely to avoid an unescaped character breaking `pdflatex` compilation outright — then map the escaped fields into `../resume_template.tex` / `../cover_template.tex` and compile to PDF via `pdflatex`. For the resume specifically (schema in `prompts/README.md`'s Resume schema note): one `\project{name}{dates}{tech}` call per `projects[]` entry (the macro itself takes only those 3 args), followed by its `description` line and `bullets` itemize block, with `repo` appended as a `\href` off the last bullet and `status` folded into the name argument only when present; `skills` iterates its category keys into one `\item \textbf{category:} ...` line each; `certifications[]` fills the `Training \& Certificates` section (previously static content — now one block per entry, same shape as the resume's existing hand-written Boot.dev block). Same one-page hard-constraint, compile-once-no-retry enforcement described in `../README.md` (overflow emails the user directly rather than retrying) — a hard compile failure from bad LaTeX would need to route the same way, though that's not yet explicitly decided.

For the application call, the JSON (`{field_id: answer}`) is handed to `form_automation/` directly — no LaTeX, no PDF.

Currently an empty stub (`write.py`) — not yet implemented. See `../README.md`.
