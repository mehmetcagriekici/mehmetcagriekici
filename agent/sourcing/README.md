# sourcing

Pulls job listings from ATS-backed career pages (Greenhouse, Lever, Ashby, Workday, etc.) — v1 scope, LinkedIn/Glassdoor/JobLeads excluded. Per-ATS adapters, shared with `form_automation/` where possible since both need to know the same ATS's structure.

**Language: Python** — an internal module of the shared Python service (see `../README.md`), called by each Go orchestrator instance. Each Go instance is configured with which ATS to target, a run-duration, and an application cap; a run fetches every listed company's board once at the start — no re-polling mid-run.

**Company list:** ATS public APIs are per-company — there's no feed of every job on an ATS — so each instance polls a list of companies on its ATS. v1 keeps that list hand-maintained, in its own JSON file in this folder (`{ats, company, enabled, note}` per entry), shared by all instances; the company's display name comes from the ATS response, not the list; automatic discovery is a deferred later phase. **Normalized posting:** no `requirements` field — sourcing doesn't try to find the requirements section (headings vary per company, and a miss would silently skip the experience gap). It guarantees `description` is plain text with each HTML bullet on its own line; downstream rules (e.g. `tailoring/gaps/`'s years-of-experience check) scan every line. Each normalized posting also keeps `raw`, the untouched ATS response, for debugging rules against what the ATS actually sent. Full shape in `../CLAUDE.md`.

**Stale filter:** postings older than 30 days (first-published date where available, else updated date) are dropped and reported as "skipped (stale)" in the end-of-run report — the only filter sourcing applies.

**Errors:** ~1-2 s between company boards; a board that fails to fetch, or a single posting that can't be normalized, is skipped and listed in the end-of-run report — never silently dropped, and never auto-disabled (the pipeline doesn't write to the company list). Everything else those companies list goes through; role/location/tech fit is decided entirely downstream by `matching/`'s `hybrid_search` against `source_of_truth/preferences.json` — sourcing applies no fit filter of its own.

Planning stage — no code yet. See `../CLAUDE.md`.
