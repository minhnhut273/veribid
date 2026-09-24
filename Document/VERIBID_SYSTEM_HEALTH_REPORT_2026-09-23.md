# VeriBid — System Health, Current State and Capability Report

**Report date:** 2026-09-23

**Live probe time:** 2026-09-23 16:49:58 ICT

**Assessment:** **CONDITIONAL GO — ready for controlled MVP demonstration and pilot use; not yet a clean unrestricted production rollout.**

## 1. Executive summary

VeriBid is currently a deployed AWS-backed MVP, not a localhost-only mock. The public frontend, public synthetic demo, health endpoint and protected API boundary are reachable. The deployed stack is `UPDATE_COMPLETE`, the latest Amplify deployment job is `SUCCEED`, and the documented authenticated synthetic workflow has completed the full path:

```text
Create Evaluation
  -> Upload RFP, rubric and vendor proposals
  -> Extract requirements
  -> Run asynchronous evaluation
  -> Evidence Matrix and result detail
  -> Human Review
  -> Markdown/PDF export
```

The system is suitable now for:

- showing the product to other people;
- controlled testing with synthetic or non-sensitive documents;
- demonstrating evidence grounding, conflict handling, abstention, deterministic calculations and Human Review;
- a bounded pilot where supported file formats and operational limits are understood.

It should not yet be described as a fully hardened production procurement platform. The most important boundaries are scanned/image PDF not being supported, fresh external-user registration not being re-tested in this report, limited current test tooling in the local environment, and the product remaining an evidence-driven evaluation assistant rather than an autonomous award system.

## 2. Current health dashboard

| Area | Current result | Evidence | Interpretation |
|---|---|---|---|
| Public frontend | PASS | Root URL returned HTTP 200 | The hosted application shell is reachable. |
| Public synthetic demo | PASS | `/demo` returned HTTP 200 and a seeded matrix | Read-only demo is available without login. |
| API health | PASS | `/api/v1/health` returned HTTP 200, `status=ok`, version `0.1.0` | API process and public route are responding. |
| Protected API boundary | PASS | Anonymous `POST /api/v1/evaluations` returned HTTP 401 | Protected operations require Cognito authentication. |
| CloudFormation stack | PASS | `VeriBidStack = UPDATE_COMPLETE` | Deployed infrastructure is in a completed update state. |
| Amplify frontend deployment | PASS | Latest inspected job `6 = SUCCEED` | Current frontend deployment completed successfully. |
| Repository harness | PASS | `python scripts/check_agent_harness.py` | Local agent harness is structurally valid; this check does not inspect AWS behavior. |
| Backend syntax | PASS | `python -m compileall -q backend` | Backend modules compile in the current Python environment. |
| Backend pytest rerun | NOT RUNNABLE | Current interpreter reports `No module named pytest` | Historical test evidence exists, but this report does not claim a fresh pytest pass. |
| Worktree | DIRTY, pre-existing | `docs/submission/assets/cover-ui-v1.png` was already untracked | This report did not modify or remove that asset. |

### Live endpoints

- Frontend: [VeriBid](https://main.d2jw7e2fbiu6od.amplifyapp.com/)
- Public demo: [Evidence demo](https://main.d2jw7e2fbiu6od.amplifyapp.com/demo)
- API health: [GET /api/v1/health](https://jzmjnr4tq4.execute-api.us-east-1.amazonaws.com/api/v1/health)

The public `/api/v1/demo` response currently contains a synthetic evaluation in `HUMAN_REVIEW` state with 3 vendors, 3 requirements and 9 matrix cells. It visibly exercises `SATISFIED`, `NOT_SATISFIED`, `CONFLICTING_EVIDENCE` and `INSUFFICIENT_EVIDENCE`. This is seeded demonstration data, not a claim about live supplier data.

## 3. What the system can currently do

### 3.1 Evaluation lifecycle

The API and worker support the following lifecycle:

1. Create an evaluation with idempotency support.
2. Initialize document uploads through presigned S3 URLs.
3. Validate that `vendor_id` and `proposal_id` are supplied together for vendor documents.
4. Verify that the uploaded object exists, is non-empty, is within the 25 MiB MVP limit and matches the initialized media type.
5. Ingest documents asynchronously through Step Functions and Lambda.
6. Extract typed buyer requirements.
7. Start an asynchronous evaluation run with optional vendor filtering.
8. Poll run status and telemetry.
9. Read an evidence matrix and click through to result detail.
10. Record Human Review.
11. Generate Markdown or PDF export records.

The API is intentionally asynchronous for ingestion, requirement extraction and evaluation. Retryable mutations use idempotency keys where defined by the contract.

### 3.2 Supported document formats

| Format | Current capability | Boundary |
|---|---|---|
| DOCX | Text paragraph extraction with document/source metadata | Locator is paragraph-oriented rather than a rich heading/anchor model. |
| Text PDF | Text extraction with page metadata | Image-only/scanned PDF is not supported. |
| XLSX | Workbook row extraction with sheet/row metadata | Exact cell-range semantics are limited. |
| Scanned/image PDF | NOT IMPLEMENTED | No Textract fallback is deployed in the MVP. |

### 3.3 Evidence and domain safeguards

The domain layer currently enforces:

- five canonical evaluation states: `SATISFIED`, `PARTIALLY_SATISFIED`, `NOT_SATISFIED`, `CONFLICTING_EVIDENCE` and `INSUFFICIENT_EVIDENCE`;
- factual `EvidenceClaim` objects with resolvable `SourcePointer` objects;
- vendor/proposal scope preservation;
- explicit `ConflictPair` records when material evidence conflicts;
- deterministic result records separate from semantic rationale;
- typed Pydantic validation before persistence;
- at most one bounded schema-repair attempt;
- schema or execution failure remaining a failure, rather than being mislabeled as insufficient evidence;
- append-only Human Review and audit records.

### 3.4 Evaluation capabilities

| Capability | Status | Current behavior |
|---|---|---|
| Technical threshold | IMPLEMENTED | Availability values are checked deterministically against the requirement threshold. |
| Commercial TCO | IMPLEMENTED | Annual license, implementation fee and annual support are calculated for 3 years, then compared with the buyer limit. |
| Compliance semantic review | IMPLEMENTED / BOUNDED | Source-backed claims are sent to Bedrock for typed semantic assessment when evidence exists and no conflict has already been detected. |
| Source grounding | IMPLEMENTED | Claims carry `SourcePointer` metadata and unresolved claims are rejected by the domain model. |
| Contradiction handling | IMPLEMENTED | Both supporting and contradicting claims are preserved with `conflict_pairs`. |
| Abstention | IMPLEMENTED | Missing evidence becomes `INSUFFICIENT_EVIDENCE`, not an invented answer. |
| Human Review | IMPLEMENTED | `ACCEPT` preserves the system result; `OVERRIDE` requires rationale, final state and final score. |
| Audit trace | IMPLEMENTED | Review and export events are persisted separately. The current UI shows the latest decision, not a complete timeline. |
| Defensible export | IMPLEMENTED WITH BOUNDARY | Markdown/PDF records include result and evidence trace; no browser-local downloaded-file artifact is claimed. |
| Autonomous award | NOT IMPLEMENTED BY DESIGN | VeriBid does not select or award a winning vendor automatically. |

## 4. Current agent/orchestration logic

The current implementation has one asynchronous workflow worker with explicit routing. It does not run three independent debating agents.

```text
Requirement × Vendor × Proposal
              |
              v
      Scope vendor/proposal chunks
              |
              v
           Router
       /      |       \
 Technical  Commercial  Compliance
    |          |            |
 threshold    TCO      source-backed claims
    |          |            |
    +----------+------------+
               |
               v
       Skeptical Verifier
               |
               v
       Persisted result
               |
               v
        Human Review
               |
               v
             Export
```

### Router

`route_requirement()` maps the requirement category to one of three explicit labels:

- `TECHNICAL_SPECIALIST`;
- `COMMERCIAL_SPECIALIST`;
- `COMPLIANCE_SPECIALIST`.

These labels preserve the intended topology and appear in result payloads. They are not currently separate deployable agents with separate memory, prompts or execution processes.

### Technical route

The worker extracts percentage values and delegates comparison to `numeric_threshold_check`. The deterministic result owns the authoritative state. The language model is not used to decide the numeric comparison.

### Commercial route

The worker extracts monetary values and delegates calculation and limit comparison to `tco_limit_check`. The arithmetic is deterministic and recorded as a `DeterministicResult`.

### Compliance route

The current MVP builds source claims from the scoped proposal chunks. EU/Europe language creates a supporting claim; US-processing language creates a contradicting claim. If both sides exist, the worker creates a `ConflictPair` and the verifier returns `CONFLICTING_EVIDENCE`. If claims exist without a conflict, Bedrock receives the typed requirement and vendor-scoped claims and returns a typed `state`, `score` and `rationale`.

### Verifier precedence

The current verifier resolves state in this order:

1. deterministic authoritative state, if present;
2. `CONFLICTING_EVIDENCE`, if explicit conflict pairs exist;
3. `INSUFFICIENT_EVIDENCE`, if no claims exist;
4. otherwise the specialist's suggested state.

This prevents semantic output from overriding deterministic arithmetic and prevents unsupported claims from becoming factual results.

### Bedrock and cache telemetry

The Bedrock adapter uses the Converse API with typed output validation. It supports one bounded repair attempt and records model invocation/token/cache telemetry. The stable buyer RFP/rubric/policy context is placed before the cache point; vendor evidence is request-scoped after it.

The separate cold/warm benchmark recorded provider cache write/read telemetry. The short production run recorded model invocations and token usage but is not counted as a production cache hit when provider cache-read fields were absent.

## 5. End-to-end acceptance evidence

The latest documented authenticated synthetic acceptance used:

- buyer RFP and buyer rubric;
- Vendor A, Vendor B and Vendor C proposals;
- 3 typed requirements;
- 9 result cells;
- Step Functions execution `RUN_d35820c4850d472f`;
- evaluation `EVL_4f323aba9796446f`;
- final evaluation state `READY_FOR_REVIEW` before review actions.

Observed behaviors:

- Vendor A preserved both sides of a residency conflict.
- Vendor B showed the deterministic availability threshold result.
- Vendor C abstained as `INSUFFICIENT_EVIDENCE`.
- `ACCEPT` succeeded.
- An `OVERRIDE` without rationale was rejected.
- A rationale-backed `OVERRIDE` succeeded while preserving the original system suggestion.
- Markdown and PDF export records reached `READY`.

This is strong evidence for the controlled synthetic MVP path. It is not evidence that arbitrary supplier documents, arbitrary requirement language or all PDF variants will work equally well.

## 6. Security and operational posture

### Positive controls currently present

- Cognito authentication is configured for the protected workspace/API path.
- Anonymous protected API access is rejected with HTTP 401.
- Upload storage is private and accessed through presigned URLs.
- Vendor and proposal identifiers are required as a pair and preserved through ingestion/evaluation.
- Review actions are tied to the authenticated reviewer subject.
- The current deployment path uses a dedicated non-root deployment identity; historical root usage remains documented as historical and should not be repeated.
- No credentials, JWTs, presigned URLs or raw supplier contents are included in this report.

### Operational boundaries

- The public demo is read-only synthetic data.
- Real supplier data should only be introduced after confirming retention, access, backup and incident-response policies.
- The local CDK asset-bundling path still depends on Docker Desktop's Linux engine; CI produced the deployable assembly used for the current deployment.
- Current local Python environment cannot rerun pytest because the package is absent.

## 7. Remaining risks and recommended next actions

| Priority | Action | Why it matters |
|---|---|---|
| P0 for unrestricted production | Add or explicitly prohibit scanned PDF ingestion; deploy OCR only after contract/security review | Current parser cannot read image-only proposals. |
| P0 for real users | Perform one fresh external Cognito sign-up/login and full non-sensitive evaluation | This report confirms the auth boundary, but not a new external user's complete journey. |
| P1 | Install/use the repository test environment and rerun backend, frontend and infrastructure checks | Current report has a fresh compile/harness pass but not a fresh pytest pass. |
| P1 | Add monitoring/alert ownership and retention policy for production operations | CloudWatch metrics exist, but operational ownership and response policy must be explicit before real procurement use. |
| P1 | Review supplier-data privacy, access control, retention and deletion behavior | Synthetic acceptance is not a privacy or compliance certification. |
| P1 | Expand prompt-cache benchmark beyond one cold/warm pair if latency/cost claims are required | One pair proves the mechanism, not a production-wide performance distribution. |
| P2 | Replace heuristic requirement/evidence extraction with broader typed extraction coverage | Current MVP patterns cover the synthetic slice, not every procurement document formulation. |
| P2 | Add a full audit timeline to the UI | Audit events are persisted, but the UI primarily shows the latest review decision. |

## 8. Commands and observations recorded for this report

The following checks were executed for this report on 2026-09-23:

```text
GET frontend root                         HTTP 200
GET frontend /demo                        HTTP 200
GET API /api/v1/health                    HTTP 200, status=ok, version=0.1.0
GET API /api/v1/demo                      HTTP 200, 3 vendors, 3 requirements, 9 cells
POST protected /api/v1/evaluations        HTTP 401 without authentication
CloudFormation VeriBidStack               UPDATE_COMPLETE
Amplify latest inspected job              job 6, SUCCEED
python scripts/check_agent_harness.py     PASS
python -m compileall -q backend           PASS
python -m pytest backend -q               NOT RUNNABLE: pytest is not installed
```

## 9. Final judgment

**Current health:** healthy enough for a controlled MVP demo and bounded pilot.

**Current capability:** the core evidence-driven evaluation vertical slice is implemented and deployed, including deterministic and semantic paths, verification, Human Review and export.

**Current readiness:** `CONDITIONAL GO`.

The honest product statement is:

> VeriBid is a deployed evidence-driven bid-evaluation MVP that other people can access and use in a controlled, authenticated workflow. It is not yet a fully hardened, unrestricted production procurement platform, and it does not autonomously award a vendor.

## 10. Source artifacts

- `AGENTS.md`
- `backend/worker.py`
- `backend/specialists.py`
- `backend/deterministic.py`
- `backend/verifier.py`
- `backend/domain.py`
- `backend/bedrock_adapter.py`
- `backend/api.py`
- `docs/implementation/STATUS.md`
- `docs/implementation/FINAL_READINESS_AUDIT.md`
- `Document/VERIBID_COMPLETION_REPORT_2026-09-23.md`
- `docs/submission-proof/ACCEPTANCE_RESULTS.md`
- `docs/submission-proof/SECURITY_REVIEW.md`

