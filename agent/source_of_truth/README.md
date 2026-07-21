# source_of_truth

Profile store — the structured, hand-maintained source of truth (education, projects, skills, job preferences, etc.) that the agent will draw from to generate per-job resumes/cover letters and score fit. Built from `resume.pdf`, with any gaps filled in by the user directly (never inferred/guessed).

**Expanding from one file to several (decided direction, more may follow).** Currently just `profile.json`. Three planned additions so far:
1. **Projects-detail file** — deeper per-project detail than the `projects` array in `profile.json` (tech stack, turning points, planning process, structure) — giving the LLM honest incident-level material for project-specific behavioral questions ("tell me about a time you solved a bug"), rather than only feature-level bullets.
2. **General-stories file** — real anecdotes not scoped to any one project, for behavioral questions the projects-detail file can't answer ("describe a time you got difficult feedback," "how do you handle disagreement").
3. **Known-gaps file**, hand-maintained by the user directly (not pipeline-generated) — honest, pre-considered phrasing for this candidate's recurring gaps (in-progress degree, no professional experience, GPA, sponsorship need). Carries forward the manual cover-letter workflow's stance of naming gaps directly rather than glossing over them (see root `CLAUDE.md`), since a small CPU-only local model is more likely to soften/omit a gap by default, and some pipeline output gets auto-submitted without a human reading it first.

EEO/legal-boilerplate answers are also being added as deterministic fields in `profile.json` (alongside `job_preferences`), same reasoning as everything else — never left for the LLM to guess.

**Deterministic vs. generative split:** work authorization, visa sponsorship, salary, notice period, language, and EEO questions are answered directly from structured fields here — no LLM involved. The LLM only touches this store for generative work (resume tailoring, cover letters, free-text behavioral questions), always adapting real content from these files, never inventing. No answer caching for now — regenerated fresh every time.

Stays a single shared, read-only resource across every running Go orchestrator instance (see deployment model in `../README.md`) — no per-instance customization of the profile store itself. Read directly by the Python service's `sourcing/`, `matching/`, and `tailoring/` modules (see tech stack in `../README.md`); Go and TypeScript work from Python's generated output rather than reading `profile.json` themselves.

Done, in use — see `profile.json`. Everything else in `../` is still planning stage; see `../CLAUDE.md`.
