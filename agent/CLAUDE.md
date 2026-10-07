# Job-application automation project

- We are designing and building an automated AI agent to apply to jobs for the user, inside this folder (`agent/`). `matching/` and `tailoring/` have working code; the rest is design (see Status).
- **No code.** Do not write, scaffold, or edit any code for this project unless the user explicitly asks for code to be written. Default mode is discussion/design only.
- Act as a rubber duck: help the user think through the design out loud, ask clarifying questions, poke at assumptions and edge cases — don't jump to solutions or implementation.
- This constraint applies specifically to the agent-building project itself, not to the existing cover-letter/resume workflow at the repo root, which continues as-is and is governed by the root `CLAUDE.md`.
- **Claude Code sessions running inside `agent/` only have this `CLAUDE.md` loaded — the root `CLAUDE.md` is not automatically visible from here.** If a task needs the root-level conventions (cover letters, `applications.md`, honesty rules), read `/home/callsower/mehmetcagriekici/CLAUDE.md` explicitly rather than assuming it's already in context.
- For the design-only folders, a folder existing doesn't mean any implementation exists — check with the user before writing implementation code into any of them (and per the no-code rule above, into the built ones too).

## How the docs are organized

**Each fact about how the project works lives in exactly one place: its module's README.** This file holds only the rules above, the decision log (what was decided, when, and what was rejected), and open questions. When something changes, update the README that owns it and add a dated line to the log — don't restate current behavior here. (Restating it in several places is what made the docs drift apart, 2026-10-07.)

| Topic | Owner |
|---|---|
| Overview, pipeline, deployment, **run lifecycle** (fetch → rank → generate, cap, exclusions, end-of-run report), setup, tech stack | `README.md` |
| Profile store files, deterministic vs. generative answers | `source_of_truth/README.md` |
| Company list, normalized posting shape, stale filter, fetch errors | `sourcing/README.md` |
| Hybrid search, fit facts, threshold, ranking | `matching/README.md` |
| Generation, rendering, one-page rule, cover-letter rules | `tailoring/README.md` (+ `llm/`, `prompts/`, `write/`, `gaps/` READMEs) |
| Which known gaps a letter raises | `tailoring/gaps/README.md` |
| Failure types (content vs. infrastructure) | `tailoring/write/README.md` |
| Application/exclusion records, dedup, file lifecycle | `tracking/README.md` |
| Application Controller, review email, approve/reject links | `review_gate/README.md` |
| Form filling and submission | `form_automation/README.md` |

## Status

- **Built (code, committed):** `source_of_truth/` (data), `matching/`, `tailoring/`. No committed test suite — tests are the user's to write.
- **Design only (README, no code):** `sourcing/`, `form_automation/`, `tracking/`, `review_gate/`, and the runner that ties the pipeline together (ranking, cap, stopping on infrastructure failures, re-check before submit).

## Decision log

Dates are when a decision was made; where a later entry supersedes an earlier one, it says so.

**2026-07-20/21 — scope and deployment**
- v1 targets ATS-backed career pages only. LinkedIn/Glassdoor/JobLeads excluded: login walls, aggressive anti-bot, partner-gated APIs — the highest ToS/account risk. Revisit only as an explicit later phase.
- Local k8s (k3s/minikube-style) on the user's machine, not cloud. One Go binary run as several instances, one per ATS — not per module or job board. The user starts instances manually; not a zero-touch system.
- Review gate is permanent, not "until trusted". Push by email; actions via clickable links, not reply parsing (email clients quote and top-post). Links open a one-tap confirm page, not a bare GET (email scanners prefetch links). Reachable from anywhere in a normal browser: **Cloudflare Tunnel**, not Tailscale (Tailscale needs an app on the phone). Costs a domain (~$10–15/yr, not yet owned); the link is a bearer credential needing token protection. Sent from a dedicated Gmail account. Full generated package shown inline, not summarized or attached — a missed bad generation is worse than a long email. Unanswered at run end defaults to reject.

**2026-07-22 — pipeline and matching**
- Pipeline: `Data -> Hybrid Search -> Application Generator -> Application Controller -> Application API`.
- Review routing is decided by a second LLM (the Controller) checking honesty and relevance — replaces a numeric confidence threshold. Any failure on either check routes to review; a user override list applies on top. Whether it shares the generator's model is undecided.
- Matching is one deterministic `hybrid_search` call per posting — supersedes a two-stage gate. No LLM in the fit decision. Per-instance `job_config` role/location filters are replaced by one shared `preferences.json`; `job_config` is ATS only.
- `source_of_truth` facts are the indexed corpus, one Document per atomic fact; the posting is the query.
- The fused `rrf_score` is used as-is. Considered and declined: carrying a raw semantic-similarity score through fusion (more precise, needed code changes). Accepted: rrf is rank-based, not magnitude-based.
- Soft requirements ("strong communication skills") are dropped, not arbitrated by an LLM.
- Deterministic screening questions (visa, salary, EEO...) come from structured `source_of_truth` fields, never the LLM. No answer caching.

**2026-07-26/27 — tailoring and tracking**
- Output is PDF, written to disk per application. The resume fills a fixed template; the cover letter is rules-based freeform prose. One page is a hard constraint on every generated document.
- Prompt-injection defense is structural (posting text framed as untrusted data), not a detection step; no "injection detected" event.
- `tracking/`: plain JSON files, one per application, keyed by posting id; company+role fallback for reposts with a fresh id, normalized by lowercase + trim only (no fuzzy matching or LLM — "Software Engineer" vs. "…II" must stay distinct). PostgreSQL is a possible future migration, not v1. Must store the full generated text, because disk copies are deleted once an application concludes. Dedup runs right after sourcing, before matching.
- One-page overflow emails the user directly, bypassing the Controller (not a content question); the reply is binary — reject, or approve and continue.

**2026-08-04/05 — rendering**
- Playwright print-to-PDF replaces an earlier LaTeX/`pdflatex` design (never shipped). Rejected: `wkhtmltopdf`/`pdfkit` — unmaintained, old QtWebKit engine, worse page breaks, container pain. The manual workflow at the repo root stays on LaTeX.
- Jinja2 with autoescape, so escaping isn't done by hand per field.
- One page enforced by rendering freely, then counting pages with `pypdf`. Rejected: CSS `overflow: hidden` clipping — it silently truncates.
- The generator consumes matching's fact dicts directly — supersedes resolving ids back to source records.
- Typed `WriteError` results instead of bare `None`; no retries for any failure.

**2026-09-30 — first live runs and code review**
- Known gaps bypass search ("option (b)"): all four gaps once scored below the cutoff, so the letter's gaps paragraph depended on search ranking. Search still decides fit.
- **A gap is raised only if the posting asks for what it's missing** — supersedes "gaps paragraph structurally required, never optional". Decided in plain code before the LLM (the 7B misapplied the rules about half the time). Tried and replaced the same day: a `gap_decisions` field where the model judged each rule itself. Considered and not chosen: post-LLM banned-phrase checks.
- Default model `qwen2.5:14b` (the 7B ignored prompt-only honesty rules). Slow is accepted (~1 h per application). `num_ctx` 16384 — Ollama's default 4096 silently dropped most of the prompt, including the job posting, which is why a letter once invented the company name. JSON-schema-constrained output.
- Matching: token-window chunking (the embedding model silently truncated past 256 tokens); JSON punctuation dropped from BM25.

**2026-10-06/07 — sourcing design, run lifecycle, three external reviews**
- ATS APIs are per-company, so instances poll a hand-maintained JSON company list (`{ats, board, enabled, note}`); automatic discovery deferred (search-engine scraping has LinkedIn's ToS/fragility problems). `board` is the slug, `company` always the display name.
- Normalized posting has no `requirements` field — rules scan description lines instead (heading-guessing fails silently). `raw` ATS response stored but never read; consumers go through `posting_content()`.
- Sourcing's only filter: postings older than 30 days, reported. Boards and postings that fail are skipped and reported; the pipeline never edits the company list.
- **Goal: the best-matching 10–50 applications a week, not every job.** So: rank matches by fit-fact count (ties: newest posting, then id), cap runs by *submitted* applications, one fetch per run, Python owns the run loop (Go passes `{ats, run_duration, application_cap}`).
- Failed or rejected postings never come back: permanent exclusion records in `tracking/`. **Only content failures exclude** (bad output, prompt/output too long, Controller or user rejection); infrastructure failures stop the run and the posting comes back. Timed-out reviews and unanswered overflows aren't exclusions.
- Matching made deterministic (tie-breaking), uncapped, and stricter about what counts as fit (gap, screening, education and logistics facts excluded). Threshold history: 0.026 → 0.028 (07-22) → 0.029 (09-30) → **0.028 with a minimum of 5 fit facts** (10-07).
- LLM calls serialized service-wide, with the timeout starting only when a call runs. Duplicates re-checked just before submit. Filenames encode ids reversibly. Untrusted text escaped so it can't close prompt tags.
- Docs restructured: current behavior only in module READMEs, history only here.
- Fourth review: the visa rule reads a region on either side of "remote" (it missed "US - Remote"); the years rule only counts requirement-shaped lines ("12 years old" no longer counts); the degree rule doesn't read `location` (state codes); Turkey exempts the visa gap only as the sole location; the resume and cover letter drop exactly the facts matching doesn't count as fit — one shared definition (`is_fit_fact`), not two lists.
- Cover-letter design (implemented): code writes the opening sentence, the closing and the gaps paragraph — the last from `known-gaps.json`'s new `text` field, word for word (each gap's old `phrasing` split into `text` and `guidance`; drafted by Claude, approved by the user). The model writes only the "why", the experience, and at most one stack-specific gap sentence. The resume summary starts from the user's own `profile.summary`. New system-prompt rule: the posting's wording describes the job, never the candidate. Reason: in the 14B run every code-decided part came out right and every open slot drifted to genre filler or upgraded claims.

- Fifth review: "yrs" and years in the title count; office attendance stated anywhere in the posting raises the visa gap even when the location says "Remote"; "Istanbul or Remote" doesn't raise it; company-history years lines still raise the experience gap but are no longer quoted to the model as requirements; "high school diploma" and "MA or remote" no longer count as degrees. Template links get a scheme added when missing; form field ids compared as strings. The system prompt's "name the mismatch" rule is scoped to form answers; the gaps' `guidance` is no longer sent to the model (its example sentence could be copied). Noted with the review: keyword rules over free text won't converge by patching imagined phrasings — next evidence should come from real postings (the Greenhouse adapter) and the user's tests.

## Open questions

- **`review_gate/` design** — same model as the generator or separate (a second 14B call adds ~15 min per application)? The 14B live run (2026-10-07) showed filler, an upgraded claim ("Experienced backend engineer"), an unsupported "frontend" claim and an instruction copied into a letter; the code-written letter parts remove the filler slots and the copying route, and the resume summary now starts from the user's own — what's left in the model-written parts is the Controller's job.
- **Fixtures** still use the old shape with `requirements` lists; move them to the normalized shape, then recalibrate — ideally on real postings from the first adapter.
- **`projects-detail.json`** has no entry for Message Notification Router (user to write).
- **Domain** for the Cloudflare Tunnel isn't registered yet.
