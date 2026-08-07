# review_gate

**Pipeline role: Application Controller.** Third stage of `Data -> Hybrid Search -> Application Generator -> Application Controller -> Application API`. A second LLM — distinct from `tailoring/`'s Generator — checks the Generator's output against `source_of_truth` (honesty: is every claim traceable to a real fact) and against the job posting (relevance: does the answer actually address what was asked). It isn't re-judging fit — `matching/` already decided that deterministically; this is QC on what the Generator produced.

Any failure on either check — no severity distinction between honesty and relevance — routes to human review. Passing both sends the application straight to `form_automation/` for submission. A user-maintained override list (always review certain roles/companies regardless of the check) applies independently on top of this.

**Language: Python** — internal module of the shared Python service, not routed through Go.

**Notification:** no dashboard. A push email fires immediately when something routes to review, with clickable approve/reject links. If the user doesn't respond before that instance's run times out, the item defaults to reject — nothing submits without explicit approval. Separately, each instance also produces an end-of-run report summarizing everything it did, for the user to read at their own pace.

**Email content:** the full generated package shown inline (resume text, cover letter text, filled form field answers) — not summarized, not attachments, since missing a bad generation in a too-short email is worse than a long one. Also includes a log/report-style breakdown of why that application was routed to review (the honesty/relevance verdict and reasoning, or which override rule fired).

**Mechanism:** a dedicated Gmail account sends the emails via Gmail's own SMTP/API — no inbound reachability needed. The approve/reject tap opens a one-tap confirm page rather than firing on a bare link (bare GET links risk being auto-triggered by email security scanners before the user opens the email). That page is reached via a Cloudflare Tunnel — chosen over Tailscale so it opens straight from Gmail in a normal browser with no app install. Requires a domain the user controls (not yet owned) and a token-protected link, since the endpoint is public.

Planning stage — no code yet. See `../CLAUDE.md`.
