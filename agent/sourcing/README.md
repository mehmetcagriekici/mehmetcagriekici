# sourcing

Pulls job listings from ATS-backed career pages only (v1 scope excludes LinkedIn/Glassdoor/JobLeads). Per-ATS adapters (Greenhouse, Lever, Ashby, Workday, etc.), shared with `form_automation/` where possible since both need to know the same ATS's structure.

**Language: Python** — an internal module of the shared Python service (see tech stack in `../README.md`), called by each Go orchestrator instance. Each running Go instance is configured with which ATS to target, a role/keyword filter (e.g. "python positions" vs "go positions"), and a run-duration after which it times out. The role filter only narrows what sourcing pulls in; it doesn't change matching or tailoring behavior downstream.

Planning stage — no code yet. See `../CLAUDE.md`.
