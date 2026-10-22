# sourcing

Pulls job listings from ATS-backed career pages (Greenhouse, Lever, Ashby, Workday, etc.) — v1 scope; LinkedIn/Glassdoor/JobLeads are excluded. Per-ATS adapters. `form_automation/` (TypeScript) needs to know the same ATS's structure, but can't share this Python code — only what's learned about each ATS.

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

There's no display-name field: the company's real name comes from the ATS response (Greenhouse: each job's `company_name`). A posting without one is skipped and reported — the board slug is never used as a name. The pipeline never writes to this file. Automatic company discovery is a deferred later phase.

## Structure

- **`fetch/`** — one adapter per ATS, in its own subfolder (`fetch/greenhouse/`); all of that ATS's logic lives there and nowhere else (its response type lives with the other types, below). Each adapter is two functions: a thin **fetch** (the HTTP call and JSON parsing; a failed request or a broken response — invalid JSON, no job list — is a `FETCH_FAILED` skip for the board) and a pure **reshape** (the ATS's job list + board slug → `list[Posting]`, nothing else; fetch unwraps the response, so reshape never sees ATS wrappers like Greenhouse's `meta`). Reshape loops over the jobs and never skips or raises on bad input: a missing key, a `None`, or a value it can't parse becomes `None` (read with `.get()`, transformed only when present, a third-party parse error caught by name), and normalize skips and reports the posting. Reshape does no I/O, so tests feed it a saved response (`tests/fixtures/greenhouse/gitlab_jobs.json`).
- **`normalize/`** — shared cleanup, no per-ATS code: HTML → text, the key/required-field check, the stale filter.
- **`custom_types/posting.py`** — every type, shared or per-ATS (see Types).
- **Reporting** — fetch and normalize each return their results plus a list of `Skip`s; the runner joins them into the end-of-run report. No shared collector object.

What the adapter hands to normalize is already in posting shape, except that `description` is still HTML (ATS-specific escaping already undone) and `posted_at` is a timezone-aware `datetime` (each ATS has its own date format, so parsing it is the adapter's job).

| Step | Takes | Returns |
|---|---|---|
| fetch | board slug | `list[GreenhousePosting]` (per ATS), or a `Skip` (`FETCH_FAILED`) |
| reshape | that list + board slug | `list[Posting]` |
| normalize | `list[Posting]` | `list[Posting]` (cleaned) + `list[Skip]` |

## Types

All types live in `sourcing/custom_types/posting.py`: the shared `Posting`, `Skip` and `SkipReason`, and one response type per ATS.

**`GreenhousePosting`** — a `TypedDict`: one Greenhouse job as fetch hands it to reshape. Fetch builds it from each job in the response, flattening `location.name` into `location_name` and keeping the untouched job object as `raw`. It describes what Greenhouse usually sends, not a guarantee — parsed JSON isn't checked against it, and `company_name`/`first_published` aren't in the docs' list-endpoint example — so reshape reads every key with `.get()`.

| Field | Type | → `Posting` |
|---|---|---|
| `id` | from Greenhouse's job id | `id` = `greenhouse:{board}:{id}` |
| `company_name` | `str` | `company` |
| `title` | `str` | `title` |
| `location_name` | `str` (from `location.name`) | `location` |
| `content` | `str`, entity-escaped HTML | `description`, unescaped |
| `absolute_url` | `str` | `url` |
| `first_published` | `str`, ISO 8601 with offset | `posted_at`, via `fromisoformat` |
| `internal_job_id` | `int` | `requisition_key`, as a string |
| `raw` | `dict[str, Any]` | `raw` |

**`Posting`** — a `TypedDict`: a plain dict at runtime, so consumers' `.get()` and `posting_content()` are unchanged. One type for both the adapter's output and normalize's. Every key is always present, one key per row below — no two fields share a key.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `id` | `str \| None` | yes | `{ats}:{board}:{ats_id}`, e.g. `greenhouse:gitlab:8860302002` — namespaced, so ids from different ATSs can't collide in `tracking/` |
| `ats` | `str \| None` | yes | which ATS the posting came from, e.g. `greenhouse` |
| `board` | `str \| None` | yes | the board slug from the company list, e.g. `gitlab` |
| `company` | `str \| None` | yes | the company's display name from the ATS, e.g. `GitLab` (used in the cover letter's greeting) |
| `title` | `str \| None` | yes | the job title as the ATS gives it, e.g. `Senior Backend Engineer (Go)` |
| `location` | `str \| None` | yes | free text as the ATS gives it, e.g. `Remote, Canada; Remote, United Kingdom` — the visa rule reads it |
| `description` | `str \| None` | yes | the posting's body: HTML from the adapter, then plain text after normalize, **each HTML bullet on its own line** |
| `url` | `str \| None` | yes | the posting page |
| `posted_at` | `datetime \| None` | yes | first-published date, timezone-aware. Greenhouse: `first_published`, never `updated_at` — companies bulk-edit old postings, which makes them look fresh. Whether another ATS may use an updated date is decided with its adapter |
| `raw` | `dict[str, Any]` | yes | the untouched ATS job object, kept for debugging rules against what the ATS actually sent; never read by the pipeline |
| `employment_type` | `str \| None` | no | full-time / part-time / contract, where the ATS provides it (`None` for Greenhouse) |
| `requisition_key` | `str \| None` | no | the ATS's id for the underlying job when one job is published as several postings (Greenhouse: `internal_job_id`, stored as a string); `tracking/` dedups on company + `requisition_key`. `None` where the ATS has none |
| `workplace_type` | `Literal["remote", "hybrid", "onsite", "unknown"]` | no — never `None` | real values from Lever/Ashby; `unknown` for Greenhouse, where the visa rule falls back to `location` |

Required `None` is what normalize skips (`MISSING_FIELD`).

**`Skip`** — a `TypedDict`, like `Posting`: a note for the end-of-run report about something dropped. Not a kept posting: the posting itself is gone.

| Field | Type | Example |
|---|---|---|
| `what` | `str` — the board slug or the posting id | `"acme"`, `"greenhouse:gitlab:8860302002"` |
| `reason` | `SkipReason` | `SkipReason.STALE` |
| `detail` | `str` — free text, shown in the report | `"404"`, `"company"`, `"41 days"` |

No `step` field: each reason comes from exactly one step, so it would only repeat the reason.

**`SkipReason`** — an Enum: the fixed list of values `Skip.reason` can hold. The runner groups the report by it — exact, unlike matching words in free text (same pattern as `tailoring/write/`'s `WriteError`).

| Value | Produced by | Means |
|---|---|---|
| `FETCH_FAILED` | fetch | request failed or response broken (invalid JSON, no job list) |
| `MISSING_KEY` | normalize | a posting lacks a key — an adapter bug |
| `MISSING_FIELD` | normalize | a required field is `None` |
| `STALE` | normalize | `posted_at` older than 30 days |

## Normalized posting

Every adapter produces the `Posting` shape — fields, types and meanings are in **Types** above.

**Every posting has every key.** `None` means the ATS didn't provide the value; a missing key is an adapter bug. Normalize checks both:

- **Required** — `id`, `ats`, `board`, `company`, `title`, `location`, `description`, `url`, `posted_at`, `raw`. A posting with any of them `None` is skipped and reported.
- **Optional** — `employment_type` (`None` where the ATS doesn't provide it, e.g. Greenhouse), `requisition_key` (`None` where the ATS has none) and `workplace_type` (`unknown` where the ATS doesn't provide it). An optional field being `None` never skips a posting.

No placeholder values: a value that's missing or failed to parse is `None` (or the posting is skipped), never a stand-in that looks like real data.

**No `requirements` field.** Real ATSs don't deliver a requirements list (Greenhouse gives one HTML blob; Lever's section headings are free text), and guessing the requirements section by heading would fail silently. Downstream rules scan every line of `description` instead — e.g. `tailoring/gaps/`'s years-of-experience check. A "5 years" in a benefits bullet can then raise the experience gap unnecessarily, which is the safe direction.

**Consumers read named content fields, never the whole dict.** `matching/`'s query, `tailoring/`'s prompts, and the gap rules all go through `posting_content()` (`matching/document_builder/`): `title`, `company`, `location`, `workplace_type`, `employment_type`, `description`. `raw`, ids, urls and dates are stored but never sent into a search, a prompt, or a keyword rule.

## Greenhouse

`boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true` — `content=true` is what includes the description. Checked against real responses (coinbase, gitlab).

| Posting field | Greenhouse |
|---|---|
| `id` | `greenhouse:{board}:{id}` |
| `company` | `company_name` |
| `title` | `title` |
| `location` | `location.name` (e.g. "Remote, Canada; Remote, United Kingdom") |
| `description` | `content`, HTML-unescaped by the adapter (it arrives entity-escaped: `&lt;p&gt;`) |
| `url` | `absolute_url` |
| `posted_at` | `first_published` |
| `requisition_key` | `internal_job_id` |
| `employment_type` | `None` — not provided (`metadata` holds company-specific custom fields) |
| `workplace_type` | `unknown` — not provided |
| `raw` | the job object |

**One job, several posts.** Greenhouse can publish one job as several posts — typically one per location — each with its own `id` and the same `internal_job_id` (gitlab: 3 such pairs in 232 posts). Each post stays its own posting and matching ranks them; once one is applied to, `tracking/` treats the rest as duplicates (company + `requisition_key`). Tailoring uses the location of the post actually applied to.

`absolute_url` can point to the company's own careers site rather than a Greenhouse page — not relevant until `form_automation/`.

## Filtering and errors

- **Stale filter:** postings older than 30 days (by `posted_at`) are dropped and reported as "skipped (stale)" in the end-of-run report. It's the only filter sourcing applies — role/location/tech fit is decided entirely by `matching/`.
- **Pacing:** a fixed ~1–2 s delay between company boards (20–50 requests per run).
- **Errors:** a board that fails to fetch (e.g. a 404 after a rename) is skipped and reported ("board fetch failed: acme (404)"); a single posting that can't be normalized (e.g. a required field is `None`) is skipped and reported while the rest of its board proceeds. Nothing is auto-disabled — a repeating failure in the report is the user's cue to fix the entry.

In progress — no code yet; the Greenhouse adapter comes first. Starter company list: gitlab, adyen, doctolib, celonis, n26, sumup, hellofresh, contentful, monzo, getyourguide, trivago. See `../CLAUDE.md` for the decision history.
