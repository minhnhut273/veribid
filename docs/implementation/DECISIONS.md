# VeriBid Implementation Decisions

## D-001 IaC mechanism

Decision: use AWS CDK v2 with TypeScript as the single infrastructure-as-code mechanism.

Reason: the repository is starting without an IaC convention; CDK can define API Gateway, Lambda, Step Functions, S3, DynamoDB, Cognito, IAM, CloudWatch and Amplify-related outputs in one typed project. The CDK dependency will be project-local, not globally installed.

Status: proposed for M0; confirm with `cdk synth --strict` before deployment.

## D-002 Application split

Decision: use a Vite + React + TypeScript frontend and a Python Lambda domain/runtime layer behind API Gateway. The frontend consumes stable `/api/v1` DTOs and never raw model payloads.

Status: proposed; preserve if no existing application code is found.

## D-003 Persistence boundary

Decision: keep the logical Data + Evidence Model entities and access patterns authoritative. Choose the physical DynamoDB key layout only after the first domain repository implementation, and document it here before deployment.

Status: pending implementation.

## D-004 Retrieval boundary

Decision: begin with bounded per-proposal retrieval over normalized chunks and explicit `vendor_id + proposal_id` filtering. Do not add a dedicated vector database before benchmark evidence justifies P2 infrastructure.

Status: pending implementation.

## D-005 Bedrock model/API

Decision: do not hard-code a model or API from memory. Query current AWS documentation and verify account/model availability immediately before implementing the Bedrock adapter.

Status: pending AWS documentation check.
