# form_automation

Per-ATS-type form-filling (not per-company). Reads a form's fields, maps them to the profile store, fills them; free-text questions get routed to an LLM call with the job description as context.

Runs inside the same per-ATS container instance as `sourcing/` (see deployment model in `../README.md`), sharing that instance's ATS adapter.

Planning stage — no code yet. See `../CLAUDE.md`.
