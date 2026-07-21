# source_of_truth

Profile store — the structured, hand-maintained source of truth (education, projects, skills, job preferences, etc.) that the agent will draw from to generate per-job resumes/cover letters and score fit. Built from `resume.pdf`, with any gaps filled in by the user directly (never inferred/guessed).

Stays a single shared, read-only resource across every running container instance (see deployment model in `../README.md`) — no per-instance customization of the profile store itself.

Done, in use — see `profile.json`. Everything else in `../` is still planning stage; see `../CLAUDE.md`.
