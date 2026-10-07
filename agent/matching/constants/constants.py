BM25_K1 = 1.5
BM25_B = 0.75

# a posting passes when at least MATCH_MIN_FACTS distinct fit facts (gap,
# screening-answer and logistics facts excluded, see NON_FIT_FACT_PREFIXES /
# NON_FIT_FACT_IDS) score rrf_score >= MATCH_RRF_THRESHOLD against it.
# Recalibrated 2026-10-07 (second pass), after the query was limited to the
# posting's content fields (no id/salary) and education + logistics
# preferences stopped counting: at 0.028 the relevant fixtures keep 9/8/8 fit
# facts and the sales-manager mismatch 2, so MATCH_MIN_FACTS = 5 leaves a
# 3-fact margin on both sides -- better than any threshold with the old
# minimum of 4. Still four synthetic postings -- recalibrate against real ATS
# data (scripts/calibrate_threshold.py).
MATCH_RRF_THRESHOLD = 0.028
MATCH_MIN_FACTS = 5

# Facts that describe the candidate's gaps or screening answers rather than
# evidence of fit. They match nearly every posting (anything mentioning
# experience, salary, location...), so counting them inflated every posting's
# fact count -- including mismatches'. They still appear in the ranked results
# (and reach the generator, where the application call needs them for honest
# answers); they just don't count toward the pass/fail verdict or the ranking.
NON_FIT_FACT_PREFIXES = ("known_gap:", "job_preference:")
# Same reasoning, decided 2026-10-07: education holds the GPA and degree status
# (gap material, decided by tailoring/gaps -- and it inflated any posting that
# mentions a degree); work_mode, regions_open_to and hard_deal_breakers are
# logistics that match any posting saying "remote" or "Europe". The roles and
# tech_stack_priority preferences still count -- role type and stack are fit.
NON_FIT_FACT_IDS = (
    "professional_experience",
    "education",
    "preference:work_mode",
    "preference:regions_open_to",
    "preference:hard_deal_breakers",
)

# semantic chunking, in embedding-model tokens. all-MiniLM-L6-v2 silently
# truncates anything past 256 tokens and was trained on 128-token sequences,
# so both facts and the posting are split into 128-token windows instead of
# being embedded whole (a project fact runs up to ~1500 tokens, a posting ~350)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_TOKENS = 128
CHUNK_OVERLAP_TOKENS = 32
