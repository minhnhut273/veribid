# Agent-to-AWS Connection Proof

Status: CURRENT — authenticated deployment and production vertical-slice
acceptance captured

This artifact contains only executed, non-secret evidence.

## Executed evidence

- Coding agent: Codex desktop, repository `D:\DOWNLOAD\01_Workspace\VeriBid`.
- Region/profile used: `us-east-1` / `my-aws`.
- AWS CLI version check: AWS CLI 2.36.30 was present.
- Foundation operations completed: CDK bootstrap, `VeriBidStack` deployment in
  `us-east-1`, Amplify manual deployment job 4, and public API/UI checks.
- Public checks executed again on 2026-09-23:
  - `GET https://jzmjnr4tq4.execute-api.us-east-1.amazonaws.com/api/v1/health`
    returned HTTP 200 and `status=ok`.
  - `GET https://jzmjnr4tq4.execute-api.us-east-1.amazonaws.com/api/v1/demo`
    returned HTTP 200 with three vendors and a seeded conflict.
  - `GET https://main.d2jw7e2fbiu6od.amplifyapp.com/` returned HTTP 200.
- The deployed Vite asset returned HTTP 200 with `text/javascript` and the
  production browser rendered the landing page and read-only matrix.
- Authenticated production proof used a synthetic Cognito account and
  evaluation `EVL_a777192bff2f4ac4`; five DOCX documents (buyer RFP/rubric plus
  three vendor proposals) reached `READY_FOR_REVIEW` with 9/9 result cells,
  preserved conflict/insufficient states, ACCEPT and rationale-backed OVERRIDE
  reviews, and READY Markdown/PDF exports.
- Production worker Bedrock configuration was verified against the global
  Claude Sonnet 4.5 inference profile. Live run `RUN_8ce16b2e2dcd4ff9`
  completed with two model invocations; CloudWatch returned one
  `RunCompleted` and two `ModelInvocations` datapoints in the verification
  window. The provider cache benchmark is recorded separately.
- GitHub Actions verified commit `2c0f751` and `f9ebe86` successfully; the
  current Amplify rewrite fix is pushed as `cab2e21` ancestry with `7ef8252`.

## Remaining release risk

The current caller identity is the account root identity. No secret, token or
session value is recorded here. Replace it with a least-privilege deployment
identity before a non-hackathon release.
