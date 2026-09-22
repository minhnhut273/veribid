---
name: veribid-release-proof
description: Perform VeriBid release validation, P0/P1 acceptance testing, E2E checks, deployment verification, or hackathon proof capture. Do not use for ordinary feature implementation or speculative screenshots.
---

# VeriBid Release Proof

Use `Document/Phase_1/VeriBid_Deployment_Test_Checklist.docx` as the release authority. Verify the actual deployed behavior and record only commands, tests and artifacts that were executed.

Coordinate browser E2E through the official Playwright workflow when it is installed, backend tests, and Git/GitHub inspection when useful. Store proof under `docs/submission-proof/`.

The P0/P1 proof must cover the live public URL and agent-to-AWS connection, two-phase isolated ingestion, grounded SourcePointers, vendor isolation, seeded `CONFLICTING_EVIDENCE` with explicit `conflict_pairs`, `INSUFFICIENT_EVIDENCE`, deterministic fixtures, bounded schema repair/fail-closed behavior, HumanReview accept/override, preserved suggestions, append-only AuditEvent history, and Markdown/PDF export traceability.

Never capture or publish secrets, JWTs, AWS keys, complete presigned URLs, account identifiers unless needed, or confidential raw vendor data. Do not fabricate screenshots, measured cache telemetry, test results or deployment proof.
