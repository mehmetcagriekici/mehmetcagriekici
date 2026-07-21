# review_gate

Confidence-threshold + manual-override logic deciding auto-submit vs. route-to-human-review (permanent threshold, not a one-time trust ladder), plus outbound notifications for anything queued for review.

**Language: Python** — an internal module of the shared Python service (see tech stack in `../README.md`), not routed through Go.

No dashboard. Notification is a push email fired immediately when something is routed to review, containing clickable approve/reject links the user acts on directly. If the user doesn't respond before the container instance's configured run-duration times out, the item defaults to reject — nothing gets submitted without explicit approval. Separately (not a review-gate concern specifically), each container instance also produces an end-of-run report summarizing everything it did, for the user to read at their own pace.

**Email content:** full generated package shown inline in the email body — resume text, cover letter text, filled form field answers — not summarized, not attachments (attachments are phone friction; the driving concern is that missing a bad generation in a too-short email is worse than a long email). Also includes a log/report-style breakdown of why that specific application was routed to review (fit-score reasoning, or which manual-override rule fired) — not just a bare yes/no prompt. **Mechanism (decided):** sending uses a dedicated Gmail account created specifically for this app, via Gmail's own SMTP/API — needs no inbound reachability. The approve/reject tap opens a one-tap confirm page rather than firing on a bare link (bare GET links risk being auto-triggered by email security scanners/prefetchers before the user opens the email). That confirm page is reached via a **Cloudflare Tunnel** (chosen over Tailscale, which would require installing a VPN app on the phone — the goal is opening straight from Gmail in a normal browser). Requires a domain the user controls (~$10-15/year, not yet owned) and the link itself needs its own token-based protection, since the endpoint is genuinely public rather than gated by a private network.

Planning stage — no code yet. See `../CLAUDE.md`.
