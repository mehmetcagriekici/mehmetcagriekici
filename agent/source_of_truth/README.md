# source_of_truth

The structured, hand-maintained profile store the rest of the pipeline reads from — education, projects, skills, job preferences, and more. Built from `resume.pdf`, with gaps filled in directly by the user (never inferred or guessed). Read-only: nothing in the pipeline writes here.

## Files

- **`profile.json`** — the core profile: personal info, summary, skills, projects, education, certifications, `job_preferences` (deterministic screening answers: salary, visa, notice period, language), and `eeo` (legal/demographic boilerplate — race/ethnicity stored with a note that "decline to state" is always valid; sexual orientation flagged "answer only if asked, never volunteer").
- **`projects-detail.json`** — deeper per-project material than `profile.json`'s `projects` array (tech stack, turning points, planning process, structure), giving the LLM incident-level detail for project-specific behavioral questions. Merged with `profile.json`'s `projects` by name at query time. Covers 7 of `profile.json`'s 8 projects; the newest (Message Notification Router) is pending detail from the user.
- **`general-stories.json`** — real anecdotes not scoped to any one project, for behavioral questions the projects-detail file can't answer: rebuilding a study streak through visible progress-tracking; redoing the Backend Developer Path in TypeScript for depth; using AI tools for guided-project research and then carrying those concepts into independent work.
- **`known-gaps.json`** — hand-maintained, honest phrasing for this candidate's recurring gaps: no professional experience (~1 year self-directed since July 2025), in-progress degree (Management Information Systems, Ankara University Open Education Faculty, expected 2029), GPA 2.6/4.0, and visa sponsorship (needed for on-site/relocation, not for remote work from Turkey). Carries forward the root `CLAUDE.md`'s rule of naming gaps directly rather than softening them, since a small local model tends to omit them by default and some pipeline output ships without human review.
- **`preferences.json`** — a shared statement of what roles/locations/stacks this candidate is open to (backend primary, fullstack/AI-ML acceptable; remote preferred, open to Europe/USA/Canada; Go and Python over TypeScript). Feeds `matching/`'s `hybrid_search` call. Distinct from `profile.json`'s `job_preferences`, which answers deterministic screening questions rather than fit — `preferences.json` points back to that instead of duplicating it.

## Deterministic vs. generative

Work authorization, visa, salary, notice period, language, and EEO questions are answered directly from structured fields here — no LLM. The LLM only touches this store for generative work (resumes, cover letters, free-text behavioral answers), always adapting real content, never inventing. No caching — every answer regenerates fresh.

Read directly by `sourcing/`, `matching/`, and `tailoring/`; Go and TypeScript work from Python's generated output rather than reading `profile.json` themselves.

Status: all five files built and in use. `matching/` is built on top of this store — see `../matching/README.md`. See `../CLAUDE.md`.
