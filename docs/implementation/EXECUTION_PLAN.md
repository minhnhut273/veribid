# VeriBid MVP Execution Plan

> Execution ledger: statuses below are evidence-backed implementation state.

## Goal

Ship the contract-first VeriBid MVP as a real AWS-hosted application with a public read-only demo, authenticated workspace workflow, evidence-grounded evaluation, Human Review, deterministic export, tested deployment, and submission proof.

## Milestones

| ID | Milestone | Exit evidence | Status |
|---|---|---|---|
| M0 | Repository and infrastructure foundation | GitHub remote, CI skeleton, IaC project, implementation ledger | PASS — GitHub + CDK foundation |
| M1 | Public frontend, API health, deployment foundation | HTTPS Amplify URL and API health route | PASS — live Amplify + API health/demo |
| M2 | Cognito and Evaluation Workspace | Authenticated workspace creation and persistence | IN_PROGRESS — JWT routes, DDB persistence and full workspace client implemented; live auth acceptance pending credential refresh |
| M3 | Two-phase upload and ingestion | Private S3 upload, complete-upload verification, PDF/DOCX/XLSX metadata | IN_PROGRESS — presigned + HEAD verification and worker parser path implemented; live upload acceptance pending |
| M4 | Requirement extraction and SourcePointers | Atomic typed requirements with buyer provenance | PASS (local) — typed models, parser locators and worker extraction path |
| M5 | Vendor-scoped retrieval | Isolation tests for `vendor_id + proposal_id` | PASS — parser/domain scope guards |
| M6 | Specialists and deterministic tools | Technical/Commercial/Compliance routing and fixture calculations | PASS (local) — explicit category router, authoritative threshold/TCO tools and worker integration |
| M7 | Skeptical Verifier | Grounding, abstention, conflict-pair and schema-failure tests | PASS — 10 backend tests |
| M8 | Evidence Matrix | 3-vendor matrix and result detail UI | PASS (local) — authenticated matrix/result DTOs and production UI path |
| M9 | Human Review | Accept/override/follow-up with immutable system suggestion | PASS (local) — append-only review/audit path and UI controls |
| M10 | Audit export | Markdown and PDF export from human-confirmed data | PASS (local) — evidence-trace Markdown and dependency-free PDF payload |
| M11 | Prompt caching telemetry | Controlled cold/warm benchmark with actual cache-read telemetry | NOT_STARTED |
| M12 | Security, reliability and accessibility | Security review, error handling, accessibility checks | NOT_STARTED |
| M13 | Full E2E and release acceptance | P0/P1 checklist evidence | NOT_STARTED |
| M14 | GitHub, production and submission proof | Pushed commit, live URLs, proof package and submission draft | IN_PROGRESS — GitHub and foundation URL are live; final authenticated proof remains |

## Ordering rules

P0 ship-gate work and the complete P1 vertical slice precede P2 polish. The physical DynamoDB layout, parser choices, IaC mechanism, retrieval method and Bedrock model are recorded in `DECISIONS.md`; they do not alter the authoritative logical contracts.
