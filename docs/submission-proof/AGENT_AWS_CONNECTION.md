# Agent-to-AWS Connection Proof

Status: PARTIAL — foundation evidence captured; refresh and final acceptance pending

This artifact contains only executed, non-secret evidence.

## Executed evidence

- Coding agent: Codex desktop, repository `D:\DOWNLOAD\01_Workspace\VeriBid`.
- Region/profile used: `us-east-1` / `my-aws`.
- AWS CLI version check: AWS CLI 2.36.30 was present.
- Foundation operations previously completed: CDK bootstrap, `VeriBidStack`
  deployment, Amplify manual deployment job 3, and public API/UI checks.
- Public checks executed again on 2026-09-23:
  - `GET https://jzmjnr4tq4.execute-api.us-east-1.amazonaws.com/api/v1/health`
    returned HTTP 200 and `status=ok`.
  - `GET https://jzmjnr4tq4.execute-api.us-east-1.amazonaws.com/api/v1/demo`
    returned HTTP 200 with three vendors and a seeded conflict.
  - `GET https://main.d2jw7e2fbiu6od.amplifyapp.com/` returned HTTP 200.
- GitHub Actions verified commit `2c0f751` and `f9ebe86` successfully; the
  current Amplify rewrite fix is pushed as `cab2e21` ancestry with `7ef8252`.

## Current blocker

`aws sts get-caller-identity --profile my-aws --region us-east-1` now returns
`Your session has expired. Please reauthenticate using 'aws login'.` No secret,
token or session value is recorded here. After the owner confirms and completes
`aws login --profile my-aws`, verify caller identity and CloudFormation before
redeploying; then capture authenticated workspace/upload/evaluation/review/
export proof and a real Bedrock cache benchmark.
