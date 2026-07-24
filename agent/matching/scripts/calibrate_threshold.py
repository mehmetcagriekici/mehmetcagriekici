import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from matcher.matcher import evaluate_posting

SOURCE_OF_TRUTH_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "source_of_truth")
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "postings")


def main():
    for path in sorted(glob.glob(os.path.join(FIXTURES_DIR, "*.json"))):
        posting = json.load(open(path))
        result = evaluate_posting(posting, SOURCE_OF_TRUTH_DIR)

        print(f"\n=== {os.path.basename(path)} ({posting['title']}) ===")
        print(f"passed: {result['passed']}  matching_fact_count: {result['matching_fact_count']}")
        print("top matching facts:")
        for r in result["results"][: result["matching_fact_count"] or 5]:
            print(f"  rrf_score={r['rrf_score']:.4f}  doc_id={r['doc_id']}")


if __name__ == "__main__":
    main()
