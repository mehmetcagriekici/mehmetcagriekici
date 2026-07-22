# matching

Fit-scoring: job posting vs. job config, and job posting vs. profile store — fully deterministic, no LLM in the go/no-go decision.

**Language: Python** — an internal module of the shared Python service (see tech stack in `../README.md`).

**Two-stage sequential gate (decided 2026-07-22), not a combined score or weighted average:**
1. **Stage 1 — `hybrid_search(job_config, job_posting)`.** `job_config` is a per-instance parameter (e.g. "backend developer, Germany" vs. "fullstack developer, Sweden") — short, and fixed for the life of that instance's run. Cheap filter, runs first.
2. **Stage 2 — `hybrid_search(source_of_truth, job_posting)`.** Only runs if Stage 1 passes. `source_of_truth` is larger and rarely changes, so its embeddings are precomputed/cached — the only embeddings that are cached. `job_config` and `job_posting` embeddings are recomputed on every comparison; not worth the complexity of caching something that cheap.

`hybrid_search` combines structured field-diff with embedding search (sentence-transformers, CPU-only, cosine similarity) and keyword search — no LLM call in either stage.

**Soft/inferred requirements dropped (decided 2026-07-22, accepted tradeoff for now).** Things like "strong communication skills" that don't reduce to a checkable profile-store field or a clean embedding match aren't specially handled — a posting weak on these is rejected at the gate like any other non-match. The LLM does not arbitrate them. Revisit only if this turns out to cost real matches.

A posting that clears both gates goes to `tailoring/` unconditionally — the LLM has no vote on fit, only on generating the application materials for jobs matching has already approved.

Planning stage — no code yet. See `../CLAUDE.md`.
