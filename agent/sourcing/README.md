# sourcing

Pulls job listings from ATS-backed career pages (Greenhouse, Lever, Ashby, Workday, etc.) — v1 scope; LinkedIn/Glassdoor/JobLeads are excluded. Per-ATS adapters, shared with `form_automation/` where possible, since both need to know the same ATS's structure.

**Language: Python** — an internal module of the shared Python service (see `../README.md`). A run fetches once, at the start (see `../README.md`'s Run lifecycle).

## Company list

ATS public APIs are per-company — Greenhouse `boards/{board}/jobs`, Lever `postings/{board}`, Ashby `job-board/{board}`; Workday has no public API at all — so there's no feed of every job on an ATS. Each instance polls a list of companies on its ATS.

The list is hand-maintained, in its own JSON file in this folder, shared by all instances (each reads the entries for its own ATS):

```json
[{ "ats": "greenhouse", "board": "acme", "enabled": true, "note": "Go backend, remote EU" }]
```

- `board` — the board name from the ATS URL (e.g. `boards.greenhouse.io/acme`).
- `enabled: false` — pauses a company without deleting the entry.
- `note` — a reminder for the user; the pipeline ignores it.

There's no display-name field: the company's real name comes from the ATS response where the ATS provides one (confirmed per adapter; a board-level endpoint or the board name is the fallback). The pipeline never writes to this file. Automatic company discovery is a deferred later phase.

## Normalized posting

Every adapter produces the same shape:

| Field | Meaning |
|---|---|
| `id` | `{ats}:{board}:{ats_id}` — namespaced, so ids from different ATSs can't collide in `tracking/` |
| `ats`, `board` | which ATS, and the board slug from the company list |
| `company` | the display name (used in the cover letter's greeting) |
| `title`, `location` | as the ATS gives them (`location` is free text) |
| `employment_type` | full-time / part-time / contract, where the ATS provides it |
| `workplace_type` | `remote` / `hybrid` / `onsite` / `unknown` — real values from Lever/Ashby; `unknown` for Greenhouse, where the visa rule falls back to location text |
| `description` | plain text, HTML removed, **each HTML bullet on its own line** |
| `url`, `posted_at` | the posting page; first-published date where available, else updated date |
| `raw` | the untouched ATS response, kept for debugging rules against what the ATS actually sent |

**No `requirements` field.** Real ATSs don't deliver a requirements list (Greenhouse gives one HTML blob; Lever's section headings are free text), and guessing the requirements section by heading would fail silently. Downstream rules scan every line of `description` instead — e.g. `tailoring/gaps/`'s years-of-experience check. A "5 years" in a benefits bullet can then raise the experience gap unnecessarily, which is the safe direction.

**Consumers read named content fields, never the whole dict.** `matching/`'s query, `tailoring/`'s prompts, and the gap rules all go through `posting_content()` (`matching/document_builder/`): `title`, `company`, `location`, `workplace_type`, `employment_type`, `description`. `raw`, ids, urls and dates are stored but never sent into a search, a prompt, or a keyword rule.

## Filtering and errors

- **Stale filter:** postings older than 30 days (by `posted_at`) are dropped and reported as "skipped (stale)" in the end-of-run report. It's the only filter sourcing applies — role/location/tech fit is decided entirely by `matching/`.
- **Pacing:** a fixed ~1–2 s delay between company boards (20–50 requests per run).
- **Errors:** a board that fails to fetch (e.g. a 404 after a rename) is skipped and reported ("board fetch failed: acme (404)"); a single posting that can't be normalized (e.g. no title) is skipped and reported while the rest of its board proceeds. Nothing is auto-disabled — a repeating failure in the report is the user's cue to fix the entry.

Planning stage — no code yet. See `../CLAUDE.md` for the decision history.
