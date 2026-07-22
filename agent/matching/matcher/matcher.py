from constants.constants import MATCH_RRF_THRESHOLD, MATCH_MIN_FACTS
from document_builder.document_builder import build_source_of_truth_documents, job_posting_to_query
from hybrid_search.hybrid_search import HybridSearch


# turns hybrid_search's ranked output into the actual go/no-go verdict
def is_match(
    rrf_results: list[dict],
    threshold: float = MATCH_RRF_THRESHOLD,
    min_facts: int = MATCH_MIN_FACTS,
) -> bool:
    matching_facts = [r for r in rrf_results if r["rrf_score"] >= threshold]
    return len(matching_facts) >= min_facts


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
    passed = len(matching_facts) >= min_facts

    return {
        "passed": passed,
        "matching_fact_ids": [r["doc_id"] for r in matching_facts],
        "matching_fact_count": len(matching_facts),
        "results": results,
    }
