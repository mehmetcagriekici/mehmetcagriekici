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

Not yet decided: where generated per-job artifacts (tailored resume/cover letter) physically land — written to disk per application, or only ever stored in the tracking store. The folders existing now does not resolve this — check with the user before writing actual implementation code into any of them.

## Architecture (decided, still design-only — no code written)

**Deployment model:** one Go binary, run as multiple configured orchestrator instances — one instance per ATS target (Greenhouse, Lever, etc.), not per module and not per job board (LinkedIn/Glassdoor stay out of v1 scope). Each instance is configured with which ATS to target, a role/keyword filter (e.g. "python positions" vs "go positions"), and a run-duration; it polls that ATS repeatedly, then times out and stops. The user starts/restarts instances manually and reads the end-of-run report afterward — this is not a fully hands-off, zero-touch system.

**Tech stack — three languages, three shared singleton services, not per-instance:**
- **Go** — orchestrator. Thin: each per-ATS instance's whole job is bridging the Python service's generated output (tailored resume/cover letter, form-field answers) to the TypeScript form-filling service, and creating/finalizing the application. Go does not own pipeline sequencing, tracking-store writes, or review-gate email triggering — those are internal to Python.
- **Python** — one shared service (not one per ATS instance) that internally owns `sourcing/`, `matching/`, `tailoring/`, `tracking/`, and `review_gate/` as modules calling each other directly. Hosts local LLM inference via **Ollama, CPU-only (no GPU available)**, which caps realistic model size to roughly 7-8B quantized for reasonable latency. The LLM's job is constrained to organizing/formatting resume and cover-letter content and answering form fields strictly from `source_of_truth/profile.json` — never hallucinating facts not present there, same principle as the honesty rules in the root `CLAUDE.md`.
- **TypeScript** — one shared service (not one per ATS instance) handling `form_automation/` (likely browser automation for JS-heavy application forms).

**Matching approach:** hybrid — structured field-diff plus embedding/keyword search runs against every sourced listing cheaply and deterministically (no LLM call). The LLM is reserved as a **tiebreaker only for listings landing close to the auto-submit/review threshold**, specifically for judging soft/inferred requirements (e.g. "strong communication skills") that don't reduce to a checkable profile-store field.

**Tracking:** must be a single store shared across all concurrently-running Go orchestrator instances (reads *and* writes), not local per-instance state — otherwise two instances (e.g. Greenhouse + Lever running at once) could double-apply to the same company/role. Storage format not yet decided. `source_of_truth/profile.json` stays read-only and shared by contrast — the pipeline never writes to it.

**Review gate:** no dashboard. Push notification via **email** with clickable approve/reject links fires immediately when something routes to review; a separate end-of-run report (submitted, matched-but-not-submitted, skipped, errors) is generated when an instance times out, for the user to read at their own pace. If the user doesn't respond before the instance's run ends, the item **defaults to reject**. Not yet decided: exact email content/format, and the technical mechanism the approve/reject links hit.
