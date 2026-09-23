# VeriBid Submission Proof

This directory contains evidence captured from the real deployed application and executed tests. Do not add credentials, JWTs, complete presigned URLs, AWS keys, confidential vendor documents, or fabricated screenshots.

Expected proof artifacts include the public URL, AWS-agent connection evidence, deployment status, seeded evidence matrix, SourcePointer resolution, contradiction, abstention, deterministic calculation, Human Review, audit trace, export, prompt-cache telemetry and CloudWatch correlation.

Proof status is tracked in `ACCEPTANCE_RESULTS.md` after each test is actually executed.

The final clean-go remediation inventory is recorded in `01_live_app.md`
through `19_builder_submission.md`. Each file states its evidence status and
keeps historical, local-only, unavailable and current live observations
separate. `UNKNOWN` means the underlying account/project state was not
observable; it is not a pass claim.
