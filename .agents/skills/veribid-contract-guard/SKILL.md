---
name: veribid-contract-guard
description: Guard changes to VeriBid domain entities, evidence, evaluation states, persistence, HumanReview, AuditEvent, or SourcePointer behavior. Do not trigger for unrelated UI, tooling, or documentation-only work.
---

# VeriBid Contract Guard

Use `Document/Phase_1/VeriBid_Data_Evidence_Model.docx` as the primary domain contract, then consult the Functional Requirements, API Contract and AI / Agent Specification for the affected behavior.

Before changing a contract-sensitive path:

1. Preserve `Requirement × Vendor × Proposal` scope on every retrieval, claim and result.
2. Require resolvable `SourcePointer` grounding for factual assessments.
3. Preserve `CONFLICTING_EVIDENCE` and explicit `conflict_pairs`; never average away material contradictions.
4. Preserve the five canonical `EvaluationState` values and their precedence over confidence.
5. Keep deterministic results authoritative for machine-evaluable calculations, while AI state/score remains suggested.
6. Keep HumanReview as final authority; require rationale for `OVERRIDE` and retain the original suggestion.
7. Keep proposal, evaluation, review and audit history append-only or versioned.
8. Validate typed output before persistence; permit at most one bounded repair and fail closed thereafter.
9. Check the known `is_disqualifying` alignment note before modifying Requirement or rule semantics.

Pair conceptually with `poka-yoke` when it is available to turn these invariants into deterministic checks. This skill guards implementation decisions; it does not implement product functionality by itself.
