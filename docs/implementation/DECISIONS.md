# VeriBid Implementation Decisions

> These decisions are active implementation choices and remain subordinate to
> the authoritative specifications under `Document/Phase_1/`.

## D-001 IaC mechanism

Decision: use AWS CDK v2 with TypeScript as the single infrastructure-as-code mechanism.

Reason: the repository is starting without an IaC convention; CDK can define API Gateway, Lambda, Step Functions, S3, DynamoDB, Cognito, IAM, CloudWatch and Amplify-related outputs in one typed project. The CDK dependency will be project-local, not globally installed.

Status: active; `npm run build` and strict synth passed, and the foundation was
deployed to `us-east-1`.

## D-002 Application split

Decision: use a Vite + React + TypeScript frontend and a Python Lambda domain/runtime layer behind API Gateway. The frontend consumes stable `/api/v1` DTOs and never raw model payloads.

Status: active; the frontend consumes stable DTOs and the Lambda boundary keeps
provider-specific payloads out of the API.

## D-003 Persistence boundary

Decision: keep the logical Data + Evidence Model entities and access patterns authoritative. Choose the physical DynamoDB key layout only after the first domain repository implementation, and document it here before deployment.

Status: active for the deployed slice. `pk=EVAL#{evaluation_id}` and typed
sort-key prefixes (`META`, `DOC#`, `CHK#`, `REQ#`, `JOB#`, `RUN#`, `RES#`,
`REV#`, `EXP#`) preserve aggregate locality while keeping review/audit records
append-only. This is an implementation choice, not a replacement for the
logical data model.

## D-004 Retrieval boundary

Decision: begin with bounded per-proposal retrieval over normalized chunks and explicit `vendor_id + proposal_id` filtering. Do not add a dedicated vector database before benchmark evidence justifies P2 infrastructure.

Status: active for the first slice: normalized chunks retain both `vendor_id`
and `proposal_id`, and every scoped operation validates the pair before use.
No vector database is provisioned.

## D-005 Bedrock model/API

Decision: do not hard-code a model or API from memory. Query current AWS documentation and verify account/model availability immediately before implementing the Bedrock adapter.

Status: pending AWS documentation/model availability check. No Bedrock model is
hard-coded yet; semantic specialist work must record the current model/API and
actual runtime telemetry before deployment.
