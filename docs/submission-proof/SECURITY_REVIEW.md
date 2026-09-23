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
   the foundation deployment. This is a release-hardening risk outside the
   application code; replace it with a least-privilege deployment identity
   before handling real supplier documents.

No credentials, JWTs or complete presigned URLs are included in this artifact.
