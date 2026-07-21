# review_gate

Confidence-threshold + manual-override logic deciding auto-submit vs. route-to-human-review (permanent threshold, not a one-time trust ladder), plus outbound notifications for anything queued for review.

No dashboard. Notification is a push email fired immediately when something is routed to review, containing clickable approve/reject links the user acts on directly. If the user doesn't respond before the container instance's configured run-duration times out, the item defaults to reject — nothing gets submitted without explicit approval. Separately (not a review-gate concern specifically), each container instance also produces an end-of-run report summarizing everything it did, for the user to read at their own pace. Not yet decided: exact email content/format (how much of the generated package — resume, cover letter, filled form, fit-score reasoning — is shown), and the technical mechanism the approve/reject links hit.

Planning stage — no code yet. See `../CLAUDE.md`.
