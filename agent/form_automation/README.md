# form_automation

Per-ATS-type form-filling (not per-company). Reads a form's fields, maps them to the profile store, fills them; free-text questions get routed to an LLM call with the job description as context.

**Language: TypeScript.** Runs as one shared singleton service (not one per ATS instance) called by every Go orchestrator instance — see tech stack in `../README.md`. Likely browser automation (Playwright-style) for JS-heavy application forms.

Planning stage — no code yet. See `../CLAUDE.md`.
