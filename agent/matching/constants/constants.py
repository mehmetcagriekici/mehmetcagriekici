BM25_K1 = 1.5
BM25_B = 0.75
SEARCH_LIMIT = 50

# a posting passes when at least MATCH_MIN_FACTS distinct source_of_truth facts
# score rrf_score >= MATCH_RRF_THRESHOLD against it (empirically corrected
# 2026-07-22 from an initial 0.026 guess that failed to discriminate a real
# mismatched posting from a real relevant one — see matching/README.md)
MATCH_RRF_THRESHOLD = 0.028
MATCH_MIN_FACTS = 4
