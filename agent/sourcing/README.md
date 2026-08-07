# sourcing

Pulls job listings from ATS-backed career pages (Greenhouse, Lever, Ashby, Workday, etc.) — v1 scope, LinkedIn/Glassdoor/JobLeads excluded. Per-ATS adapters, shared with `form_automation/` where possible since both need to know the same ATS's structure.

**Language: Python** — an internal module of the shared Python service (see `../README.md`), called by each Go orchestrator instance. Each Go instance is configured with which ATS to target and a run-duration after which it stops polling.

Sourcing pulls in everything the configured ATS lists; role/location/tech fit is decided entirely downstream by `matching/`'s `hybrid_search` against `source_of_truth/preferences.json` — sourcing applies no filter of its own.

Planning stage — no code yet. See `../CLAUDE.md`.
