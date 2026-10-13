from tailoring.gaps.gaps import GapDecision
from tailoring.write.write import opening_sentence

from ._shared import escape_untrusted, format_facts, format_posting

# The model writes only the parts of the letter that need judgment about this
# posting. The opening sentence, the gaps paragraph (the user's known-gaps.json
# `text`, word for word) and the closing are written by code -- see
# write.py's CoverLetterDraft for why.
#
# The Nordbridge reruns (2026-10-07, 2026-10-13) drifted in the same places
# each time: a sentence summing up the candidate's stack across projects (it
# added the posting's React), "why" adopting the posting's work areas ("across
# frontend and backend"), and stack_gap negating the posting's requirement
# ("not ... for more than three years", implying some years). Project-by-project
# sentences stayed faithful -- so "experience" is limited to those, and
# stack_gap is told what to state instead of what to avoid.
COVER_LETTER_SCHEMA = """{
  "why": "1-2 sentences that continue the opening: why this role -- link one specific fact about the candidate to one specific thing the job involves; the job's technologies appear only as the job's, never as the candidate's",
  "experience": "1-2 short paragraphs about specific projects from the facts: what each one is and does, with only the technologies its own fact lists; no sentence summing up the candidate's overall skills or stack",
  "stack_gap": "ONE sentence stating what the facts show about the candidate's work with the stack named in the quoted requirement (which project used it, or that none did) -- no number of years, and not the requirement restated or negated; omit if the requirement names no specific language, framework or stack"
}"""

# same shape minus stack_gap: used when the posting quoted no years requirement
COVER_LETTER_SCHEMA_NO_STACK_GAP = """{
  "why": "1-2 sentences that continue the opening: why this role -- link one specific fact about the candidate to one specific thing the job involves; the job's technologies appear only as the job's, never as the candidate's",
  "experience": "1-2 short paragraphs about specific projects from the facts: what each one is and does, with only the technologies its own fact lists; no sentence summing up the candidate's overall skills or stack"
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

The candidate doesn't meet the years requirement(s) above; a separate paragraph already says so in general terms. If a requirement names a specific language, framework or stack, write "stack_gap": one plain sentence stating what the facts show about the candidate's work with that stack -- which project used it, or that no project did. State it as a fact about the candidate's projects; don't restate or negate the requirement ("I haven't done X for more than three years" implies some years), and don't mention any number of years. If no requirement names one, omit "stack_gap"."""
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

The opening sentence, the closing, and a paragraph about the candidate's gaps are written separately. The letter opens with: "{escape_untrusted(opening)}" -- "why" continues straight after it, so don't restate the role or company and don't greet.

The job posting describes the job, not the candidate. Everything said about the candidate, in "why" and "experience" alike, comes from the facts above and nothing else:
- A technology, tool, or area of work ("frontend", "backend", "fullstack", ...) belongs to the candidate only if a fact above names it for the candidate. If the posting asks for something no fact names, leave it out: don't claim it, and don't mention it as missing.
- In "why", the posting's technologies and areas of work may appear only as what the job involves, never as something the candidate has used, done, or worked across.
- "experience" describes specific projects, each only with what its own fact says: its own tech and what it actually does. Don't write a sentence that sums up the candidate's overall skills or lists technologies across projects -- name each technology inside the sentence about the project whose fact lists it.
- Never make a claim stronger than its fact: no "extensive", "strong", "solid", "deep", "expert", "experienced", "proven", "production" or "years of" unless a fact says exactly that. Keep every qualifier a fact carries ("experimental", "prototype", "in progress").
- Do not invent numbers, percentages, or outcomes (e.g. performance gains, user counts, cost savings) that aren't present in the facts.
- Neither "why" nor "experience" mentions the candidate's gaps (experience, degree, GPA, visa) -- they're handled separately.

Match the tone of the posting where the posting itself is direct, rather than defaulting to formal boilerplate. No generic filler ("I am excited to...", "passion for...", "I believe my skills align well..."). Keep it short: the whole letter has to fit on one page.

Every technology you name in "why" or "experience" must appear in a fact above for the candidate -- if you can't point to the fact, leave it out.

Respond with a JSON object matching exactly this shape:
{schema}"""
