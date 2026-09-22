# VeriBid Cost Notes

## Current deployed baseline

The live baseline uses pay-per-request DynamoDB, Lambda, HTTP API, S3, Cognito,
Step Functions Standard, and Amplify Hosting. No OpenSearch/vector database,
NAT gateway, EC2, or always-on container was provisioned.

The stack is intentionally small for MVP validation. AWS billing is the source
of truth; this file records architecture choices and must not be presented as a
measured bill until the account cost view is queried.

## Operational guardrails

- Keep S3 private, encrypted, versioned and protected from public access.
- Keep asynchronous runs bounded and record actual telemetry before making
  cache or latency claims.
- Recheck CloudWatch and Cost Explorer after a real acceptance run.
- The current deployment used the root identity and therefore remains a
  security/operations risk even if the resource footprint is small.
