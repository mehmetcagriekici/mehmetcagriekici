from ._shared import format_facts, format_posting


def _format_question(question: dict) -> str:
    line = f"- {question['field_id']}: {question['question']}"
    if question.get("max_length"):
        line += f" (max {question['max_length']} characters)"
    return line


def build_application_prompt(facts: list[dict], job_posting: dict, questions: list[dict]) -> str:
    questions_block = "\n".join(_format_question(q) for q in questions)

    return f"""Answer the free-text application questions below for the job posting below, using only the facts given further below.

<job_posting>
{format_posting(job_posting)}
</job_posting>

<questions>
{questions_block}
</questions>

<facts>
{format_facts(facts)}
</facts>

Answer only from the facts given -- if a question cannot be honestly answered from these facts, answer "not provided" rather than inventing anything. For behavioral questions ("tell me about a time you..."), draw on real incident-level material where the facts provide it, not generic feature descriptions. Where a question above states a character limit, keep your answer within it -- the platform enforces it and answers that don't fit will be rejected or truncated.

Respond with a JSON object mapping each field_id to its answer as a string, e.g.:
{{"field_id_1": "answer text", "field_id_2": "answer text"}}"""
