import json

from matching.document_builder.document_builder import posting_content


def format_facts(facts: list[dict]) -> str:
    return "\n".join(f"- ({fact['doc_id']}) {fact['content']}" for fact in facts)


# ensure_ascii=False: the model should read "München", not "M\u00fcnchen".
# < and > are escaped as \u003c/\u003e -- still valid JSON that reads the same,
# but posting text can no longer contain a literal "</job_posting>" and close
# the untrusted-data tag early, making whatever follows look like prompt
# structure (json.dumps alone leaves < and > as-is).
# Only the posting's content fields (posting_content) -- not ids, urls, or the
# stored raw ATS response, which would roughly double the posting's share of
# the context window.
def format_posting(job_posting: dict) -> str:
    return (
        json.dumps(posting_content(job_posting), ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


# the same protection for untrusted text placed outside a JSON blob (form
# questions, posting requirements quoted in the gaps block): HTML entities,
# which the model reads as < and > but which can't form a tag
def escape_untrusted(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;")
