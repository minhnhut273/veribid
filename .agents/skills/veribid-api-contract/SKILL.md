---
name: veribid-api-contract
description: Implement or review VeriBid /api/v1 handlers, DTOs, API Gateway/Lambda boundaries, async commands, idempotency, uploads, matrix/results, review, and export endpoints. Do not invent endpoints absent from the API Contract.
---

# VeriBid API Contract

Read `Document/Phase_1/VeriBid_API_Contract.docx` before changing the public boundary. Keep frontend types aligned to API DTOs, not database records or raw provider payloads.

Enforce:

- standard success, list and error envelopes;
- `202 Accepted` plus a pollable job/run/export resource for long-running extraction, evaluation, upload completion and export commands;
- `Idempotency-Key` and replay behavior for retryable mutations;
- the two-phase upload contract: initialize presigned transfer, then `complete-upload`; verify the S3 object before ingestion;
- vendor/proposal scope validation, including the paired `vendor_id` and `proposal_id` requirement;
- lightweight matrix responses and full evidence only from result detail;
- separate `deterministic_result` from model rationale and preserve actual runtime telemetry;
- `OVERRIDE` rationale, immutable system suggestion, and append-only HumanReview/AuditEvent history;
- frontend isolation from raw Bedrock, Step Functions and other internal orchestration payloads.

If a needed endpoint or field is absent from the contract, report the proposal and its contract owner before inventing a REST shape.
