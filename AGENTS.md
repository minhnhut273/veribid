# VeriBid Repository Constitution

## Project Identity

VeriBid is an Evidence-Driven Bid Evaluation Engine. The MVP workflow is:

Upload -> Verify -> Human Review -> Defensible Export

VeriBid is not a generic procurement platform or generic AI chatbot. AI assists evaluation; it must not autonomously award or select the winning vendor.

## Document Authority by Concern

Authoritative specifications are under `Document/Phase_1/` and its diagram subdirectories. Use the document that owns the concern:

- `VeriBid_Product_Brief_PRD.docx`: product scope, thesis, MVP non-goals.
- `VeriBid_Functional_Requirements_v0.1.docx`: application behavior and acceptance criteria.
- `VeriBid_Data_Evidence_Model.docx` plus `Diagram/Data_evidence/VeriBid_Data_Evidence_Model_Description.docx`: domain entities, evidence semantics, canonical states and historical integrity.
- `VeriBid_AI_Agent_Specification.docx`: specialist contracts, verifier behavior, abstention and structured model outputs.
- `Diagram/Agent_orchestration/VeriBid_Agent_Orchestration_v0.1.docx`: router/specialist/verifier topology and delegation boundaries.
- `VeriBid_API_Contract.docx`: public REST boundary, DTOs, HTTP semantics, async commands and idempotency.
- `Diagram/System_architecture/VeriBid_AWS_System_Architecture_v0.1.docx`: runtime/cloud architecture, infrastructure and IAM/service boundaries.
- `Diagram/User_flow/VeriBid_User_Flow.docx` and `Diagram/Main_Evaluation_Sequence/VeriBid_Main_Evaluation_Sequence_v0.1.docx`: user lifecycle and stage ordering.
- `VeriBid_Deployment_Test_Checklist.docx`: release gates, acceptance tests and submission proof.

When specifications disagree, identify the owning concern first and do not silently reconcile it. Block only when the discrepancy changes API, schema, persistence or runtime behavior; record minor documentation drift in the completion report. Known drift: Functional Requirements and API behavior require `is_disqualifying`, while the current Data + Evidence Model does not yet lock that field. The active API contract takes precedence until the data model is intentionally revised.

## Non-Negotiable Invariants

- Every user-visible factual AI assessment resolves to a `SourcePointer`; missing, non-responsive, ambiguous or unresolvable evidence is `INSUFFICIENT_EVIDENCE`.
- Every retrieval/evaluation operation preserves `vendor_id` and `proposal_id`; never cross-contaminate vendor or proposal evidence.
- Material source-backed contradictions are `CONFLICTING_EVIDENCE`; preserve both sides with explicit `conflict_pairs`.
- LLMs perform semantic reasoning and extraction. Deterministic code owns booleans, numeric thresholds, SLA comparison, TCO, formulas, totals and weighted scores.
- AI produces suggested state/score. Human Review owns final state/score. `OVERRIDE` requires rationale and never erases the original suggestion.
- Proposal, evaluation, review and audit history is append-only or versioned.
- Typed model validation precedes persistence. Allow at most one bounded repair attempt; a second failure fails closed. Execution/schema failure is not `INSUFFICIENT_EVIDENCE`.

## Architectural Baseline

Follow the current architecture documents. The baseline is frontend -> public API boundary -> asynchronous workflow -> semantic Bedrock path plus deterministic tool path -> Skeptical Verifier -> persisted verified results -> Human Review -> Defensible Export.

Do not introduce a second orchestration framework, dedicated vector database, AgentCore or other P2 infrastructure before the P0/P1 vertical slice is working and measured. Do not freeze physical DynamoDB PK/SK design here; preserve the logical Data + Evidence Model and document physical choices when implemented. The frontend consumes stable DTOs, never raw Bedrock/model payloads.

## Implementation Behavior

Prefer minimal surgical changes, concrete end-to-end vertical slices and existing project conventions. Do not perform unrelated refactors or add production dependencies without a concrete requirement. Long-running operations remain asynchronous under the active API contract, and retryable mutations remain idempotent where specified.

## AWS Tooling

AWS Agent Toolkit, AWS skills, MCP and AWS CLI are assumed to be configured already. Reuse existing tooling when needed; do not reinstall or duplicate it, and never commit credentials. Mention tooling only for authorization, permissions, errors or an explicit request.

## Testing and Completion

Run the smallest relevant tests, configured static/type/lint checks and the affected acceptance criterion. Inspect the diff and never claim an unexecuted check passed. Completion reports state files changed, behavior, commands/results, unresolved risk or spec drift, and the next blocker.

## Implementation and Shipping Mode

The repository is in implementation and shipping mode. The coding agent is authorized to implement application code, tests, infrastructure as code, CI/CD, AWS deployment, production validation, Git commits, and GitHub pushes required to ship the documented VeriBid MVP.

Do not use this section to expand product scope beyond the authoritative MVP contracts.

## Repository-Local Agent Harness

- Treat `AGENTS.md`, `.agents/SOURCES.md`, `skills-lock.json` and the authoritative files under `Document/Phase_1/` as the agent's local operating contract.
- Before changing the harness, run `python scripts/check_agent_harness.py` from the repository root. The check is standard-library-only and must remain runnable before an application package exists.
- Preserve the project-local skill bundle. Use `scripts/setup-agent-skills.sh` only when a skill is missing; it must not install AWS tooling, credentials or global dependencies.
- Record harness adoption and verification in `docs/harness/adoption-report.md`. Record a new failure under `docs/failures/` only when it is repository-relevant, user-visible or likely to recur, and include its detection/prevention point.
- Keep the product roadmap in `docs/implementation/` synchronized with the implementation and deployment state.
