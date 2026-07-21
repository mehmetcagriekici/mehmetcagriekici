# tracking

State store logging what was applied to, when, status, and the generated materials, to avoid duplicates and support follow-up. Storage format not yet decided.

Must be a single store **shared across all concurrently-running per-ATS container instances** (see deployment model in `../README.md`), reading and writing to the same place rather than keeping local per-instance state — otherwise two instances (e.g. a Greenhouse container and a Lever container running at the same time) could double-apply to the same company/role. This is a stronger requirement than `source_of_truth/`, which stays read-only and shared but is never written to by the pipeline.

Planning stage — no code yet. See `../CLAUDE.md`.
