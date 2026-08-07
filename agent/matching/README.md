# matching

Fit-scoring: job posting vs. `source_of_truth` — fully deterministic, no LLM in the pass/fail decision.

**Language: Python** — internal module of the shared Python service (see `../README.md`).

## How it works

One call, `hybrid_search(job_posting, source_of_truth)`, per posting. No chained stages, no per-instance `job_config` filter — `job_config` is reduced to ATS selection only (a sourcing/routing concern), and role/location/tech preferences live in the shared `source_of_truth/preferences.json` instead.

`hybrid_search` combines embedding search (sentence-transformers, CPU-only, cosine similarity) with keyword search (BM25) via RRF fusion — no structured field-diff.

**Corpus/query direction:** `source_of_truth` is the indexed corpus, one `Document` per atomic fact (every skill, project, known-gap, story, and preference item gets its own `Document(id, content)`, built via `json.dumps` of that fact). `job_posting` is the query string (same `json.dumps` treatment). So results come back as *your own facts*, ranked by relevance to a given posting — not the posting's requirements ranked against your profile.

**Pass/fail signal:** `rrf_search`'s fused `rrf_score`, as returned. Known imprecision, accepted: it's rank-based (`1 / (rank + 60)`), not similarity-magnitude, so a corpus's top-ranked fact scores in roughly the same range whether it's a strong match or just the least-bad option available.

**Threshold:** a posting passes when at least 4 distinct facts score `rrf_score` ≥ 0.028 against it. This value was empirically tuned — an initial guess didn't separate a mismatched test posting from a genuinely relevant one; 0.028 does. Stress-tested against several synthetic postings (see `fixtures/postings/`) — all clear comfortably, so the cutoff is validated for "clearly relevant vs. clearly irrelevant" but not yet against a real near-miss case or real ATS data.

**Known blind spot:** `rrf_score` has no concept of polarity. On one test posting, `known_gap:visa_sponsorship_needed` scored as a *matching* fact against a posting that explicitly offers no sponsorship — the two texts share vocabulary even though the posting is a disqualifying mismatch. Matching was always designed to be blind to deal-breakers like this (see Soft/inferred requirements below); worth flagging for `review_gate/`, since a "passed" match says nothing about whether the matched facts are actually favorable.

**Soft/inferred requirements** (e.g. "strong communication skills") are dropped rather than arbitrated — not resolved by an LLM or anything else. Accepted tradeoff, revisit only if it costs real matches.

Sourcing applies no pre-filter — role/location/tech fit is decided entirely here. A posting that passes goes to `tailoring/` unconditionally; the LLM has no vote on fit, only on generating materials for postings matching has already approved.

## Document construction

`document_builder/document_builder.py`'s `build_source_of_truth_documents()` loads the five `source_of_truth` files and produces one `Document` per atomic fact (skills, projects — merged across `profile.json` and `projects-detail.json` by name — certifications, education, professional-experience note, each `job_preferences` field, each known-gap, each story, each preference item). `job_posting_to_query()` is `json.dumps()` on the posting dict.

Excluded from the corpus: `profile["personal"]` (not a fit signal), `profile["eeo"]` (kept out so protected-characteristic text never influences a match score), and the empty `screening_answers`/`work_experience` fields.

## Types

`job_posting` and `source_of_truth` entries both reduce to `Document(id, content)` — a stable id plus flattened text — so `hybrid_search` treats both uniformly. It returns `id` plus the matched `Document` itself, not a bare id.

`tailoring/`'s Generator consumes the top-N `(id, content)` pairs directly, as returned — no resolve-by-id step back to a richer structured record. This works because each `Document`'s `content` is already the full serialized atomic fact; there's no structure left to resolve. See `../tailoring/README.md`'s Generator input note.

## Implementation

Adapted from an older RAG project, stripped of parts specific to that project (S3/Redis storage, msgpack conversion, multi-tenant plumbing) — this module has no caching layer and no user concept.

- `inverted_index/` — BM25 keyword search over `Document`s, built fresh per query.
- `semantic_index/` — sentence-transformers (`all-MiniLM-L6-v2`) embeddings, chunked per document, cosine similarity.
- `helpers/` — shared stateless pieces: `cosine_similarity`, `calc_rrf_score`, tokenization, chunking.
- `hybrid_search/` — fuses the BM25 and semantic ranked lists via `calc_rrf_score` (`HybridSearch.rrf_search`). A corpus+query search primitive, not a pass/fail gate by itself.
- `document_builder/` — turns the `source_of_truth` files (plus a posting) into `Document`s / a query string.
- `matcher/` — `evaluate_posting()` ties `document_builder` and `hybrid_search` together and applies the threshold rule (`is_match`) to produce the pass/fail verdict.

## Reproducibility

`../requirements.txt` (pinned freeze) and `../pyproject.toml` (direct deps, grouped by module — matching's are `numpy`, `nltk`, `sentence-transformers`, `pydantic`) live at `agent/`, shared across the whole Python service. The venv lives at `../venv`, gitignored. `torch` installs as a `+cpu` build; if PyPI alone can't resolve it, add `--extra-index-url https://download.pytorch.org/whl/cpu`.

## Calibration fixtures

`fixtures/postings/` holds synthetic job postings used to stress-test the threshold — run via `python scripts/calibrate_threshold.py`, which prints each posting's pass/fail and matching-fact breakdown. Not a pytest suite — a manual calibration script.

Status: design and code complete, pending recalibration against real ATS data. See `../CLAUDE.md`.
