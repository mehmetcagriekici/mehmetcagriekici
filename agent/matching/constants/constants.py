BM25_K1 = 1.5
BM25_B = 0.75

# a posting passes when at least MATCH_MIN_FACTS distinct fit facts (gap and
# screening-answer facts excluded, see NON_FIT_FACT_PREFIXES) score
# rrf_score >= MATCH_RRF_THRESHOLD against it. Recalibrated 2026-10-07 after
# excluding non-fit facts from the count, ranking every fact (no 50-item cap),
# deterministic tie-breaking, and indexing profile.summary: the sales-manager
# mismatch now has 0 fit facts at every threshold from 0.027 to 0.032, and
# 0.028 gives the relevant fixtures the most room (7/6/7 facts vs. the minimum
# of 4; 0.029 left the Go posting at exactly 4). Still four synthetic
# postings -- recalibrate against real ATS data (scripts/calibrate_threshold.py).
MATCH_RRF_THRESHOLD = 0.028
MATCH_MIN_FACTS = 4

# Facts that describe the candidate's gaps or screening answers rather than
# evidence of fit. They match nearly every posting (anything mentioning
# experience, salary, location...), so counting them inflated every posting's
# fact count -- including mismatches'. They still appear in the ranked results
# (and reach the generator, where the application call needs them for honest
# answers); they just don't count toward the pass/fail verdict or the ranking.
NON_FIT_FACT_PREFIXES = ("known_gap:", "job_preference:")
NON_FIT_FACT_IDS = ("professional_experience",)

# semantic chunking, in embedding-model tokens. all-MiniLM-L6-v2 silently
# truncates anything past 256 tokens and was trained on 128-token sequences,
# so both facts and the posting are split into 128-token windows instead of
# being embedded whole (a project fact runs up to ~1500 tokens, a posting ~350)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_TOKENS = 128
CHUNK_OVERLAP_TOKENS = 32
