# agent

Job-application automation project — **planning stage, no code yet**. An AI agent that will apply to jobs on the user's behalf.

Full design context (scope, constraints, decisions) lives in [`CLAUDE.md`](CLAUDE.md), not here. Default mode for this project is discussion/design only — implementation code is written only when explicitly asked.

Kept separate from the manual cover-letter/resume workflow at the repo root (`../cover.tex`, `../resume.pdf`, `../applications.md`), which is unaffected by this project.

## Modules

Mirrors the planned pipeline, one folder per stage:

| Folder | Status | Purpose |
|---|---|---|
| [`source_of_truth/`](source_of_truth/README.md) | Done, in use | Profile store the rest of the pipeline reads from |
| [`sourcing/`](sourcing/README.md) | Planned | Pulls job listings from ATS career pages |
| [`matching/`](matching/README.md) | Planned | Fit-scoring against the profile store |
| [`tailoring/`](tailoring/README.md) | Planned | Generates per-job resume/cover letter |
| [`form_automation/`](form_automation/README.md) | Planned | Per-ATS form-filling |
| [`tracking/`](tracking/README.md) | Planned | State store for what's been applied to |
| [`review_gate/`](review_gate/README.md) | Planned | Auto-submit vs. human-review threshold |

Whether this one-folder-per-module split survives into implementation, and where generated per-job artifacts land, are both still open — see `CLAUDE.md`.

## Deployment model (decided, still design-only)

One container image, run as multiple configured instances — one instance per ATS target (e.g. Greenhouse, Lever), not per module and not per job board (LinkedIn/Glassdoor stay out of scope). `sourcing`, `matching`, `tailoring`, `form_automation`, `tracking`, and `review_gate` are the same code in every instance; what differs per instance is config: which ATS, role/keyword filters, and a run-duration (e.g. "run for a day"). A container polls its ATS repeatedly for the configured duration, then times out and stops; the user starts/restarts instances manually and reads the end-of-run report afterward.

`source_of_truth/profile.json` stays a single shared, read-only resource every instance reads from — no per-instance customization of the profile store itself. `tracking` is the opposite case: a single shared store all concurrently-running instances read *and write*, so two instances (e.g. a Greenhouse container and a Lever container running at once) can't double-apply to the same company/role.

Review-gate notifications go out over email: a push email fires immediately when something is routed to review, with clickable approve/reject links (no dashboard); if the user doesn't respond before that instance's run times out, the item defaults to reject. Separately, each instance's end-of-run report summarizes everything it did (submitted, matched-but-not-submitted, skipped, errors) for the user to read at their own pace.
