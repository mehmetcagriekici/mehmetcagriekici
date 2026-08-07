# tracking

State store logging what was applied to, when, status, and the generated materials — avoids duplicate applications and supports follow-up.

**Language: Python** — internal module of the shared Python service, not routed through Go.

**Storage: plain JSON files, no database.** One JSON file per application, not a single running log — the simpler starting option, consistent with `tailoring/`'s per-application resume/cover-letter files. A future migration to PostgreSQL is possible but not in scope for now.

**Concurrency:** must behave as a single store across all concurrently-running Go orchestrator instances (e.g. Greenhouse and Lever running at once) so two instances can't double-apply to the same role. In practice this is simpler than a multi-writer design sounds — Python runs as one shared singleton service, so every instance's writes funnel through that one process, which serializes them naturally.

**Must store the full generated resume/cover-letter text, not just metadata.** Applications that pass `review_gate/` without routing to review never have their content shown anywhere else — the review email is the only other place full text appears, and only on review — so once `tailoring/`'s on-disk copy is deleted, `tracking/` is the sole surviving record of what was submitted.

**Duplicate detection:** job posting ID as the primary match (also the filename of each per-application JSON file, so this is a plain file-existence check), with a company+role fallback that scans across files. ID-match is an explicit, acknowledged assumption — it only catches a repost if the ATS keeps the same ID on re-listing, which isn't guaranteed across the v1 ATS set (Greenhouse, Lever, Ashby, Workday); the fallback exists for reposts that get a fresh ID. Fallback matching is simple normalization (lowercase + trim), not fuzzy or LLM-based — deliberately minimal so distinct roles ("Software Engineer" vs. "Software Engineer II") don't collapse together, and dedup stays fully deterministic.

**Where the dedup check sits:** right after `sourcing/`, before `matching/` — an already-applied-to posting is dropped before it burns a `hybrid_search` call.

**Generated-artifact lifecycle:** `tailoring/`'s per-application resume/cover-letter files land on disk, then get deleted once that application's process concludes — create, use (compile/attach/submit), delete, so working files don't accumulate. Only safe because `tracking/` persists the full text first. "Concludes" means sent (via the Application API), rejected (by the Controller or the user), or answered (a one-page overflow also emails the user directly — the file is kept until the user replies).

Planning stage — no code yet. See `../CLAUDE.md`.
