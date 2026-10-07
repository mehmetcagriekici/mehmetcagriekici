# gaps

Decides, in plain code and before any LLM call, which of `source_of_truth/known-gaps.json`'s gaps a cover letter raises for a given posting. **A gap is raised only if the posting asks for the thing it's missing** (decided 2026-09-30, see `../../CLAUDE.md`) — the 7B model misapplied these rules about half the time when it judged them itself (visa raised for a remote role, GPA volunteered unasked).

`decide_gaps(job_posting, known_gaps) -> list[GapDecision]` returns one `GapDecision(gap, applies, reason, fact, phrasing, requirements)` per known gap. `reason` names the rule and the matched text (for the review email / `review_gate/`); `phrasing` is the gap's phrasing with any situational variant already selected; `requirements` quotes the posting's own years-of-experience lines verbatim, so the letter names the narrower stack-specific gap ("3+ years … TypeScript"), not just the general one.

## Rules (keyword checks over the posting's text)

The text checked is the posting's content fields only (`posting_content()` from `matching/document_builder/` — never ids, urls, or the stored `raw` ATS response), with curly apostrophes normalized to straight ones first, since real ATS HTML uses them ("Master’s" once slipped past the degree rule).

| Gap | Raised when |
|---|---|
| `no_professional_experience` | a line states a years requirement — "years" followed by a requirement word ("3+ years of Go", "5 years building…", "years' experience"), or a years figure on a line that also says "experience"; digits or spelled out ("two years"). Every line of the description is checked (prose split into sentences), plus the fixtures' `requirements`/`nice_to_have`. "We are 12 years old" / "founded 10 years ago" don't count. Also raised when the posting mentions professional/work/industry/commercial/paid experience. |
| `in_progress_degree` | the posting mentions a degree, bachelor's, master's, BSc/MSc, diploma, or PhD/Ph.D. — or a short form (BS, M.S., BA, MA) followed by "in", "degree", "or", or a slash. The `location` field isn't read for this rule: a degree requirement never appears there, but US state codes ("Boston, MA") do. |
| `gpa` | the posting mentions GPA / grade point average |
| `visa_sponsorship_needed` | not when Turkey is the *only* location ("Istanbul or Berlin" doesn't count); always for a hybrid/on-site `workplace_type` or location text; for a remote role, only if the location names a region on either side of "remote" ("Remote (US/Canada)", "US - Remote", "United States (Remote)", or a remote `workplace_type` with location "United States") — words that only set hours or say "no restriction" ("EU timezones", "worldwide", "remote-first", "fully remote") don't count — or if the posting requires authorization/residence *of the candidate* in a place ("authorized to work in the United States", "candidates must be based in Canada", "open to candidates in the EU", "US-based candidates only"). A company blurb's "Acme is based in Berlin" doesn't count, nor does a bare "we cannot sponsor visas" on a fully remote role — working remotely from Turkey needs no visa. No remote signal at all raises it. |

Ambiguity resolves toward raising a gap, never hiding one — e.g. a posting with no usable location raises the visa gap. Keyword rules are crude (a "360-degree view" would match the degree rule); that errs in the same direction.

A gap in `known-gaps.json` with no rule here raises `ValueError` rather than being silently skipped — a new gap needs its "when does a posting ask for this?" rule written first.
