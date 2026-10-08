# Backlog

Open findings from the external reviews of 2026-10-07, checked against HEAD (`3a07d39`); findings already fixed there are dropped. A gap-rule finding is fixed only together with a test in `tests/test_gaps.py`; xfail cases there point here.

## FIX NOW
Can cause irreversible harm: a posting permanently excluded by mistake, a wrong or misleading application submitted, or every future run blocked.

- **The generator still invents technology for projects** — model-written `experience` paragraph (`tailoring/prompts/cover_letter.py`). 14B live run, 2026-10-07: BlightSanest given "React for its frontend", the Pub/sub CLI "a Node.js backend using Express" — neither fact mentions React, Node or Express. A misleading application once anything can be submitted; nothing can be yet (no `form_automation/`). Short fix: `review_gate/` (the Controller's honesty check) before any submission path exists.

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
