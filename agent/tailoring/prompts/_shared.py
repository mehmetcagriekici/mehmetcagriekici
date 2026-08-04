import json


def format_facts(facts: list[dict]) -> str:
    return "\n".join(f"- ({fact['doc_id']}) {fact['content']}" for fact in facts)


def format_posting(job_posting: dict) -> str:
    return json.dumps(job_posting)
