from matching.constants.constants import (
    MATCH_MIN_FACTS,
    MATCH_RRF_THRESHOLD,
    NON_FIT_FACT_IDS,
    NON_FIT_FACT_PREFIXES,
)
from matching.document_builder.document_builder import (
    build_source_of_truth_documents,
    job_posting_to_query,
)
from matching.hybrid_search.hybrid_search import HybridSearch


def _is_fit_fact(doc_id: str) -> bool:
    return not doc_id.startswith(NON_FIT_FACT_PREFIXES) and doc_id not in NON_FIT_FACT_IDS


# facts at or above the threshold that count as evidence of fit -- gap and
# screening-answer facts excluded (see NON_FIT_FACT_PREFIXES)
def fit_fact_count(rrf_results: list[dict], threshold: float = MATCH_RRF_THRESHOLD) -> int:
    return sum(1 for r in rrf_results if r["rrf_score"] >= threshold and _is_fit_fact(r["doc_id"]))


# turns hybrid_search's ranked output into the actual go/no-go verdict
def is_match(
    rrf_results: list[dict],
    threshold: float = MATCH_RRF_THRESHOLD,
    min_facts: int = MATCH_MIN_FACTS,
) -> bool:
    return fit_fact_count(rrf_results, threshold) >= min_facts


# full orchestration: source_of_truth files -> Documents -> hybrid_search -> verdict.
# no caching layer, by design (see matching/README.md) — everything is rebuilt
# fresh on every call.
def evaluate_posting(
    job_posting: dict,
    source_of_truth_dir: str,
    threshold: float = MATCH_RRF_THRESHOLD,
    min_facts: int = MATCH_MIN_FACTS,
) -> dict:
    documents = build_source_of_truth_documents(source_of_truth_dir)
    search = HybridSearch(documents)
    query = job_posting_to_query(job_posting)
    results = search.rrf_search(query)

    matching_facts = [r for r in results if r["rrf_score"] >= threshold]

    return {
        "passed": is_match(results, threshold, min_facts),
        # fit facts only -- the pass/fail count and the ranking key for
        # choosing which matched posting to generate for next
        "matching_fact_count": fit_fact_count(results, threshold),
        # every fact at or above the threshold, gap/screening facts included:
        # the generator's input (generate()'s facts) -- tailoring itself keeps
        # gap-governed facts out of the resume/cover letter prompts
        "matching_facts": matching_facts,
        "matching_fact_ids": [r["doc_id"] for r in matching_facts],
        "results": results,
    }
