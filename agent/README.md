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
- **Application Controller** (`review_gate/`) — a second LLM checks the Generator's output for honesty (traceable to `source_of_truth/`) and relevance (addresses the posting); any failure on either routes to human review.
- **Application API** (`form_automation/`, bridged through the Go orchestrator) — submits, firing only once the Controller or the user approves.

A duplicate check against `tracking/` runs right after sourcing, before matching, so a posting already applied to — or permanently excluded after a failure or rejection — never burns a match/generate cycle.

**Goal:** not every possible job, but the best-matching ones — 10–50 applications a week.

## Deployment model

Runs on a local k8s distro (k3s/minikube-style) on the user's own machine. The Go orchestrator runs as multiple instances, one per ATS target (Greenhouse, Lever, etc.) — not per module, not per job board (LinkedIn/Glassdoor are out of scope). Each instance is configured with which ATS to target, a run-duration, and an application cap. A run fetches every listed company's board on that ATS once, drops stale (30+ days) and already-seen postings, matches and ranks the rest, then generates from the top until it has submitted the cap or runs out of time. Role/location/tech fit is not instance config — it's decided by `matching/` against a shared preference set in `source_of_truth/`. The user starts/restarts instances manually and reads the end-of-run report afterward; this isn't a hands-off system.

The Python and TypeScript services are shared singletons every Go instance calls into, not one trio per instance. `source_of_truth/` is a single shared, read-only resource; `tracking/` is shared and read-write, so concurrent instances can't double-apply to the same role; it holds full records for submitted applications and minimal permanent-exclusion records for postings that failed generation or were rejected.

**Review notifications:** email, via a dedicated Gmail account. A push email fires immediately when something routes to review, with approve/reject links; unanswered items default to reject once the instance's run ends (nothing is submitted, but no exclusion is recorded, so the posting can come back in a later run). The email shows the full generated package inline (not attachments, not summarized) plus why it was flagged. A separate end-of-run report summarizes each instance's whole run (submitted / matched-but-not-submitted / skipped / errors). The approve/reject link opens a one-tap confirm page (not a bare GET, to avoid email scanners auto-triggering it), reachable via a Cloudflare Tunnel — chosen over Tailscale so it opens in any browser with no app install. Needs a domain (not yet owned) and a token-protected link, since the endpoint is public.

## Python service setup

From `agent/` (the single import root — every module imports as `matching.x` / `tailoring.x`):

```sh
python -m venv venv && . venv/bin/activate
pip install -r requirements.txt           # pinned; declares PyTorch's CPU-only index itself
pip install -e . --no-deps                # makes matching/ and tailoring/ importable
playwright install --with-deps chromium   # tailoring/write renders PDFs via headless Chromium
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
