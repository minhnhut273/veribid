# VeriBid Implementation Status

## Current state

Status: IN_PROGRESS — product implementation and shipping mode.

Last verified: 2026-09-23

The repository-local agent environment is now switched to implementation and
shipping mode. The first deployed vertical slice includes CDK infrastructure,
private storage, Cognito, a public HTTP API, an Amplify-hosted frontend, and a
read-only synthetic demo. The deployed authenticated workflow now covers scoped
document upload, typed requirement extraction, explicit specialist routing,
evaluation polling, evidence matrix, result detail, Human Review, audit events,
and Markdown/PDF export. The Bedrock inference profile and prompt-cache path
are enabled in the production worker; the latest backend/IaC changes were
redeployed and accepted through a live synthetic Cognito workspace.

## Baseline evidence

- GitHub remote: `https://github.com/minhnhut273/veribid.git`.
- Foundation commit: `23bd86b`; first product implementation commit: `0cc9517`.
- Authoritative specifications: `Document/Phase_1/`.
- Project-local skills: `.agents/skills/`, with provenance in `.agents/SOURCES.md`
  and installer hashes in `skills-lock.json`.
- Agent harness check: `scripts/check_agent_harness.py`.
- `infra`: `npm run build` and `npm run synth` pass; stack `VeriBidStack` is
  deployed in `us-east-1` and is `UPDATE_COMPLETE`.
- Live API: `GET /api/v1/health` returned `status=ok`; `GET /api/v1/demo`
  returned three vendors, one conflict and two insufficient-evidence cells.
- Live Amplify: deployment job 4 succeeded. The Vite asset returned HTTP 200
  as `text/javascript` and contained `createRoot`; browser verification showed
  the landing page API connected and the read-only evidence matrix rendered.
- Live authenticated production acceptance: synthetic evaluation
  `EVL_a777192bff2f4ac4` completed with 5 DOCX documents (1 RFP, 1 rubric and
  3 vendor proposals), 3 typed requirements, 3 vendor/proposal scopes,
  `READY_FOR_REVIEW`, 9/9 result cells, all three specialist labels, a
  preserved Vendor A contradiction, Vendor C abstentions, deterministic
  TCO/availability checks, ACCEPT plus rationale-backed OVERRIDE reviews with
  audit trace, and READY Markdown/PDF exports. Failed IAM retry records were
  removed before the clean export proof, and the synthetic evaluation, S3
  objects and Cognito test user were deleted and verified absent afterward.
- Production Bedrock acceptance: worker run `RUN_8ce16b2e2dcd4ff9` completed
  with `model_invocations=2`, `input_tokens=1099`, and `output_tokens=467`;
  CloudWatch reported `RunCompleted=1` and `ModelInvocations=2` in the live
  verification window. The separate cold/warm benchmark proves provider cache
  write/read telemetry with 4,801 tokens.
- Local contract evidence: `22 passed` in `backend/`, including deterministic
  threshold/TCO, specialist routing, abstention, conflict pairs, OVERRIDE
  guard, bounded repair, vendor scope, source locators, append-only review,
  matrix final decisions, PDF export payload and the Bedrock semantic branch.

## Acceptance tracking

| Area | Status | Evidence / next action |
|---|---|---|
| Repository constitution | PASS | `AGENTS.md` inspected and kept as the local source of truth. |
| Project-local skill environment | PASS | `.agents/SOURCES.md`, `skills-lock.json` and setup script are present. |
| Harness drift check | PASS | `python scripts/check_agent_harness.py` passed after the local-vs-external lock distinction was corrected. |
| Product implementation | PASS for the deployed vertical slice | Live authenticated workflow reached evaluation, Human Review and export; Bedrock cache evidence is recorded separately. |
| AWS deployment / release proof | PASS for hackathon MVP | Public URL, API health/demo, authenticated production workflow, Bedrock run telemetry and export evidence are verified; root deployment identity remains an INFO hardening risk. |
| Contract/domain core | PASS | Pydantic domain models, deterministic tools, verifier, parsers, review and export paths are covered by 22 backend tests. |

## Blockers and risks

- The configured AWS identity is the account root identity. Keep this as a
  ship risk and do not expose credentials; production hardening needs a
  least-privilege deployment/runtime identity.
- Production Bedrock uses the verified Sonnet 4.5 global inference profile with
  prompt-cache support enabled. The benchmark's provider-reported cache hit is
  the authoritative cache evidence; the short controlled production run did
  not report cache read/write fields, so it is not counted as a production cache
  hit.

## Continuation

Commit and push the final worker/IAM/docs/fixture changes, run CI, then keep the
current live URLs, acceptance artifacts and cache benchmark as the release
record.
