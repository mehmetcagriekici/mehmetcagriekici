# source_of_truth

Profile store — the structured, hand-maintained source of truth (education, projects, skills, job preferences, etc.) that the agent will draw from to generate per-job resumes/cover letters and score fit. Built from `resume.pdf`, with any gaps filled in by the user directly (never inferred/guessed).

Stays a single shared, read-only resource across every running Go orchestrator instance (see deployment model in `../README.md`) — no per-instance customization of the profile store itself. Read directly by the Python service's `sourcing/`, `matching/`, and `tailoring/` modules (see tech stack in `../README.md`); Go and TypeScript work from Python's generated output rather than reading `profile.json` themselves.

Done, in use — see `profile.json`. Everything else in `../` is still planning stage; see `../CLAUDE.md`.
