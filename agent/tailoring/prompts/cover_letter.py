from tailoring.gaps.gaps import GapDecision

from ._shared import format_facts, format_posting

COVER_LETTER_SCHEMA = """{
  "opening": "1 short paragraph naming the role and company, and why you are writing -- no gaps",
  "experience": "1-2 short paragraphs on relevant experience, selected for relevance to this posting -- no gaps",
  "gaps": "1 short paragraph raising, plainly and directly, every gap listed in <gaps_to_raise>, and nothing else",
  "closing": "1-2 sentence close -- no gaps, and don't repeat the experience"
}"""

# same shape minus "gaps": used when no known gap applies to the posting
COVER_LETTER_SCHEMA_NO_GAPS = """{
  "opening": "1 short paragraph naming the role and company, and why you are writing",
  "experience": "1-2 short paragraphs on relevant experience, selected for relevance to this posting",
  "closing": "1-2 sentence close -- don't repeat the experience"
}"""


def _format_gap(decision: GapDecision) -> str:
    lines = [f"- {decision.gap}", f"  fact: {decision.fact}", f"  phrasing: {decision.phrasing}"]
    if decision.requirements:
        quoted = "; ".join(f'"{r}"' for r in decision.requirements)
        lines.append(f"  the posting's own requirement(s) this answers: {quoted}")
    return "\n".join(lines)


# gaps: the known gaps that apply to this posting, already decided in code
# (tailoring/gaps/gaps.py) -- a gap is raised only when the posting asks for
# what it's missing, and the model no longer judges that itself. Passed
# independently of the hybrid_search facts (option (b), ../../CLAUDE.md).
def build_cover_letter_prompt(facts: list[dict], job_posting: dict, gaps: list[GapDecision]) -> str:
    if gaps:
        gaps_section = f"""<gaps_to_raise>
{chr(10).join(_format_gap(g) for g in gaps)}
</gaps_to_raise>

Each gap above has already been checked against this posting: the posting asks for something the candidate doesn't have. Raise every one of them in the "gaps" paragraph, plainly and directly, following its phrasing -- including any specifics it asks for (a real duration; and where the posting's own requirement names a specific language or stack, the narrower gap for that stack, not just the general one). Never soften, hedge, or leave one out. Gaps belong only in the "gaps" paragraph -- the opening, experience, and closing never mention or repeat one. Don't raise anything not listed above (no degree, GPA, visa, or experience gap unless it's listed)."""
        schema = COVER_LETTER_SCHEMA
    else:
        gaps_section = """This posting doesn't ask for anything the candidate is known to lack, so the letter has no gaps paragraph. Don't mention degree status, GPA, visa or work-permit status, or lack of professional experience anywhere."""
        schema = COVER_LETTER_SCHEMA_NO_GAPS

    return f"""Write a cover letter tailored to the job posting below, using only the facts given below it.

<job_posting>
{format_posting(job_posting)}
</job_posting>

<facts>
{format_facts(facts)}
</facts>

{gaps_section}

In the experience paragraph(s), describe each project only with what its own fact says -- its own tech and what it actually does. Don't claim the posting's technologies for a project whose fact doesn't list them.

Address the specific role and company by name. Match the tone of the posting where the posting itself is direct, rather than defaulting to formal boilerplate. No generic filler ("I am a great fit for...", "I believe my skills align well..."). 3-4 short paragraphs total: this has to fit on one page. Do not invent numbers, percentages, or outcomes (e.g. performance gains, user counts, cost savings) that aren't present in the facts.

Respond with a JSON object matching exactly this shape:
{schema}"""
