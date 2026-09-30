# gaps

Decides, in plain code and before any LLM call, which of `source_of_truth/known-gaps.json`'s gaps a cover letter raises for a given posting. **A gap is raised only if the posting asks for the thing it's missing** (decided 2026-09-30, see `../../CLAUDE.md`) — the 7B model misapplied these rules about half the time when it judged them itself (visa raised for a remote role, GPA volunteered unasked).

`decide_gaps(job_posting, known_gaps) -> list[GapDecision]` returns one `GapDecision(gap, applies, reason, fact, phrasing, requirements)` per known gap. `reason` names the rule and the matched text (for the review email / `review_gate/`); `phrasing` is the gap's phrasing with any situational variant already selected; `requirements` quotes the posting's own years-of-experience lines verbatim, so the letter names the narrower stack-specific gap ("3+ years … TypeScript"), not just the general one.

## Rules (keyword checks over the posting's text)

| Gap | Raised when |
|---|---|
| `no_professional_experience` | a requirement line asks for years ("3+ years", "5-7 years"), or the posting mentions professional/work/industry/commercial experience |
| `in_progress_degree` | the posting mentions a degree, bachelor's, master's, BSc/MSc, diploma, or PhD |
| `gpa` | the posting mentions GPA / grade point average |
| `visa_sponsorship_needed` | not when the role is located in Turkey; otherwise when the posting mentions work authorization, visas, work permits, or sponsorship; otherwise unless the role is fully remote (remote with no qualifier, or only a timezone one — "Remote (US/Canada)" counts as region-restricted and raises it) |

Ambiguity resolves toward raising a gap, never hiding one — e.g. a posting with no usable location raises the visa gap. Keyword rules are crude (a "360-degree view" would match the degree rule); that errs in the same direction.

A gap in `known-gaps.json` with no rule here raises `ValueError` rather than being silently skipped — a new gap needs its "when does a posting ask for this?" rule written first.
