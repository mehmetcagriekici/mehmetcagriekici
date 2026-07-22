# matching

Fit-scoring: job posting vs. job config, and job posting vs. profile store — fully deterministic, no LLM in the go/no-go decision.

**Language: Python** — an internal module of the shared Python service (see tech stack in `../README.md`).

**Two-stage sequential gate (decided 2026-07-22), not a combined score or weighted average:**
1. **Stage 1 — `hybrid_search(job_config, job_posting)`.** `job_config` is a per-instance parameter (e.g. "backend developer, Germany" vs. "fullstack developer, Sweden") — short, and fixed for the life of that instance's run. Cheap filter, runs first.
2. **Stage 2 — `hybrid_search(source_of_truth, job_posting)`.** Only runs if Stage 1 passes. `source_of_truth` is larger and rarely changes, so its embeddings are precomputed/cached — the only embeddings that are cached. `job_config` and `job_posting` embeddings are recomputed on every comparison; not worth the complexity of caching something that cheap.

`hybrid_search` combines structured field-diff with embedding search (sentence-transformers, CPU-only, cosine similarity) and keyword search — no LLM call in either stage.

**Soft/inferred requirements dropped (decided 2026-07-22, accepted tradeoff for now).** Things like "strong communication skills" that don't reduce to a checkable profile-store field or a clean embedding match aren't specially handled — a posting weak on these is rejected at the gate like any other non-match. The LLM does not arbitrate them. Revisit only if this turns out to cost real matches.

A posting that clears both gates goes to `tailoring/` (the Application Generator) unconditionally — the LLM has no vote on fit, only on generating the application materials for jobs matching has already approved.

## Types (decided 2026-07-22)

`job_config`, `job_posting`, and `source_of_truth` entries all reduce to the same simple shape for search purposes: `Document(id, content)` — a stable id plus flattened text. This lets `hybrid_search` treat all three inputs uniformly; it doesn't need to know which kind of thing it's comparing. `hybrid_search` returns `id` plus the matched `Document` itself (not bare ids), since the caller already has the `Document` in hand during search.

The richer structured record behind each `id` (the real ATS listing JSON, or the structured `source_of_truth` JSON) is *not* part of this module's concern — it's resolved separately, by that same `id`, downstream in `tailoring/`, where the LLM benefits from real structure the flattened `content` string discards.

## Implementation notes

Adapted from an older RAG project. Current pieces:
- `inverted_index/` — BM25 keyword search over `Document`s. Complete.
- `semantic_index/` — sentence-transformers (`all-MiniLM-L6-v2` default) embeddings, chunked per-document (`helpers.semantic_chunk`), cosine similarity search, cached via `storage/`. Complete.
- `helpers/` — shared, stateless building blocks: `cosine_similarity`, `calc_rrf_score` (the per-rank RRF formula), tokenization, chunking.
- `hybrid_search/` — where BM25's and the semantic index's two ranked lists get fused into one, using `calc_rrf_score` as the per-rank ingredient. The actual merge (walk both ranked lists, sum RRF contributions per doc-id, re-sort) is the orchestration logic that belongs here, not in `helpers.py` — same separation as `InvertedIndex`/`SemanticIndex` each owning their own search logic while borrowing atomic helpers. Not yet written.

Storage/serialization (`storage/`, `type_converter/`) is also carried over from the old project (S3 + Redis, msgpack-based type round-tripping) and reused as-is.

See `../CLAUDE.md`.
