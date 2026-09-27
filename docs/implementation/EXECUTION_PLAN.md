# VeriBid MVP Execution Plan

> Execution ledger: statuses below are evidence-backed implementation state.

## Goal

Ship the contract-first VeriBid MVP as a real AWS-hosted application with a public read-only demo, authenticated workspace workflow, evidence-grounded evaluation, Human Review, deterministic export, tested deployment, and submission proof.

## Milestones

| ID | Milestone | Exit evidence | Status |
|---|---|---|---|
| M0 | Repository and infrastructure foundation | GitHub remote, CI skeleton, IaC project, implementation ledger | PASS — GitHub + CDK foundation |
| M1 | Public frontend, API health, deployment foundation | HTTPS Amplify URL and API health route | PASS — live Amplify + API health/demo |
| M2 | Cognito and Evaluation Workspace | Authenticated workspace creation and persistence | PASS — live browser creation verified 2026-09-27; API Gateway group-claim normalization and role refresh/retry fixed |
| M3 | Two-phase upload and ingestion | Private S3 upload, complete-upload verification, PDF/DOCX/XLSX metadata | PASS — live DOCX uploads, S3 verification and worker ingestion succeeded |
| M4 | Requirement extraction and SourcePointers | Atomic typed requirements with buyer provenance | PASS — live typed requirements with buyer SourcePointers |
| M5 | Vendor-scoped retrieval | Isolation tests for `vendor_id + proposal_id` | PASS — parser/domain scope guards |
| M6 | Specialists and deterministic tools | Technical/Commercial/Compliance routing and fixture calculations | PASS — live Commercial/Compliance specialist routing and deterministic abstention |
| M7 | Skeptical Verifier | Grounding, abstention, conflict-pair and schema-failure tests | PASS — 10 backend tests |
| M8 | Evidence Matrix | 3-vendor matrix and result detail UI | PASS — live authenticated matrix/result detail with source evidence |
| M9 | Human Review | Accept/override/follow-up with immutable system suggestion | PASS — live ACCEPT review and audit trace |
| M10 | Audit export | Markdown and PDF export from human-confirmed data | PASS — live READY Markdown/PDF exports |
| M11 | Prompt caching telemetry | Controlled cold/warm benchmark with actual cache-read telemetry | PASS — Bedrock provider telemetry confirmed 4,801-token warm read |
| M12 | Security, reliability and accessibility | Security review, error handling, accessibility checks | PASS with INFO risk — static review, dependency audit, public browser check and root-identity risk recorded |
| M13 | Full E2E and release acceptance | P0/P1 checklist evidence | PASS — live 5-document/3-vendor production workflow, review/export proof, Bedrock telemetry and cache evidence |
| M14 | GitHub, production and submission proof | Pushed commit, live URLs, proof package and submission draft | PASS — commits `8bb01ad`, `6bbcb91`, `7e24e35` pushed and CI runs passed |

## Ordering rules

P0 ship-gate work and the complete P1 vertical slice precede P2 polish. The physical DynamoDB layout, parser choices, IaC mechanism, retrieval method and Bedrock model are recorded in `DECISIONS.md`; they do not alter the authoritative logical contracts.

## Plan alignment and Sprint 1

The execution plan is aligned to the current repository and deployed baseline:

- **IaC:** AWS CDK v2 TypeScript is the only infrastructure mechanism. Use `npm run build`, `cdk synth --strict`, `cdk diff`, and `cdk deploy`; do not introduce SAM or Serverless Framework files.
- **Bedrock:** keep Claude Sonnet 4.5 as the configured evaluator/verifier model. Prompt caching uses Bedrock Converse `cachePoint` and provider telemetry (`cache_read_input_tokens` / `cache_write_input_tokens`); do not add a DynamoDB `BedrockCache` table.
- **Runtime:** keep Lambda on Python 3.13 and CI on the compatible Python 3.12 lane unless a tested runtime change is explicitly approved.
- **Textract:** scanned-PDF/Textract remains outside the current MVP claim. A future integration may use Step Functions AWS SDK service integration, but Sprint 1 does not provision or claim it.

Sprint 1 is now the workspace authorization slice:

1. Provision Cognito groups `TenantAdmin`, `SourcingLead`, and `Auditor`, plus an immutable `custom:workspace_id` attribute and a V2 Pre Token Generation trigger that emits `workspace_id` in access tokens.
2. Require the token's `workspace_id` claim in protected API requests and persist it on evaluation aggregates and derived DynamoDB records. Workspace scope, not `owner_sub`, controls tenant visibility; `owner_sub` remains actor/audit metadata.
3. Allow `TenantAdmin` and `SourcingLead` to mutate evaluation workflows; keep `Auditor` read-only within its workspace.
4. Run the workspace authorization test script and CDK build/synth checks.
5. Normalize the API Gateway `cognito:groups` claim when it arrives as a serialized bracketed string, and retry a write once after a stale-role `403` using a refreshed access token.

Live follow-up on 2026-09-27: the API Gateway authorizer supplied `cognito:groups` as a serialized bracketed string. After the API parser fix and a user-authorized switch from `Auditor` to the least-privileged write role `SourcingLead`, the production browser created the `Cloud platform procurement` evaluation and loaded it as `DRAFT`.

Definition of Done: a synthesized stack contains all three groups and the workspace attribute; same-workspace users can read shared evaluation state; a different workspace receives `404`; an Auditor mutation receives `403`; and existing append-only review/audit semantics remain intact.
