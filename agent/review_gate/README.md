# review_gate

**Pipeline role: Application Controller.** Third stage of `Data -> Hybrid Search -> Application Generator -> Application Controller -> Application API`. A second LLM — distinct from `tailoring/`'s Generator — checks the Generator's output against `source_of_truth` (honesty: is every claim traceable to a real fact) and against the job posting (relevance: does the answer actually address what was asked). It isn't re-judging fit — `matching/` already decided that deterministically; this is QC on what the Generator produced.

Any failure on either check — no severity distinction between honesty and relevance — routes to human review. Passing both sends the application straight to `form_automation/` for submission. A user-maintained override list (always review certain roles/companies regardless of the check) applies independently on top of this.

**Language: Python** — internal module of the shared Python service, not routed through Go.

**Notification:** no dashboard. A push email fires immediately when something routes to review, with clickable approve/reject links. If the user doesn't respond before that instance's run times out, the item defaults to reject — nothing submits without explicit approval — but no exclusion is recorded, so the posting can come back in a later run with a fresh email. The same holds for a one-page overflow still unanswered at run end. A link tapped after its run has ended opens a page saying it expired and the posting will come back, rather than acting. An explicit reject (by the user, or the Controller's own failure verdict) writes a permanent exclusion record to `tracking/`, so that posting never comes back. Separately, each instance also produces an end-of-run report summarizing everything it did, for the user to read at their own pace.

**Email content:** the full generated package shown inline (resume text, cover letter text, filled form field answers) — not summarized, not attachments, since missing a bad generation in a too-short email is worse than a long one. Also includes a log/report-style breakdown of why that application was routed to review (the honesty/relevance verdict and reasoning, or which override rule fired).

**Mechanism:** a dedicated Gmail account sends the emails via Gmail's own SMTP/API — no inbound reachability needed. The approve/reject tap opens a one-tap confirm page rather than firing on a bare link (bare GET links risk being auto-triggered by email security scanners before the user opens the email). That page is reached via a Cloudflare Tunnel — chosen over Tailscale so it opens straight from Gmail in a normal browser with no app install. Requires a domain the user controls (not yet owned) and a token-protected link, since the endpoint is public.

## What live runs say the Controller must catch

Four live runs of `tailoring/` against local Ollama (2026-08-05 and 2026-09-30, 7B model) produced output that passed every structural check — valid JSON, schema-valid, one page — but was not honest. Fixed upstream since: invented company names (a context-window truncation), placeholder form-answer keys, visa/GPA gaps raised unasked (now decided in code). Still seen on the last 7B run, and exactly the Controller's job:
- **Upgraded claims:** "Go in production systems", "databases at scale", "Experienced backend engineer… proven track record" — against facts saying the Go API is in early bootstrap and gRPC "not yet started".
- **Dropped hedges:** "Kubernetes/EKS" listed plainly where every fact says experimental.
- **Misattribution:** a technology credited to a project whose fact doesn't list it.
- **Filler** despite being banned by name ("strong background", "I believe my skills align well").

The 14B live run (2026-10-07) fixed the misattribution and the "production"/"at scale" claims and described an early-stage project honestly, but still produced filler ("I am excited to apply", "passion"), an upgraded claim ("Experienced backend engineer"), an unsupported "frontend" claim echoing the posting's wording, and a phrasing-rule instruction from `known-gaps.json` copied into a letter. **Cost to plan for:** if the Controller is a second call on the same 14B, it adds roughly another ~15 minutes per application on top of ~45–60 for generation — still undecided whether it shares the model or uses a separate one.

Planning stage — no code yet. See `../CLAUDE.md`.
