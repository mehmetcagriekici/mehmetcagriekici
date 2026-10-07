# gaps

Decides, in plain code and before any LLM call, which of `source_of_truth/known-gaps.json`'s gaps a cover letter raises for a given posting. **A gap is raised only if the posting asks for the thing it's missing** (decided 2026-09-30, see `../../CLAUDE.md`) — the 7B model misapplied these rules about half the time when it judged them itself (visa raised for a remote role, GPA volunteered unasked).

`decide_gaps(job_posting, known_gaps) -> list[GapDecision]` returns one `GapDecision(gap, applies, reason, fact, phrasing, requirements)` per known gap. `reason` names the rule and the matched text (for the review email / `review_gate/`); `phrasing` is the gap's phrasing with any situational variant already selected; `requirements` quotes the posting's own years-of-experience lines verbatim, so the letter names the narrower stack-specific gap ("3+ years … TypeScript"), not just the general one.

## Rules (keyword checks over the posting's text)

| Gap | Raised when |
|---|---|
| `no_professional_experience` | a requirement line asks for years ("3+ years", "5-7 years"), or the posting mentions professional/work/industry/commercial experience |
| `in_progress_degree` | the posting mentions a degree, bachelor's, master's, BSc/MSc, diploma, or PhD |
| `gpa` | the posting mentions GPA / grade point average |
| `visa_sponsorship_needed` | not when the location is in Turkey; always for a hybrid/on-site work mode or location text; for a remote role, only if it's restricted to a region ("Remote (US/Canada)", or a remote work mode with location "United States" — a timezone-only qualifier doesn't count) or the posting ties work authorization/residence to a place ("authorized to work in the United States", "must reside in Canada"). A bare "we cannot sponsor visas" on a fully remote role doesn't raise it — working remotely from Turkey needs no visa. No remote signal at all raises it. Location text and the structured `workplace_type`/`remote` fields are read separately (joined into one string, a second "remote" was once mistaken for a region). |

Ambiguity resolves toward raising a gap, never hiding one — e.g. a posting with no usable location raises the visa gap. Keyword rules are crude (a "360-degree view" would match the degree rule); that errs in the same direction.

A gap in `known-gaps.json` with no rule here raises `ValueError` rather than being silently skipped — a new gap needs its "when does a posting ask for this?" rule written first.
