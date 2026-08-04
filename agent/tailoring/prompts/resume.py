from ._shared import format_facts, format_posting

RESUME_SCHEMA = """{
  "summary": "2-3 sentence professional summary, tailored to this specific posting",
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
      "repo": "repo URL, if given in the facts"
    }
  ],
  "certifications": [
    {
      "name": "certification or program name",
      "dates": "date range, as given in the facts",
      "details": "1-2 sentence description",
      "verification_url": "verification URL, if given in the facts"
    }
  ]
}"""


def build_resume_prompt(facts: list[dict], job_posting: dict) -> str:
    return f"""Write the content for a one-page resume tailored to the job posting below, using only the facts given below it.

<job_posting>
{format_posting(job_posting)}
</job_posting>

<facts>
{format_facts(facts)}
</facts>

Select whichever facts, and however many, best match this posting — you are not required to use all of them, and you must not use anything not listed above. Group skills under the same categories given in the facts; do not invent new categories. Order projects by relevance to this posting. Keep bullets short: this has to fit on one page. Do not invent numbers, percentages, or outcomes (e.g. performance gains, user counts, cost savings) that aren't present in the facts.

This resume has no education or professional-experience section. If a fact about education, degree status, GPA, or years of professional experience is among the facts given, do not put it anywhere in this output — it belongs in the cover letter, not here.

Respond with a JSON object matching exactly this shape:
{RESUME_SCHEMA}"""
