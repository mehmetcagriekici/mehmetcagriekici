BM25_K1 = 1.5
BM25_B = 0.75
SEARCH_LIMIT = 50

# a posting passes when at least MATCH_MIN_FACTS distinct source_of_truth facts
# score rrf_score >= MATCH_RRF_THRESHOLD against it. Recalibrated 2026-09-30
# (was 0.028) after token-window chunking and the BM25 punctuation fix changed
# the rankings -- and 0.028 had already stopped separating anything on the
# current corpus (the sales-manager mismatch fixture passed with 8 facts).
# 0.029 is the only value that separates the fixtures: relevant postings keep
# 5/5/9 facts, the mismatch 3. Thin margin, 4 fixtures -- recalibrate against
# real ATS data (scripts/calibrate_threshold.py; see matching/README.md).
MATCH_RRF_THRESHOLD = 0.029
MATCH_MIN_FACTS = 4

# semantic chunking, in embedding-model tokens. all-MiniLM-L6-v2 silently
# truncates anything past 256 tokens and was trained on 128-token sequences,
# so both facts and the posting are split into 128-token windows instead of
# being embedded whole (a project fact runs up to ~1500 tokens, a posting ~350)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_TOKENS = 128
CHUNK_OVERLAP_TOKENS = 32
