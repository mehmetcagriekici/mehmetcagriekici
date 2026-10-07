import json


def format_facts(facts: list[dict]) -> str:
    return "\n".join(f"- ({fact['doc_id']}) {fact['content']}" for fact in facts)


# ensure_ascii=False: the model should read "München", not "M\u00fcnchen".
# < and > are escaped as \u003c/\u003e -- still valid JSON that reads the same,
# but posting text can no longer contain a literal "</job_posting>" and close
# the untrusted-data tag early, making whatever follows look like prompt
# structure (json.dumps alone leaves < and > as-is).
def format_posting(job_posting: dict) -> str:
    return (
        json.dumps(job_posting, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
    )


# the same protection for untrusted text placed outside a JSON blob (form
# questions, posting requirements quoted in the gaps block): HTML entities,
# which the model reads as < and > but which can't form a tag
def escape_untrusted(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;")
