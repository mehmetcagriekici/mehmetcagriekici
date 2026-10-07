from ._shared import escape_untrusted, format_facts, format_posting

RESUME_SCHEMA = """{
  "summary": "2-3 sentences: the candidate's own summary (given above), shortened and tailored to this posting",
  "skills": {
    "category name, as given in the facts": ["skill", "skill", ...]
  },
  "projects": [
    {
      "name": "project name",
      "status": "short status tag, e.g. 'in development' or 'live demo' -- include only when it adds something worth knowing, omit otherwise",
      "dates": "date range, as given in the facts",
      "tech": "comma-separated tech stack",
      "description": "1 short sentence describing what the project is",
      "bullets": ["bullet point", "bullet point", ...],
      "repo": "repo URL -- include only if given in the facts, omit otherwise"
    }
  ],
  "certifications": [
    {
      "name": "certification or program name",
      "dates": "date range, as given in the facts",
      "details": "1-2 sentence description",
      "verification_url": "verification URL -- include only if given in the facts, omit otherwise"
    }
  ]
}"""


# candidate_summary: profile.json's `summary`, written by the candidate. The
# resume summary starts from it instead of being written from scratch -- left
# to write a "professional summary" from a few facts, the model reached for the
# genre's default opener ("Experienced backend engineer...").
def build_resume_prompt(facts: list[dict], job_posting: dict, candidate_summary: str) -> str:
    return f"""Write the content for a one-page resume tailored to the job posting below, using only the facts given below it.

<job_posting>
{format_posting(job_posting)}
</job_posting>

<candidate_summary>
{escape_untrusted(candidate_summary)}
</candidate_summary>

<facts>
{format_facts(facts)}
</facts>

The resume's "summary" starts from the candidate's own summary above: shorten it to 2-3 sentences and emphasize what's relevant to this posting. Keep its claims and its self-description -- don't add titles, seniority, years, or expertise it doesn't state (no "experienced", "senior", "proven").

Select whichever facts, and however many, best match this posting — you are not required to use all of them, and you must not use anything not listed above. Group skills under the same categories given in the facts; do not invent new categories. List a skill only if a fact lists it, and keep any qualifier its fact attaches (e.g. "Kubernetes (experimental)" when the fact says it's experimental). A project's "tech", description, and bullets use only what that project's own fact says — never add the posting's technologies to a project that didn't use them. Order projects by relevance to this posting. Keep bullets short: this has to fit on one page. Do not invent numbers, percentages, or outcomes (e.g. performance gains, user counts, cost savings) that aren't present in the facts.

This resume has no education or professional-experience section. If a fact about education, degree status, GPA, or years of professional experience is among the facts given, do not put it anywhere in this output — it belongs in the cover letter, not here.

Respond with a JSON object matching exactly this shape:
{RESUME_SCHEMA}"""
