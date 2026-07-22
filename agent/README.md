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
| [`matching/`](matching/README.md) | Done, in use — design and code complete, pending real-data threshold recalibration | Fit-scoring against the profile store |
| [`tailoring/`](tailoring/README.md) | Planned | Generates per-job resume/cover letter |
| [`form_automation/`](form_automation/README.md) | Planned | Per-ATS form-filling |
| [`tracking/`](tracking/README.md) | Planned | State store for what's been applied to |
| [`review_gate/`](review_gate/README.md) | Planned | Application Controller — checks generated materials for honesty/relevance before submission |

Whether this one-folder-per-module split survives into implementation, and where generated per-job artifacts land, are both still open — see `CLAUDE.md`.

## Deployment model (decided, still design-only)

Runs on a local k8s distro (k3s/minikube-style) on the user's own computer — not a cloud-hosted cluster. The Go orchestrator (see Tech stack below) runs as multiple configured instances, potentially several running simultaneously, — one instance per ATS target (e.g. Greenhouse, Lever), not per module and not per job board (LinkedIn/Glassdoor stay out of scope). What differs per Go instance is config: which ATS, and a run-duration (e.g. "run for a day") — role/location/tech filtering is no longer part of instance config (decided 2026-07-22); that fit decision now happens entirely downstream in `matching/`, against a generalized preference set shared in `source_of_truth/` (see Tech stack below). An instance polls its ATS repeatedly for the configured duration, then times out and stops; the user starts/restarts instances manually and reads the end-of-run report afterward.

The Python and TypeScript services are **not** per-instance — they're shared singletons every Go instance calls into (see Tech stack below).

`source_of_truth/` (expanding beyond `profile.json` — see below) stays a single shared, read-only resource every instance reads from — no per-instance customization of the profile store itself. `tracking` is the opposite case: a single shared store all concurrently-running Go instances read *and write*, so two instances (e.g. a Greenhouse instance and a Lever instance running at once) can't double-apply to the same company/role.

Review-gate notifications go out over email: a push email fires immediately when something is routed to review, with clickable approve/reject links (no dashboard); if the user doesn't respond before that instance's run times out, the item defaults to reject. The email shows the full generated package inline (resume text, cover letter text, filled form field answers — not attachments, not summarized) plus a log/report-style breakdown of why that specific application was flagged (the Application Controller's honesty/relevance verdict and reasoning, or which manual-override rule fired). Separately, each instance's end-of-run report summarizes everything it did (submitted, matched-but-not-submitted, skipped, errors) for the user to read at their own pace.

Sending uses a dedicated Gmail account created for the app (no inbound reachability needed). The approve/reject tap opens a one-tap confirm page (not a bare link, to avoid email security scanners auto-triggering the action) reachable via a **Cloudflare Tunnel** — chosen over Tailscale because it needs to open in any browser with no special app installed. Requires a domain (~$10-15/year, not yet owned) and a token-protected link, since the endpoint is genuinely public.

## Tech stack (decided, still design-only)

Three languages, three shared singleton services (not one trio per ATS instance):

| Service | Language | Owns |
|---|---|---|
| Orchestrator | Go | Bridges the Python service's generated output to the TypeScript form-filling service, creates/finalizes the application. Thin — does not own pipeline sequencing, tracking writes, or review-gate email triggering. |
| Content/logic service | Python | `sourcing/`, `matching/`, `tailoring/`, `tracking/`, `review_gate/` — all internal modules calling each other directly, not routed through Go. Hosts local LLM inference via **Ollama, CPU-only** (no GPU available), capping realistic model size to roughly 7-8B quantized. |
| Form service | TypeScript | `form_automation/` — likely browser automation for JS-heavy application forms. |

The LLM's role is constrained to organizing/formatting resume and cover-letter content and answering form fields strictly from `source_of_truth/`, never hallucinating facts not present there — same principle as the honesty rules in the root `CLAUDE.md`. `source_of_truth/` is expanding beyond `profile.json` to support this: a projects-detail file (incident-level material per project), a general-stories file (non-project-specific anecdotes), and a hand-maintained known-gaps file (honest phrasing for this candidate's recurring gaps — see `source_of_truth/README.md`).

**Matching is fully deterministic — no LLM in the fit decision (updated 2026-07-22, single-call design supersedes the earlier two-stage gate).** One call, `hybrid_search(job_posting, source_of_truth)`, per posting — no separate `job_config` stage. `job_config` is now ATS-only, a sourcing/routing concern; role/location/tech preferences are generalized into a shared preference set inside `source_of_truth` instead of a per-instance filter. `hybrid_search` itself (embedding search + keyword search via RRF fusion, sentence-transformers embeddings, CPU-only, cosine similarity — no structured field-diff) is complete. Corpus/query direction is decided (2026-07-22): `source_of_truth` is the indexed corpus, one `Document` per atomic fact, `job_posting` is the query — so results come back as your own facts ranked against a posting. The pass/fail signal is also decided: the fused `rrf_score` (both BM25 and semantic, as already built), accepting its known imprecision (rank-based, not similarity-magnitude-based) rather than reworking `hybrid_search` for a more precise raw score. The threshold rule is decided and empirically corrected: a posting passes when at least 4 distinct facts from `source_of_truth` score `rrf_score` ≥ 0.028 against it (the original 0.026 guess failed to discriminate a real mismatched posting from a real relevant one — see `matching/README.md`). Document construction is also built (`matching/document_builder/`) — matching's design is now settled end-to-end, pending recalibration against real data. No caching layer — all embeddings are recomputed on every comparison. Soft/inferred requirements (e.g. "strong communication skills") are dropped rather than arbitrated — an accepted tradeoff for now.

**Pipeline (decided 2026-07-22):** `Data -> Hybrid Search -> Application Generator -> Application Controller -> Application API`. `matching/` is Hybrid Search; `tailoring/` is the Application Generator, running unconditionally on every posting that clears the match step and generating from the full structured record (not the flattened `Document`); `review_gate/` is the Application Controller — a second LLM checking the generator's output for honesty (vs. `source_of_truth`) and relevance (vs. the job posting), any failure on either routing to human review with no severity distinction; `form_automation/` (bridged through Go) is the Application API, firing only once the Controller or the user approves.
