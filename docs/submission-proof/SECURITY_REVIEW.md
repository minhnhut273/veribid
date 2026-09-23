# Security review report

| Severity | Count |
|---|---:|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 0 |
| INFO | 1 |
| **Total** | **1** |

Scan date: 2026-09-23. Scope: backend Python handlers/parsers/worker,
frontend React/TypeScript, CDK/IAM, CI and lockfiles. Dependency audit:
`npm audit --audit-level=high --omit=optional` returned zero vulnerabilities
for both frontend and infra. `pip-audit -r backend/requirements.txt` returned
no known vulnerabilities after upgrading `pypdf` to `6.16.1`; the updated
worker asset was redeployed successfully.

## Security controls verified

- API Gateway routes that mutate or read evaluation data use Cognito JWT
  authorization; each API lookup checks the authenticated subject against the
  evaluation owner before reading or mutating records.
- S3 is private, encrypted, versioned and blocked from public access. Presigned
  PUTs use a safe basename/object prefix, require the initialized content type,
  and are HEAD-verified before ingestion.
- S3 and API CORS are restricted to the configured Amplify origin; the API
  stage has bounded throttling (25 requests/second, burst 50).
- Lambda S3 permissions are limited to `evaluations/*`; the worker is read-only
  for objects. Uploads are capped at 25 MiB and DOCX XML parts at 10 MiB.
- React renders user/API values as text and does not use
  `dangerouslySetInnerHTML`; no shell execution, eval, raw SQL, or JWT decode
  path was found.
- Public health/demo routes are read-only and the demo uses synthetic data.

## INFO findings

1. The configured AWS deployment identity was the account root identity during
   the foundation deployment. This was a release-hardening risk outside the
   application code. Normal VeriBid deployment now uses the dedicated IAM
   user `veribid-deploy` through the local AWS profile of the same name; no
   root credentials were rotated, disabled or deleted.

## Deployment identity migration evidence

- Old condition: `aws sts get-caller-identity` returned the account root ARN
  before remediation.
- New principal: dedicated IAM user `veribid-deploy`, used through the local
  AWS profile `veribid-deploy`.
- Non-root verification: `aws --profile veribid-deploy sts get-caller-identity`
  returned `arn:aws:iam::<account>:user/veribid-deploy`, not
  `arn:aws:iam::<account>:root`.
- Permission rationale: the inline policy is limited to CloudFormation stack
  deployment/read operations, the CDK bootstrap asset bucket, the bootstrap
  version SSM parameter, `sts:GetCallerIdentity`, and `iam:PassRole` for the
  existing CDK CloudFormation execution role. It does not grant
  `AdministratorAccess` to the deployment user and does not permit stack
  deletion or termination-protection changes.
- Commands performed: caller identity verification; CloudFormation stack and
  resource inspection for `VeriBidStack`; public root, `/demo`, API health and
  anonymous protected-route probes. The stack remained `UPDATE_COMPLETE`.
- Deployment validation boundary: CDK TypeScript build passed. CDK synth/diff
  were not runnable because the local Docker Desktop Linux engine was not
  available for the existing Python Lambda asset bundling command.

No credentials, JWTs or complete presigned URLs are included in this artifact.
