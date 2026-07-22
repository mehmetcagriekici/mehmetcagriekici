# matching

Fit-scoring: job posting vs. job config, and job posting vs. profile store — fully deterministic, no LLM in the go/no-go decision.

**Language: Python** — an internal module of the shared Python service (see tech stack in `../README.md`).

**Two-stage sequential gate (decided 2026-07-22), not a combined score or weighted average:**
1. **Stage 1 — `hybrid_search(job_config, job_posting)`.** `job_config` is a per-instance parameter (e.g. "backend developer, Germany" vs. "fullstack developer, Sweden") — short, and fixed for the life of that instance's run. Cheap filter, runs first.
2. **Stage 2 — `hybrid_search(source_of_truth, job_posting)`.** Only runs if Stage 1 passes. No caching layer — all embeddings (`job_config`, `job_posting`, and `source_of_truth`) are recomputed on every comparison.

`hybrid_search` combines embedding search (sentence-transformers, CPU-only, cosine similarity) with keyword search (BM25) via RRF fusion — no structured field-diff and no LLM call.

**Soft/inferred requirements dropped (decided 2026-07-22, accepted tradeoff for now).** Things like "strong communication skills" that don't reduce to a checkable profile-store field or a clean embedding match aren't specially handled — a posting weak on these is rejected at the gate like any other non-match. The LLM does not arbitrate them. Revisit only if this turns out to cost real matches.

A posting that clears both gates goes to `tailoring/` (the Application Generator) unconditionally — the LLM has no vote on fit, only on generating the application materials for jobs matching has already approved.

## Types (decided 2026-07-22)

`job_config`, `job_posting`, and `source_of_truth` entries all reduce to the same simple shape for search purposes: `Document(id, content)` — a stable id plus flattened text. This lets `hybrid_search` treat all three inputs uniformly; it doesn't need to know which kind of thing it's comparing. `hybrid_search` returns `id` plus the matched `Document` itself (not bare ids), since the caller already has the `Document` in hand during search.

The richer structured record behind each `id` (the real ATS listing JSON, or the structured `source_of_truth` JSON) is *not* part of this module's concern — it's resolved separately, by that same `id`, downstream in `tailoring/`, where the LLM benefits from real structure the flattened `content` string discards.

## Implementation notes

Adapted from an older RAG project; the parts specific to that project (AWS S3/Redis-backed `storage/`, msgpack `type_converter/`, per-user `Storage`/`User` plumbing) have been stripped out — this module has no caching layer and no multi-tenant user concept. Current pieces:
- `inverted_index/` — BM25 keyword search over `Document`s, built fresh from the given document list each time. Complete.
- `semantic_index/` — sentence-transformers (`all-MiniLM-L6-v2` default) embeddings, chunked per-document (`helpers.semantic_chunk`), cosine similarity search, built fresh from the given document list each time. Complete.
- `helpers/` — shared, stateless building blocks: `cosine_similarity`, `calc_rrf_score` (the per-rank RRF formula), tokenization, chunking.
- `hybrid_search/` — where BM25's and the semantic index's two ranked lists get fused into one, using `calc_rrf_score` as the per-rank ingredient (`HybridSearch.rrf_search`). Complete.

`hybrid_search` itself is complete: it's a corpus+query search primitive (index a list of `Document`s once via `HybridSearch(documents)`, then query it by string with `rrf_search`) — not structured field-diff, and not a pass/fail gate decision. Both of those are handled by a separate, not-yet-built orchestration layer above this module, which is responsible for framing `job_config`/`job_posting`/`source_of_truth` into the corpus+query shape and turning `rrf_search`'s ranked scores into a go/no-go verdict.

**Note:** the two-stage gate description above (and the field-diff line under Types) predate this scoping and are known to be stale — flagged 2026-07-22, not yet rewritten to match.

See `../CLAUDE.md`.
