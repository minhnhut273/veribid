"""Skeptical verification rules kept separate from specialist reasoning."""

from __future__ import annotations

from typing import Iterable
from uuid import uuid4

try:
    from .domain import ConflictPair, DeterministicResult, EvaluationResult, EvaluationState, EvidenceClaim
except ImportError:
    from domain import ConflictPair, DeterministicResult, EvaluationResult, EvaluationState, EvidenceClaim  # type: ignore


def verify_candidate(
    *,
    evaluation_result_id: str,
    requirement_id: str,
    vendor_id: str,
    proposal_id: str,
    suggested_state: EvaluationState,
    suggested_score: float | None,
    max_score: float,
    rationale: str,
    claims: Iterable[EvidenceClaim],
    conflict_pairs: Iterable[ConflictPair] = (),
    deterministic_result: DeterministicResult | None = None,
) -> EvaluationResult:
    """Ground, abstain, and preserve conflicts before returning a result."""
    claims_tuple = tuple(claims)
    conflicts_tuple = tuple(conflict_pairs)
    if deterministic_result and deterministic_result.authoritative_state:
        state = deterministic_result.authoritative_state
    elif conflicts_tuple:
        state = EvaluationState.CONFLICTING_EVIDENCE
    elif not claims_tuple:
        state = EvaluationState.INSUFFICIENT_EVIDENCE
    else:
        state = suggested_state
    return EvaluationResult(
        evaluation_result_id=evaluation_result_id,
        requirement_id=requirement_id,
        vendor_id=vendor_id,
        proposal_id=proposal_id,
        state=state,
        suggested_score=suggested_score,
        max_score=max_score,
        rationale=rationale,
        evidence_claims=claims_tuple,
        conflict_pairs=conflicts_tuple,
        deterministic_result=deterministic_result,
    )


def new_conflict_pair(supporting_claim_id: str, contradicting_claim_id: str, conflict_type: str) -> ConflictPair:
    return ConflictPair(
        supporting_claim_id=supporting_claim_id,
        contradicting_claim_id=contradicting_claim_id,
        conflict_type=conflict_type,
        resolution_status="UNRESOLVED",
    )
