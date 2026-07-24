# matching

Fit-scoring: job posting vs. profile store (`source_of_truth`) — fully deterministic, no LLM in the go/no-go decision. `job_config` no longer participates in matching — see below.

**Language: Python** — an internal module of the shared Python service (see tech stack in `../README.md`).

**Single-call match (decided 2026-07-22, supersedes the two-stage gate this replaces):** one call, `hybrid_search(job_posting, source_of_truth)`, per posting — no chaining, no separate `job_config` stage.

`job_config` is reduced to **ATS only** (which career-page adapter/instance polls — e.g. Greenhouse vs. Lever). It's a sourcing/orchestrator routing concern, not a semantic filter, and it is never fed into `hybrid_search`.

The role/location/tech preferences that used to live in per-instance `job_config` (e.g. "backend developer, Germany" vs. "fullstack developer, Sweden") are **generalized** into one preference set shared across every instance (e.g. "open to backend or fullstack; Germany or Sweden; Python or Go"). Because they're no longer narrowed per instance run, they can live inside the single shared, read-only `source_of_truth` without breaking its "no per-instance customization" rule. Built as `source_of_truth/preferences.json` — **distinct from** the existing `job_preferences` field in `profile.json`, which answers deterministic screening questions (salary, visa, notice period); `preferences.json` points back to `profile.json` for those rather than duplicating them.

`hybrid_search` combines embedding search (sentence-transformers, CPU-only, cosine similarity) with keyword search (BM25) via RRF fusion — no structured field-diff and no LLM call.

**Soft/inferred requirements dropped (decided 2026-07-22, accepted tradeoff for now).** Things like "strong communication skills" that don't reduce to a checkable profile-store field or a clean embedding match aren't specially handled — a posting weak on these is rejected like any other non-match. The LLM does not arbitrate them. Revisit only if this turns out to cost real matches.

A posting that passes goes to `tailoring/` (the Application Generator) unconditionally — the LLM has no vote on fit, only on generating the application materials for jobs matching has already approved.

**Corpus/query direction and granularity (decided 2026-07-22):** `source_of_truth` is the indexed corpus, `job_posting` is the single query string. The corpus is built at **one `Document` per atomic fact** — every skill, every project (from `profile.json`'s `projects` plus the matching `projects-detail.json` entry), every `known-gaps.json` entry, every `general-stories.json` story, every `preferences.json` item gets its own `Document(id, content)`. `hybrid_search(job_posting, source_of_truth)`'s ranked output is therefore *your own facts*, ranked by relevance to that one posting — not the posting's requirements ranked against your profile. Implementation note: this granularity means some documents are very short (a single skill name like "Go") — fine for the semantic side, but BM25's document-length normalization has little to work with on a one-token document; observed in practice (see `fixtures/postings/` results) but hasn't caused a bad verdict yet.

**Pass/fail signal (decided 2026-07-22): use `rrf_search`'s fused `rrf_score` as-is** — both BM25 and semantic search stay in, combined via RRF, exactly as already built. Known, deliberately accepted imprecision: `rrf_score` is rank-based (`calc_rrf_score(rank) = 1 / (rank + 60)`), not a magnitude of similarity — the top-ranked fact in *any* corpus against *any* query scores in roughly the same range, whether it's a strong match or just the least-irrelevant thing available. Raw semantic cosine-similarity would be more precise but requires code changes to carry it through fusion (it's dropped in `hybrid_search.py`'s final result assembly); decided against that — use search as it already exists rather than build more to fix this.

**Threshold rule (decided 2026-07-22, empirically corrected same day):** a posting passes when **at least 4 distinct facts** from `source_of_truth` score **`rrf_score` ≥ 0.028** against that posting. The original guess (0.026) was tested end-to-end against the real 48-document corpus and failed to discriminate: a clearly-mismatched posting (sales manager) also cleared it (12 facts ≥ 0.026, versus 13 for a genuinely relevant backend posting — barely different). Scanning thresholds against both test postings, 0.028 is where they actually separate: the relevant posting clears 9 facts (≥4, passes), the mismatched one clears only 2 (<4, fails).

**Stress-tested 2026-07-24 against three more synthetic postings** (see `fixtures/postings/`, run via `scripts/calibrate_threshold.py`) — a fullstack posting (8 matching facts), a senior backend Go on-site/no-visa-sponsorship posting (9 facts), and a Data Engineer/MLOps posting (10 facts). All three passed comfortably, none close to the 4-fact cutoff — so 0.028 still holds for "clearly tech-adjacent vs. clearly irrelevant," but this batch didn't surface a genuine near-miss case either; that's still untested. Five synthetic postings total now, still not a real calibration set — revisit once real ATS data flows through.

**Notable finding from that stress test:** on the senior-backend-Go posting, `known_gap:visa_sponsorship_needed` and `job_preference:visa_sponsorship_needed` both scored as *matching* facts — not because the posting is a good visa fit (it explicitly offers no sponsorship), but because the posting's "cannot sponsor visas" text and the known-gap's "visa sponsorship needed" text share vocabulary. `rrf_score` (BM25 + semantic) has no concept of polarity, so a disqualifying fact can contribute to a passing score precisely because it's topically relevant, not despite it. Doesn't change the threshold decision (matching was always designed to be blind to deal-breakers — see Soft/inferred requirements above), but it's a sharper version of that blindness worth flagging for `review_gate/`: a "passed" match says nothing about whether the matched facts are actually favorable to the candidate.

**Sourcing's pre-filter (decided 2026-07-22): none needed.** Sourcing pulls everything from the configured ATS; role/location/tech fit is decided entirely by this matching step.

**Document construction (decided and built 2026-07-22):** see `document_builder/document_builder.py`. `build_source_of_truth_documents()` loads the five `source_of_truth` files and produces one `Document` per atomic fact (skills, projects — merged across `profile.json` and `projects-detail.json` by name — certifications, education, professional-experience note, each `job_preferences` field, each known-gap, each general-story, each preference item), with `content` as plain `json.dumps()` of the fact — no per-type templating. `job_posting_to_query()` is `json.dumps()` on the posting dict, since postings arrive from sourcing as JSON already. Intentionally excluded from the corpus: `profile["personal"]` (contact info, not a fit signal), `profile["eeo"]` (demographic/compliance answers — kept out so protected-characteristic text never influences a match score), and `profile["screening_answers"]`/`work_experience` (empty). Tested end-to-end against the real corpus (48 documents) with `hybrid_search` — see Threshold rule above.

Matching's design is now fully settled end-to-end; only recalibrating the threshold against real data remains.

## Types (decided 2026-07-22)

`job_posting` and `source_of_truth` entries reduce to the same simple shape for search purposes: `Document(id, content)` — a stable id plus flattened text. This lets `hybrid_search` treat both uniformly; it doesn't need to know which kind of thing it's comparing. `hybrid_search` returns `id` plus the matched `Document` itself (not bare ids), since the caller already has the `Document` in hand during search.

The richer structured record behind each `id` (the real ATS listing JSON, or the structured `source_of_truth` JSON) is *not* part of this module's concern — it's resolved separately, by that same `id`, downstream in `tailoring/`, where the LLM benefits from real structure the flattened `content` string discards.

## Implementation notes

Adapted from an older RAG project; the parts specific to that project (AWS S3/Redis-backed `storage/`, msgpack `type_converter/`, per-user `Storage`/`User` plumbing) have been stripped out — this module has no caching layer and no multi-tenant user concept. Current pieces:
- `inverted_index/` — BM25 keyword search over `Document`s, built fresh from the given document list each time. Complete.
- `semantic_index/` — sentence-transformers (`all-MiniLM-L6-v2` default) embeddings, chunked per-document (`helpers.semantic_chunk`), cosine similarity search, built fresh from the given document list each time. Complete.
- `helpers/` — shared, stateless building blocks: `cosine_similarity`, `calc_rrf_score` (the per-rank RRF formula), tokenization, chunking.
- `hybrid_search/` — where BM25's and the semantic index's two ranked lists get fused into one, using `calc_rrf_score` as the per-rank ingredient (`HybridSearch.rrf_search`). Complete.

`hybrid_search` itself is a corpus+query search primitive (index a list of `Document`s once via `HybridSearch(documents)`, then query it by string with `rrf_search`) — not structured field-diff, and not a pass/fail gate decision by itself. That framing and verdict logic is the orchestration layer built on top of it:
- `document_builder/` — turns the five `source_of_truth` files (plus a job posting) into `Document`s / a query string. Complete.
- `matcher/` — `evaluate_posting()` ties `document_builder` and `hybrid_search` together and applies the threshold rule (`is_match`) to produce the actual pass/fail verdict. Complete.

## Reproducibility

`requirements.txt` (full pinned freeze) and `pyproject.toml` (direct dependencies: `numpy`, `nltk`, `sentence-transformers`, `pydantic`) are both checked in — `venv/` itself stays gitignored. `torch` installs as a `+cpu` build; if a fresh install can't resolve it from PyPI alone, add `--extra-index-url https://download.pytorch.org/whl/cpu`.

## Calibration fixtures

`fixtures/postings/` holds synthetic job postings (JSON, same shape `document_builder.job_posting_to_query` expects) used to stress-test the threshold rule above — run them all via `python scripts/calibrate_threshold.py`, which prints each posting's pass/fail and matching-fact breakdown. Not a pytest suite (there isn't one yet for this module) — a manual calibration script.

See `../CLAUDE.md`.
