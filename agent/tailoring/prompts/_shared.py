import json


def format_facts(facts: list[dict]) -> str:
    return "\n".join(f"- ({fact['doc_id']}) {fact['content']}" for fact in facts)


# ensure_ascii=False: the model should read "München", not "M\u00fcnchen"
def format_posting(job_posting: dict) -> str:
    return json.dumps(job_posting, ensure_ascii=False)


def format_known_gaps(known_gaps: list[dict]) -> str:
    return "\n".join(
        f"- ({gap['gap']}) {json.dumps(gap, ensure_ascii=False)}" for gap in known_gaps
    )
