from tailoring.gaps.gaps import GapDecision
from tailoring.write.write import opening_sentence

from ._shared import escape_untrusted, format_facts, format_posting

# The model writes only the parts of the letter that need judgment about this
# posting. The opening sentence, the gaps paragraph (the user's known-gaps.json
# `text`, word for word) and the closing are written by code -- see
# write.py's CoverLetterDraft for why.
COVER_LETTER_SCHEMA = """{
  "why": "1-2 sentences that continue the opening: why this role -- link one specific fact to one specific requirement of the posting",
  "experience": "1-2 short paragraphs on relevant experience, selected for relevance to this posting",
  "stack_gap": "ONE sentence naming the narrower experience gap for the quoted requirement -- only if it names a specific language, framework or stack; omit otherwise"
}"""

# same shape minus stack_gap: used when the posting quoted no years requirement
COVER_LETTER_SCHEMA_NO_STACK_GAP = """{
  "why": "1-2 sentences that continue the opening: why this role -- link one specific fact to one specific requirement of the posting",
  "experience": "1-2 short paragraphs on relevant experience, selected for relevance to this posting"
}"""


# gaps: the known gaps that apply to this posting, already decided in code
# (tailoring/gaps/gaps.py). The model never writes their sentences -- it only
# sees the posting's quoted years requirement(s), for the one stack_gap
# sentence. The gaps' `guidance` isn't sent: its example sentence (about
# TypeScript) could be copied into a letter for a posting about another
# stack. Passed independently of the hybrid_search facts (option (b),
# ../../CLAUDE.md).
def build_cover_letter_prompt(facts: list[dict], job_posting: dict, gaps: list[GapDecision]) -> str:
    opening = opening_sentence(job_posting.get("title"), job_posting.get("company"))
    stack_gaps = [g for g in gaps if g.requirements]

    if stack_gaps:
        # quoted from the posting -- untrusted text inside our own tag
        quoted = "\n".join(f'- "{escape_untrusted(r)}"' for g in stack_gaps for r in g.requirements)
        stack_section = f"""<years_requirements>
{quoted}
</years_requirements>

The candidate doesn't meet the years requirement(s) above; a separate paragraph already says so in general terms. If a requirement names a specific language, framework or stack, write "stack_gap": one plain sentence naming the narrower gap for it, using only the facts (e.g. how much of the candidate's work actually used that stack). If no requirement names one, omit "stack_gap"."""
        schema = COVER_LETTER_SCHEMA
    else:
        stack_section = ""
        schema = COVER_LETTER_SCHEMA_NO_STACK_GAP

    return f"""Write parts of a cover letter for the job posting below, using only the facts given below it.

<job_posting>
{format_posting(job_posting)}
</job_posting>

<facts>
{format_facts(facts)}
</facts>

{stack_section}

The opening sentence, the closing, and a paragraph about the candidate's gaps are written separately. The letter opens with: "{escape_untrusted(opening)}" -- "why" continues straight after it, so don't restate the role or company and don't greet. Neither "why" nor "experience" mentions the candidate's gaps (experience, degree, GPA, visa) -- they're handled separately.

In the experience paragraph(s), describe each project only with what its own fact says -- its own tech and what it actually does. Don't claim the posting's technologies for a project whose fact doesn't list them.

Match the tone of the posting where the posting itself is direct, rather than defaulting to formal boilerplate. No generic filler ("I am excited to...", "passion for...", "I believe my skills align well..."). Keep it short: the whole letter has to fit on one page. Do not invent numbers, percentages, or outcomes (e.g. performance gains, user counts, cost savings) that aren't present in the facts.

Respond with a JSON object matching exactly this shape:
{schema}"""
