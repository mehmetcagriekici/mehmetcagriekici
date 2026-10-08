# agent

Job-application automation project — an AI agent that applies to jobs on the user's behalf. Design-first: implementation code is written only where explicitly requested (see [`CLAUDE.md`](CLAUDE.md)).

Kept separate from the manual cover-letter/resume workflow at the repo root (`../cover.tex`, `../resume.pdf`, `../applications.md`), which this project doesn't touch.

## Modules

| Folder | Status | Purpose |
|---|---|---|
| [`source_of_truth/`](source_of_truth/README.md) | Built, in use | Profile store the rest of the pipeline reads from |
| [`sourcing/`](sourcing/README.md) | Planned | Pulls job listings from ATS career pages |
| [`matching/`](matching/README.md) | Built, in use | Fit-scoring against the profile store |
| [`tailoring/`](tailoring/README.md) | In progress | Generates per-job resume/cover letter and screening-question answers |
| [`form_automation/`](form_automation/README.md) | Planned | Per-ATS form-filling and submission |
| [`tracking/`](tracking/README.md) | Planned | State store for what's been applied to |
| [`review_gate/`](review_gate/README.md) | Planned | Checks generated materials for honesty/relevance before submission |

`tailoring/` splits further into `llm/`, `prompts/`, `write/`, and `gaps/` submodules.

## Pipeline

`Data -> Hybrid Search -> Application Generator -> Application Controller -> Application API`

- **Hybrid Search** (`matching/`) — deterministic fit-scoring, no LLM.
- **Application Generator** (`tailoring/`) — takes matched postings in rank order (most facts above the matching threshold first) until the run's cap is reached; generates the resume, cover letter, and free-text answers.
- **Application Controller** (`review_gate/`) — a code check (no invented names) and then a second LLM check the Generator's output for honesty (traceable to `source_of_truth/`) and relevance (addresses the posting); any failure on either routes to human review.
- **Application API** (`form_automation/`, bridged through the Go orchestrator) — submits, firing only once the Controller or the user approves.

A duplicate check against `tracking/` runs right after sourcing, before matching, so a posting already applied to — or permanently excluded after a failure or rejection — never burns a match/generate cycle.

## Deployment model

Runs on a local k8s distro (k3s/minikube-style) on the user's own machine. The Go orchestrator runs as multiple instances, one per ATS target (Greenhouse, Lever, etc.) — not per module, not per job board (LinkedIn/Glassdoor are out of scope). The Python and TypeScript services are shared singletons every Go instance calls into, not one trio per instance. `source_of_truth/` is a single shared, read-only resource; `tracking/` is shared and read-write. The user starts/restarts instances manually and reads the end-of-run report afterward — this isn't a hands-off system.

## Run lifecycle

**Goal:** not every possible job, but the best-matching ones — 10–50 applications a week.

1. **Start.** A Go instance passes `{ats, run_duration, application_cap}` to Python. Python owns the loop from here; Go's part is bridging each generated application to the TypeScript form service and reporting each submission's result back, so Python can count submissions.
2. **Fetch once.** Every enabled company board on that ATS, fetched once — no re-fetching mid-run; at ~1 hour of generation per application, discovery isn't the bottleneck (`sourcing/`).
3. **Filter.** Drop postings older than 30 days, and postings `tracking/` already holds — applied to, or permanently excluded.
4. **Match and rank.** `matching/` decides pass/fail; passing postings are ranked by `matching_fact_count`, ties broken by newest `posted_at` first, then by id.
5. **Generate, top down.** `tailoring/` generates for the highest-ranked posting, `review_gate/` checks it, then it's submitted or routed to the user's review. Repeat until the **submitted-application cap** (reviews don't count until approved and submitted) or the run-duration is reached.
6. **What happens to each posting:**
   - **Submitted** → a full application record in `tracking/` (with the generated text).
   - **Content failure** (bad model output for this posting, a prompt or output too long) or **the user's explicit reject** → a permanent exclusion record in `tracking/`; it never comes back. A failed Controller check never excludes by itself — it routes to the user's review.
   - **Infrastructure failure** (Ollama down or timing out, Chromium crashing) → no record, and **the run stops**; the posting comes back next run. See `tailoring/write/README.md` for which error is which.
   - **Review unanswered at run end** (Controller review or one-page overflow) → not submitted, no record; it comes back next run with a fresh email.
   - **Matched but not reached** → no record; re-ranked next run.

   Just before submitting, `tracking/` is checked again for the same company + role — generation takes about an hour, and another instance may have applied in the meantime.
7. **End-of-run report**, for the user to read at their own pace: submitted, matched-but-not-submitted, skipped and errors — specifically stale postings, boards that failed to fetch (with the error), postings that couldn't be normalized, exclusions written (with reason), and reviews that timed out.

**Review notifications:** email, via a dedicated Gmail account, fired immediately when something routes to review — the full generated package inline plus why it was flagged, with approve/reject links behind a one-tap confirm page reachable via a Cloudflare Tunnel. Details in `review_gate/README.md`.

## Python service setup

From `agent/` (the single import root — every module imports as `matching.x` / `tailoring.x`):

```sh
python -m venv venv && . venv/bin/activate
pip install -r requirements.txt           # pinned; declares PyTorch's CPU-only index itself
pip install -e . --no-deps                # makes matching/ and tailoring/ importable
playwright install --with-deps chromium   # tailoring/write renders PDFs via headless Chromium
python -m nltk.downloader punkt_tab stopwords  # matching's tokenizer data (else downloaded on first import -- fails offline)
sudo apt install fonts-liberation         # the templates pin Liberation Sans (see below)
ollama pull qwen2.5:14b                   # tailoring/llm's default model (~9 GB)
```

**Ollama server setting:** serve one request at a time — `OLLAMA_NUM_PARALLEL=1` in the Ollama service's environment (e.g. `sudo systemctl edit ollama` → `[Service]` / `Environment="OLLAMA_NUM_PARALLEL=1"`, then restart). `tailoring/llm`'s token cap and timeout reasoning assume a single slot, and each extra slot would need its own 16k-token context in RAM. Observed as the effective behavior on this machine already; this pins it.

The same steps belong in the container image once one exists. `fonts-liberation` matters beyond looks: the one-page check counts the rendered PDF's pages, so a machine falling back to a different font could flip identical content between one and two pages.

Lint/format with `uvx ruff check .` and `uvx ruff format .` (config in `pyproject.toml`; not a project dependency).

## Tech stack

| Service | Language | Owns |
|---|---|---|
| Orchestrator | Go | Bridges Python's generated output to the TypeScript form-filling service; creates/finalizes the application. Thin — no pipeline sequencing, tracking writes, or review-gate emails. |
| Content/logic service | Python | `sourcing/`, `matching/`, `tailoring/`, `tracking/`, `review_gate/` — internal modules calling each other directly. Hosts local LLM inference via Ollama, CPU-only — default model `qwen2.5:14b`, slow (~1 hour of generation per application) by accepted design. |
| Form service | TypeScript | `form_automation/` — browser automation for JS-heavy application forms. |

The LLM is constrained to organizing/formatting content and answering form fields strictly from `source_of_truth/` — never inventing facts, same honesty principle as the root `CLAUDE.md`.

**Prompt injection defense:** job posting text is attacker-controlled and reaches two LLM calls — the Generator and the Controller's relevance check. Both wrap it like a system-prompt boundary, explicitly labeled as untrusted data rather than instructions — structural, not a separate detection step. `matching/`'s search is deterministic and needs no such defense.

**Screening questions:** deterministic ones (work authorization, visa, salary, notice period, language, EEO) are structured fields in `source_of_truth/`, answered without the LLM. The LLM only handles generative work — resume tailoring, cover letters, free-text/behavioral answers — always drawn from `source_of_truth/`, never invented. No answer caching — every answer regenerates fresh.
