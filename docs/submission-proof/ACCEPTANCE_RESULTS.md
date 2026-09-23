# VeriBid Acceptance Results

Status: PASS for hackathon MVP — public and authenticated production vertical
slice, Bedrock invocation telemetry, review, export and cache benchmark
evidence accepted; root deployment identity remains the single INFO hardening
risk.

Executed local evidence includes 22 backend tests, frontend build/test, CDK
build/synth, a live public health response, a live public demo response, and a
successful Amplify manual deployment. The contract path covers specialist
routing, append-only review/matrix final decisions, DynamoDB Decimal handling,
idempotent extraction retry, and dependency-free PDF export bytes.

Production browser verification initially found that the prior Amplify SPA
rewrite returned HTML for Vite asset URLs. The extension-aware rewrite fix was
deployed as Amplify manual deployment job 4; the asset now returns JavaScript,
the landing page shows `API connected`, and `/demo` renders the seeded matrix.

The live authenticated production proof used synthetic evaluation
`EVL_a777192bff2f4ac4`: five DOCX uploads (buyer RFP, buyer rubric and three
vendor proposals) were verified and scoped to `VENDOR_A/PROPOSAL_A`,
`VENDOR_B/PROPOSAL_B`, and `VENDOR_C/PROPOSAL_C`. Worker ingestion and
requirement extraction succeeded; `RUN_8ce16b2e2dcd4ff9` reached
`READY_FOR_REVIEW` with 9/9 result cells. The matrix preserved a Vendor A
contradiction, Vendor C insufficient evidence, deterministic TCO/availability
results and all three specialist labels. ACCEPT and rationale-backed OVERRIDE
reviews were appended with audit events, and clean Markdown/PDF exports were
stored READY. Failed pre-IAM retry records were removed before export
regeneration.

The worker emitted structured completion telemetry with two Bedrock model
invocations, 1,099 input tokens and 467 output tokens. CloudWatch metrics for
the live window reported one `RunCompleted` and two `ModelInvocations`; the
production cache fields were null for this short run, so the separate measured
cold/warm benchmark is the cache-hit proof.

The controlled prompt-cache benchmark is recorded in
`docs/submission-proof/CACHE_BENCHMARK.md`: the cold request wrote 4,801 input
tokens to cache and the warm request read the same 4,801 tokens from cache.

The pushed implementation commit `fed4986` passed GitHub Actions run
[`35807611863`](https://github.com/minhnhut273/veribid/actions/runs/35807611863)
with backend, frontend and infrastructure checks. The static security review
is recorded in `SECURITY_REVIEW.md`; it found no critical/high/medium code
finding and the Python dependency audit is clean. Least-privilege deployment
identity hardening remains the explicit INFO item.
