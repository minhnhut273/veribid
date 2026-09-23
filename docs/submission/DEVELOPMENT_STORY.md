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
artifacts. The final remediation added a dedicated non-root deployment
profile, expanded the result-detail trace, and made conflict pairs explicit in
Markdown/PDF export. CI synthesized a production-context CDK assembly and the
non-root deployment updated the backend; Amplify job 6 then deployed the
configured frontend. A fresh authenticated synthetic replay
(`EVL_4f323aba9796446f`, Step Functions run
`RUN_d35820c4850d472f`) verified conflict, abstention, deterministic evidence,
Human Review and READY export records. Docker Desktop remains unavailable for
local CDK asset bundling, so local direct synth is still an environment
failure; CI is the recorded synth/deployment handoff.
