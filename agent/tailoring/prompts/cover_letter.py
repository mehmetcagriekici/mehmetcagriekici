from ._shared import format_facts, format_posting

COVER_LETTER_SCHEMA = """{
  "opening": "1 short paragraph naming the role and company, and why you are writing",
  "experience": "1-2 short paragraphs on relevant experience, selected for relevance to this posting",
  "gaps": "1 short paragraph naming, plainly and directly, any hard mismatch between this posting's requirements and the facts given (work permit, years of experience, degree status, GPA, etc.) -- omit this field entirely only if none of the given facts describe a mismatch with this posting",
  "closing": "1 short closing paragraph"
}"""


def build_cover_letter_prompt(facts: list[dict], job_posting: dict) -> str:
    return f"""Write a cover letter tailored to the job posting below, using only the facts given below it.

<job_posting>
{format_posting(job_posting)}
</job_posting>

<facts>
{format_facts(facts)}
</facts>

Address the specific role and company by name. Match the tone of the posting where the posting itself is direct, rather than defaulting to formal boilerplate. No generic enthusiasm ("I am a great fit for..."). 3-4 short paragraphs total: this has to fit on one page. Do not invent numbers, percentages, or outcomes (e.g. performance gains, user counts, cost savings) that aren't present in the facts.

Respond with a JSON object matching exactly this shape:
{COVER_LETTER_SCHEMA}"""
