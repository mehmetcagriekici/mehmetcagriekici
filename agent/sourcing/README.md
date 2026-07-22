# sourcing

Pulls job listings from ATS-backed career pages only (v1 scope excludes LinkedIn/Glassdoor/JobLeads). Per-ATS adapters (Greenhouse, Lever, Ashby, Workday, etc.), shared with `form_automation/` where possible since both need to know the same ATS's structure.

**Language: Python** — an internal module of the shared Python service (see tech stack in `../README.md`), called by each Go orchestrator instance. Each running Go instance is configured with which ATS to target and a run-duration after which it times out (decided 2026-07-22: role/location/tech filtering is no longer part of instance config — see `../matching/README.md`). Sourcing now pulls in everything the configured ATS lists; role/location/tech fit is decided entirely downstream by `matching/`'s single `hybrid_search` call against a generalized preference set in `source_of_truth`, not by what sourcing chooses to pull in.

Planning stage — no code yet. See `../CLAUDE.md`.
