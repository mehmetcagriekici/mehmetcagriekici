import glob
import json
import os
import sys

# agent/ is the import root (see ../../pyproject.toml); this lets the script
# run directly without an editable install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from matching.matcher.matcher import evaluate_posting

SOURCE_OF_TRUTH_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "source_of_truth")
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "postings")

# expected verdict per fixture -- a relevant posting must pass, a mismatch must
# fail. Kept here rather than inside the fixture JSON, since the whole posting
# JSON becomes the search query and an extra key would leak into it.
EXPECTED = {
    "data_engineer_mlops.json": True,
    "fullstack_developer.json": True,
    "sales_manager_mismatch.json": False,
    "senior_backend_go_onsite.json": True,
}


def main():
    wrong = []
    for path in sorted(glob.glob(os.path.join(FIXTURES_DIR, "*.json"))):
        with open(path) as f:
            posting = json.load(f)
        result = evaluate_posting(posting, SOURCE_OF_TRUTH_DIR)

        name = os.path.basename(path)
        expected = EXPECTED.get(name)
        if expected is None:
            verdict = "no expected verdict -- add it to EXPECTED"
        elif result["passed"] == expected:
            verdict = "as expected"
        else:
            verdict = "WRONG"
            wrong.append(name)

        print(f"\n=== {name} ({posting['title']}) ===")
        print(
            f"passed: {result['passed']}  matching_fact_count: "
            f"{result['matching_fact_count']}  [{verdict}]"
        )
        print("top matching facts:")
        for r in result["results"][: result["matching_fact_count"] or 5]:
            print(f"  rrf_score={r['rrf_score']:.4f}  doc_id={r['doc_id']}")

    listed = f": {', '.join(wrong)}" if wrong else ""
    print(f"\n{len(wrong)} fixture(s) with the wrong verdict{listed}")
    if wrong:
        sys.exit(1)


if __name__ == "__main__":
    main()
