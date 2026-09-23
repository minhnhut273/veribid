# VeriBid MVP Execution Plan

> Execution ledger: statuses below are evidence-backed implementation state.

## Goal

Ship the contract-first VeriBid MVP as a real AWS-hosted application with a public read-only demo, authenticated workspace workflow, evidence-grounded evaluation, Human Review, deterministic export, tested deployment, and submission proof.

## Milestones

| ID | Milestone | Exit evidence | Status |
|---|---|---|---|
| M0 | Repository and infrastructure foundation | GitHub remote, CI skeleton, IaC project, implementation ledger | PASS — GitHub + CDK foundation |
| M1 | Public frontend, API health, deployment foundation | HTTPS Amplify URL and API health route | PASS — live Amplify + API health/demo |
| M2 | Cognito and Evaluation Workspace | Authenticated workspace creation and persistence | PASS — live synthetic Cognito workspace creation and owner-scoped persistence |
| M3 | Two-phase upload and ingestion | Private S3 upload, complete-upload verification, PDF/DOCX/XLSX metadata | PASS — live DOCX uploads, S3 verification and worker ingestion succeeded |
| M4 | Requirement extraction and SourcePointers | Atomic typed requirements with buyer provenance | PASS — live typed requirements with buyer SourcePointers |
| M5 | Vendor-scoped retrieval | Isolation tests for `vendor_id + proposal_id` | PASS — parser/domain scope guards |
| M6 | Specialists and deterministic tools | Technical/Commercial/Compliance routing and fixture calculations | PASS — live Commercial/Compliance specialist routing and deterministic abstention |
| M7 | Skeptical Verifier | Grounding, abstention, conflict-pair and schema-failure tests | PASS — 10 backend tests |
| M8 | Evidence Matrix | 3-vendor matrix and result detail UI | PASS — live authenticated matrix/result detail with source evidence |
| M9 | Human Review | Accept/override/follow-up with immutable system suggestion | PASS — live ACCEPT review and audit trace |
| M10 | Audit export | Markdown and PDF export from human-confirmed data | PASS — live READY Markdown/PDF exports |
| M11 | Prompt caching telemetry | Controlled cold/warm benchmark with actual cache-read telemetry | PASS — Bedrock provider telemetry confirmed 4,801-token warm read |
| M12 | Security, reliability and accessibility | Security review, error handling, accessibility checks | IN_PROGRESS — static security review pass; root identity and pip-audit remain INFO risks |
| M13 | Full E2E and release acceptance | P0/P1 checklist evidence | PASS — live public/authenticated vertical slice, review/export proof and cache evidence |
| M14 | GitHub, production and submission proof | Pushed commit, live URLs, proof package and submission draft | IN_PROGRESS — GitHub and foundation URL are live; final authenticated proof remains |

## Ordering rules

P0 ship-gate work and the complete P1 vertical slice precede P2 polish. The physical DynamoDB layout, parser choices, IaC mechanism, retrieval method and Bedrock model are recorded in `DECISIONS.md`; they do not alter the authoritative logical contracts.
