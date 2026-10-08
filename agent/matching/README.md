# matching

Fit-scoring: job posting vs. `source_of_truth` — fully deterministic, no LLM in the pass/fail decision.

**Language: Python** — internal module of the shared Python service (see `../README.md`).

## How it works

One call, `hybrid_search(job_posting, source_of_truth)`, per posting. No chained stages, no per-instance `job_config` filter — `job_config` is reduced to ATS selection only (a sourcing/routing concern), and role/location/tech preferences live in the shared `source_of_truth/preferences.json` instead.

`hybrid_search` combines embedding search (sentence-transformers, CPU-only, cosine similarity) with keyword search (BM25) via RRF fusion — no structured field-diff.

**Corpus/query direction:** `source_of_truth` is the indexed corpus, one `Document` per atomic fact (every skill, project, known-gap, story, and preference item gets its own `Document(id, content)`, built via `json.dumps` of that fact). `job_posting` is the query string (same `json.dumps` treatment). So results come back as *your own facts*, ranked by relevance to a given posting — not the posting's requirements ranked against your profile.

**Pass/fail signal:** `rrf_search`'s fused `rrf_score`, as returned. Known imprecision, accepted: it's rank-based (`1 / (rank + 60)`), not similarity-magnitude, so a corpus's top-ranked fact scores in roughly the same range whether it's a strong match or just the least-bad option available.

**Threshold:** a posting passes when at least **5** distinct **fit** facts score `rrf_score` ≥ **0.028** against it. Not counted as fit (they stay in the results and reach the generator): gap and screening-answer facts (`known_gap:*`, `job_preference:*`, `professional_experience`), `education`, and the logistics preferences `work_mode` / `regions_open_to` / `hard_deal_breakers` — all of which match nearly any posting (see `NON_FIT_FACT_PREFIXES` / `NON_FIT_FACT_IDS`); the `roles` and `tech_stack_priority` preferences do count. Every fact is ranked (no result cap — a cap would start dropping facts once the corpus outgrew it, shifting every score) and ties are broken by doc id, so rankings are identical across runs. Recalibrated 2026-10-07; re-checked 2026-10-08 after the `source_of_truth` accuracy fixes: on the fixtures the relevant postings keep 9/10/7 fit facts and the mismatch 3 at 0.028, so a minimum of 5 leaves a 2-fact margin on both sides (it was 3 before the fixes). Still four synthetic fixtures — re-run `scripts/calibrate_threshold.py` after any `source_of_truth` change, and recalibrate against real ATS data once sourcing exists.

**Known blind spot:** `rrf_score` has no concept of polarity. On one test posting, `known_gap:visa_sponsorship_needed` scored as a *matching* fact against a posting that explicitly offers no sponsorship — the two texts share vocabulary even though the posting is a disqualifying mismatch. Matching was always designed to be blind to deal-breakers like this (see Soft/inferred requirements below); worth flagging for `review_gate/`, since a "passed" match says nothing about whether the matched facts are actually favorable.

**Soft/inferred requirements** (e.g. "strong communication skills") are dropped rather than arbitrated — not resolved by an LLM or anything else. Accepted tradeoff, revisit only if it costs real matches.

Sourcing applies no pre-filter — role/location/tech fit is decided entirely here. Postings that pass are **ranked by `matching_fact_count`** (the number of fit facts at or above the threshold, returned by `evaluate_posting`; ties broken by newest `posted_at` first, then by posting id). Expect many ties: a fact only clears 0.028 by ranking well in *both* lists (one list alone gives at most 1/61 ≈ 0.016), so when the two lists broadly agree at most ~11 facts can clear it, and passing postings fall in a narrow range of counts. They're handed to `tailoring/` highest first, until the run's submitted-application cap is reached (decided 2026-10-07 — the goal is the best-matching 10–50 applications a week, not every match). The LLM has no vote on fit, only on generating materials for postings matching has already approved.

## Document construction

`document_builder/document_builder.py`'s `build_source_of_truth_documents()` loads the five `source_of_truth` files and produces one `Document` per atomic fact (skills, projects — merged across `profile.json` and `projects-detail.json` by name — certifications, education, professional-experience note, each `job_preferences` field, each known-gap, each story, each preference item). `job_posting_to_query()` is `json.dumps()` of `posting_content(job_posting)` — the posting's content fields only (`title`, `company`, `location`, `workplace_type`, `employment_type`, `description`, plus the fixtures' `requirements`/`nice_to_have`), never ids, urls, salary, or the stored `raw` ATS response. `tailoring/` reads postings through the same function. Both use `ensure_ascii=False`, so non-ASCII text ("München", "Açıköğretim") stays intact instead of becoming `\u` escapes that split words. A project in `profile.json` with no matching `projects-detail.json` entry (by exact name) is still indexed, without the incident-level detail, and logs a warning.

`profile["summary"]` is indexed as one fact (`summary`) — the candidate's own fit statement. Excluded from the corpus: `profile["personal"]` (not a fit signal), `profile["eeo"]` (kept out so protected-characteristic text never influences a match score), and the empty `screening_answers`/`work_experience` fields.

## Types

`source_of_truth` facts reduce to `Document(id, content)` — a stable id plus flattened text; the posting becomes a query string. `rrf_search` returns one dict per fact, best first: `{doc_id, content, bm25_rank, semantic_rank, rrf_score}` (a rank of 0 means that list didn't return the fact). `evaluate_posting` adds the verdict on top: `{passed, matching_fact_count, matching_facts, matching_fact_ids, results}`.

`tailoring/`'s Generator consumes `evaluate_posting`'s `matching_facts` (every fact at or above the threshold, as those result dicts — `tailoring/prompts` reads their `doc_id` and `content`) directly, as returned — no resolve-by-id step back to a richer structured record. This works because each `Document`'s `content` is already the full serialized atomic fact; there's no structure left to resolve. See `../tailoring/README.md`'s Generator input note.

## Implementation

Adapted from an older RAG project, stripped of parts specific to that project (S3/Redis storage, msgpack conversion, multi-tenant plumbing) — this module has no caching layer and no user concept.

- `inverted_index/` — BM25 keyword search over `Document`s, built fresh per query.
- `semantic_index/` — sentence-transformers (`all-MiniLM-L6-v2`) embeddings, cosine similarity. Both facts and the posting are split into 128-token windows (32 overlap) measured in the model's own tokens — the model silently truncates past 256 tokens (a project fact runs up to ~1500, a posting ~350, and a posting's requirements come last), and it was trained on 128-token sequences. A fact's score is its best (posting chunk, fact chunk) pair. The model itself is loaded once per process and reused; embeddings are still recomputed on every call.
- `helpers/` — shared stateless pieces: `calc_rrf_score`, tokenization (English stopwords and JSON punctuation dropped — every `json.dumps`'d fact and posting shares `{ } : ,` and quote tokens, which only added BM25 noise), token-window chunking.
- `hybrid_search/` — fuses the BM25 and semantic ranked lists via `calc_rrf_score` (`HybridSearch.rrf_search`). A corpus+query search primitive, not a pass/fail gate by itself.
- `document_builder/` — turns the `source_of_truth` files (plus a posting) into `Document`s / a query string.
- `matcher/` — `evaluate_posting()` ties `document_builder` and `hybrid_search` together and applies the threshold rule (`is_match`) to produce the pass/fail verdict.

## Reproducibility

`../requirements.txt` (pinned freeze) and `../pyproject.toml` (direct deps, grouped by module — matching's are `numpy`, `nltk`, `sentence-transformers`, `pydantic`) live at `agent/`, shared across the whole Python service. The venv lives at `../venv`, gitignored. `torch` installs as a `+cpu` build from PyTorch's own index, which `requirements.txt` declares itself (`--extra-index-url`).

## Calibration fixtures

`fixtures/postings/` holds synthetic job postings used to stress-test the threshold — run via `python scripts/calibrate_threshold.py`, which prints each posting's pass/fail and matching-fact breakdown, checks it against the script's `EXPECTED` verdicts (relevant postings must pass, `sales_manager_mismatch.json` must fail), and exits non-zero if any fixture gets the wrong verdict. Not a pytest suite — a manual calibration script.

Status: design and code complete, pending recalibration against real ATS data. See `../CLAUDE.md`.
