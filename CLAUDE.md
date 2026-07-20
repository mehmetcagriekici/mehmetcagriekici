# Working conventions for this repo

## Job-application automation project (planning stage)
- We are designing an automated AI agent to apply to jobs for the user, built inside this folder.
- **No code.** Do not write, scaffold, or edit any code for this project unless the user explicitly asks for code to be written. Default mode is discussion/design only.
- Act as a rubber duck: help the user think through the design out loud, ask clarifying questions, poke at assumptions and edge cases — don't jump to solutions or implementation.
- This constraint applies specifically to the agent-building project itself, not to the existing cover-letter/resume workflow below, which continues as-is.

## Cover letters
- All cover letters are written to `cover.tex`, always. Don't create per-company files (`cover_letter_<company>.tex`) unless explicitly asked — one file, overwritten each time a new job comes in.
- Before overwriting, if the current `cover.tex` content isn't already summarized in `applications.md`, add it there first so it isn't lost.
- Compile after every edit (`pdflatex -interaction=nonstopmode cover.tex`) and confirm it's one page with no overfull/underfull warnings before considering it done. Clean up `.aux`/`.log`/`.out` afterward.

## Honesty — non-negotiable
- Never invent or embellish credentials, degrees, employers, experience, or skills. Every claim in a letter must trace back to `resume.tex` or something explicitly confirmed by the user in conversation.
- If a job's requirements don't match what's in `resume.tex`, name the gap directly in the letter rather than glossing over it or omitting it. This has been the consistent tone across every letter so far (PHP, degree, work permits, years of experience, language, etc.) — keep doing that, don't soften it into vague qualifiers.
- If credentials mentioned in an old/deleted file (git history) aren't in the current `resume.tex`, don't assume they're still accurate — ask the user before using them.
- When a requirement is a hard, unverifiable gap (e.g., years of professional experience, a specific language, a work permit), ask the user for the real facts rather than guessing or hedging.

## Style
- Keep letters simple and direct: short paragraphs, no corporate filler, no generic enthusiasm ("I am a great fit for..."). Match the tone of the job posting where it's direct (e.g., Viaplay, Travelcircus) rather than defaulting to formal boilerplate.
- Match the LaTeX style already established in `cover.tex`/`resume.tex`: accent color `RGB{38,86,166}`, same header block with fontawesome icons and contact info, `hidelinks` hyperref, `parskip`.

## Tracking
- `applications.md` is the source of truth for what's been sent where. Update its Status column only when the user confirms an application was actually submitted — never mark something "Applied" on assumption.
