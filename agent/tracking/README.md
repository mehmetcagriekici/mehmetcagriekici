# tracking

State store logging what was applied to, when, status, and the generated materials, to avoid duplicates and support follow-up.

**Language: Python** — an internal module of the shared Python service (see tech stack in `../README.md`), not routed through Go.

Must be a single store **shared across all concurrently-running per-ATS Go orchestrator instances** (see deployment model in `../README.md`), reading and writing to the same place rather than keeping local per-instance state — otherwise two instances (e.g. a Greenhouse instance and a Lever instance running at the same time) could double-apply to the same company/role. This is a stronger requirement than `source_of_truth/`, which stays read-only and shared but is never written to by the pipeline. **In practice the concurrency concern is smaller than it sounds (decided 2026-07-27):** since Python runs as one shared singleton service (not one per Go instance), every orchestrator's writes funnel through that single process, which serializes them naturally within a run — no multi-writer coordination needed at the storage layer.

**Storage format (decided 2026-07-27): plain JSON files, no database for now.** The user is comfortable with PostgreSQL and may stand up a local instance later, but that's an explicit future migration, not the v1 design.

**Granularity (decided 2026-07-27): one JSON file per application**, not one running log/array file for the whole store — the simpler starting option, and consistent with the per-application resume/cover-letter files `tailoring/` already writes to disk. Duplicate-detection queries across all of these per-application files rather than scanning a single one; not treated as a concern for now.

**Must store the full generated resume/cover-letter text (decided 2026-07-27), not just metadata.** Applications that pass `review_gate/` without routing to human review never have their content shown anywhere else — the review email is the only other place full text appears, and it only fires on review — so once `tailoring/`'s on-disk copy is deleted (see lifecycle below), `tracking/` is the sole surviving record of what was actually submitted.

**Duplicate key (decided 2026-07-27): job posting ID as the primary match, with a company+role fallback.** The job posting ID also names each per-application JSON file, so primary dedup is a plain file-existence check; the company+role fallback requires an actual scan across files and only kicks in when the ID lookup misses. ID-match is an explicit, acknowledged assumption — it only catches a repost if the ATS keeps the same ID on re-listing, which isn't guaranteed to hold uniformly across the v1 ATS set (Greenhouse, Lever, Ashby, Workday); the fallback exists to catch reposts that get a fresh ID instead.

**Fallback matching logic (decided 2026-07-27): simple normalization, not fuzzy matching or an LLM call** — lowercase + trim only, no stemming/suffix-stripping/token-level comparison. Deliberately minimal so it doesn't lose information (e.g. "Software Engineer" vs. "Software Engineer II" stay distinct rather than collapsing together), and keeps dedup fully deterministic — no LLM involved, consistent with `matching/`'s stance of not spending the CPU-only local model on decisions plain logic can resolve.

**Where the dedup check sits in the pipeline (decided 2026-07-27):** right after `sourcing/`, before `matching/` — a posting already applied to (by ID or the company+role fallback) is dropped before it burns a `hybrid_search` call, not filtered later.

**Generated-artifact lifecycle (decided 2026-07-27):** `tailoring/`'s per-application resume/cover-letter files land on disk, then get deleted once that application's process concludes — create, use (compile/attach/submit), delete — so working files don't accumulate indefinitely. This is only safe because `tracking/` persists the full text first (see above); without that write, deletion on the no-review-needed path would destroy the only record of what was submitted. "Concludes" means sent (via the Application API), rejected (by the Controller or the user, via review), or answered (a one-page overflow also emails the user directly — the file is kept and deletion waits until the user replies reject or approve-for-continuing, same as a review-routed rejection).

Planning stage — no code yet. See `../CLAUDE.md`.
