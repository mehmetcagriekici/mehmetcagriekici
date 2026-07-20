# Job-application automation project (planning stage)

- We are designing an automated AI agent to apply to jobs for the user, built inside this folder (`agent/`).
- **No code.** Do not write, scaffold, or edit any code for this project unless the user explicitly asks for code to be written. Default mode is discussion/design only.
- Act as a rubber duck: help the user think through the design out loud, ask clarifying questions, poke at assumptions and edge cases — don't jump to solutions or implementation.
- This constraint applies specifically to the agent-building project itself, not to the existing cover-letter/resume workflow at the repo root, which continues as-is and is governed by the root `CLAUDE.md`.
- **Claude Code sessions running inside `agent/` only have this `CLAUDE.md` loaded — the root `CLAUDE.md` is not automatically visible from here.** If a task needs the root-level conventions (cover letters, `applications.md`, honesty rules), read `/home/callsower/mehmetcagriekici/CLAUDE.md` explicitly rather than assuming it's already in context.

## Folder structure
- `agent/` holds everything belonging to the automation project, kept separate from the manual cover-letter workflow files at repo root (`cover.tex`, `resume.pdf`, `applications.md`), which are unaffected by this project.
- `agent/source_of_truth/profile.json` is the profile store — the structured, hand-maintained source of truth (education, projects, skills, job preferences, etc.) that the agent will draw from to generate per-job resumes/cover letters and score fit. Built from `resume.pdf`, with any gaps filled in by the user directly (never inferred/guessed). Built and in use.

### Planned folder structure (scaffolded as placeholders — no implementation code exists for any of this)
Mirrors the pipeline modules from the design discussion, one folder per module, each currently just a `README.md` stub restating its purpose:
- `agent/source_of_truth/` — profile store. Done, in use.
- `agent/sourcing/` — pulls job listings from ATS-backed career pages only (v1 scope excludes LinkedIn/Glassdoor/JobLeads). Per-ATS adapters (Greenhouse, Lever, Ashby, Workday, etc.), shared with `form_automation/` where possible since both need to know the same ATS's structure.
- `agent/matching/` — fit-scoring: job description + profile store → a match-strength score (requirements diffed against structured profile-store fields, not LLM self-reported confidence) + reasoning.
- `agent/tailoring/` — generates a per-job resume variant and cover letter from profile-store facts. Reorders/rephrases/emphasizes only — never adds a fact not present in the profile store.
- `agent/form_automation/` — per-ATS-type form-filling (not per-company). Reads a form's fields, maps them to the profile store, fills them; free-text questions get routed to an LLM call with the job description as context.
- `agent/tracking/` — state store logging what was applied to, when, status, and the generated materials, to avoid duplicates and support follow-up. Storage format not yet decided.
- `agent/review_gate/` — confidence-threshold + manual-override logic deciding auto-submit vs. route-to-human-review (permanent threshold, not a one-time trust ladder — see design history), plus outbound notifications for anything queued for review.

Not yet decided: whether this one-folder-per-module split matches how the code actually ends up organized once implementation starts (it may end up as one app internally organized by module instead of top-level folders), and where generated per-job artifacts (tailored resume/cover letter) physically land — written to disk per application, or only ever stored in the tracking store. The folders existing now does not resolve this — check with the user before writing actual implementation code into any of them.
