# Backlog

Open findings from the external reviews of 2026-10-07, checked against HEAD (`3a07d39`); findings already fixed there are dropped. A gap-rule finding is fixed only together with a test in `tests/test_gaps.py`; xfail cases there point here.

## FIX NOW
Can cause irreversible harm: a posting permanently excluded by mistake, a wrong or misleading application submitted, or every future run blocked.

- **The generator still turns the posting's wording into claims about the candidate** — model-written parts of the cover letter and resume (`tailoring/prompts/`). A misleading application once anything can be submitted; nothing can be yet (no `form_automation/`). A tailoring bug, fixed in `tailoring/` by the user directly (2026-10-13) — not closed by `review_gate/`, which stays the last check before submission.
  - 14B, 2026-10-07: BlightSanest given "React for its frontend", the Pub/sub CLI "a Node.js backend using Express" — neither fact mentions React, Node or Express.
  - 14B rerun of the same Nordbridge fixture, 2026-10-13: `experience` lists "Go, Python, React, and PostgreSQL" (React in no fact) and claims "extensive experience"; `why` claims work "across both frontend and backend" (no frontend fact); `stack_gap` reads "I have not built web applications with TypeScript for more than three years" — the posting's requirement negated, implying some years. Resume summary: "enjoy building web applications with TypeScript", echoing the posting's first requirement instead of starting from `profile.summary`. The code-written parts (opening, gap text, closing) and the gap decisions were all correct; project sentences matched their facts.

(Fixed: the three items from 2026-10-07 — each with a test: the prompt-length guard no longer excludes the best matches, since `generate()` trims the lowest-ranked facts to fit (`tests/test_generate.py`); a named office outside Turkey overrides the Turkey exemption (`istanbul-location-onsite-berlin`, with `istanbul-location-onsite-istanbul` guarding the other direction); experience requirements in months are recognized (`months-of-experience`).

## BEFORE SOURCING
Will matter once real postings flow, but causes no irreversible harm by itself.

(none open)

## LATER
Docs mismatches, unused code, cleanup, style, design smells.

- **JSON keys are indexed as words** — `matching/document_builder/document_builder.py:176` (`job_posting_to_query` and the per-fact `_dumps`). Field names like "title"/"description" become BM25 tokens; the reviewer judged it below the harm bar, and the fit-fact exclusions already removed its worst effect.
- **`gaps.py` grows a branch per patched phrasing** — `tailoring/gaps/gaps.py` (180 → ~330 lines in a week). A design smell: new branches interact with old ones; to be judged against real postings, not imagined ones.
- **Docs restate the code** — `tailoring/gaps/README.md` (rule table) and other module READMEs. Each fix touched ~20 files, and every copy is another place for drift; a design smell, not a defect.
- **claude.ai Project knowledge files still say "planning stage, no code"** — outside this repo. A docs mismatch that misleads new sessions there; only the user can update it.
