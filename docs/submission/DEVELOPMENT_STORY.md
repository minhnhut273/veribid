# VeriBid development story

The implementation moved from a repository-local agent setup into product and
shipping mode. The first vertical slice established a public Amplify URL,
API health/demo routes, Cognito, private S3, DynamoDB and a Step Functions
worker through CDK.

The domain layer was then made contract-first: Pydantic models enforce
SourcePointers, conflict pairs, deterministic authority and Human Review
history. PDF/DOCX/XLSX parsers preserve practical page, paragraph and
sheet/row locators. Retrieval is intentionally bounded to `vendor_id` plus
`proposal_id`, avoiding an unmeasured vector database.

The worker now routes each requirement to exactly one explicit specialist,
uses deterministic code for thresholds and TCO, and sends only typed semantic
work to the Bedrock adapter. The verifier can abstain or preserve conflicts;
schema failure is not mislabeled as insufficient evidence. The API and UI
expose matrix/result detail, append-only reviews and evidence-trace exports.

Codex used the existing AWS CLI/CDK/GitHub tooling, verified the live public
foundation, and kept credentials and presigned URLs out of source and proof
artifacts. The remaining release work is live authenticated acceptance after
the expired AWS session is refreshed, followed by current-model Bedrock and
cache telemetry verification.
