# VeriBid MVP Execution Plan

> Execution ledger: statuses below are evidence-backed implementation state.

## Goal

Ship the contract-first VeriBid MVP as a real AWS-hosted application with a public read-only demo, authenticated workspace workflow, evidence-grounded evaluation, Human Review, deterministic export, tested deployment, and submission proof.

## Milestones

| ID | Milestone | Exit evidence | Status |
|---|---|---|---|
| M0 | Repository and infrastructure foundation | GitHub remote, CI skeleton, IaC project, implementation ledger | PASS — GitHub + CDK foundation |
| M1 | Public frontend, API health, deployment foundation | HTTPS Amplify URL and API health route | PASS — live Amplify + API health/demo |
| M2 | Cognito and Evaluation Workspace | Authenticated workspace creation and persistence | IN_PROGRESS — JWT routes and DDB persistence deployed |
| M3 | Two-phase upload and ingestion | Private S3 upload, complete-upload verification, PDF/DOCX/XLSX metadata | IN_PROGRESS — presigned + HEAD verification deployed |
| M4 | Requirement extraction and SourcePointers | Atomic typed requirements with buyer provenance | NOT_STARTED |
| M5 | Vendor-scoped retrieval | Isolation tests for `vendor_id + proposal_id` | NOT_STARTED |
| M6 | Specialists and deterministic tools | Technical/Commercial/Compliance routing and fixture calculations | NOT_STARTED |
| M7 | Skeptical Verifier | Grounding, abstention, conflict-pair and schema-failure tests | NOT_STARTED |
| M8 | Evidence Matrix | 3-vendor matrix and result detail UI | NOT_STARTED |
| M9 | Human Review | Accept/override/follow-up with immutable system suggestion | NOT_STARTED |
| M10 | Audit export | Markdown and PDF export from human-confirmed data | NOT_STARTED |
| M11 | Prompt caching telemetry | Controlled cold/warm benchmark with actual cache-read telemetry | NOT_STARTED |
| M12 | Security, reliability and accessibility | Security review, error handling, accessibility checks | NOT_STARTED |
| M13 | Full E2E and release acceptance | P0/P1 checklist evidence | NOT_STARTED |
| M14 | GitHub, production and submission proof | Pushed commit, live URLs, proof package and submission draft | NOT_STARTED |

## Ordering rules

P0 ship-gate work and the complete P1 vertical slice precede P2 polish. The physical DynamoDB layout, parser choices, IaC mechanism, retrieval method and Bedrock model are recorded in `DECISIONS.md`; they do not alter the authoritative logical contracts.
