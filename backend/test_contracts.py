import pytest

from backend.deterministic import numeric_threshold_check, tco_calculator
from backend.domain import (
    EvaluationResult,
    EvaluationState,
    EvidenceClaim,
    HumanReview,
    ReviewAction,
    SchemaExecutionFailure,
    SourcePointer,
    validate_with_one_repair,
)
from backend.verifier import new_conflict_pair, verify_candidate


def pointer(name: str = "proposal.pdf") -> SourcePointer:
    return SourcePointer(
        source_pointer_id="PTR_01",
        document_id="DOC_01",
        document_name=name,
        document_type="PDF",
        page_number=3,
        section="SLA",
        resolvable=True,
    )


def claim(claim_id: str = "EVC_01", relation: str = "supports") -> EvidenceClaim:
    return EvidenceClaim(
        evidence_claim_id=claim_id,
        claim_text="Availability is committed in the proposal.",
        relation=relation,
        confidence=0.92,
        source_pointer=pointer(),
    )


def test_threshold_and_tco_are_deterministic():
    threshold = numeric_threshold_check(operator=">=", required_value=99.99, actual_value=99.90, unit="%")
    assert threshold.authoritative_state is EvaluationState.NOT_SATISFIED
    tco = tco_calculator(annual_license=120000, implementation_fee=40000, support_per_year=15000, contract_years=3)
    assert tco.result == {"tco": 445000.0, "currency": "USD"}


def test_verifier_abstains_without_resolvable_evidence():
    result = verify_candidate(
        evaluation_result_id="EVAL_01", requirement_id="REQ_01", vendor_id="VEN_A", proposal_id="PROP_A",
        suggested_state=EvaluationState.SATISFIED, suggested_score=9, max_score=10,
        rationale="The model found no source-backed claim.", claims=[],
    )
    assert result.state is EvaluationState.INSUFFICIENT_EVIDENCE


def test_verifier_preserves_conflict_pairs():
    pair = new_conflict_pair("EVC_01", "EVC_02", "DATA_RESIDENCY")
    result = verify_candidate(
        evaluation_result_id="EVAL_01", requirement_id="REQ_01", vendor_id="VEN_A", proposal_id="PROP_A",
        suggested_state=EvaluationState.SATISFIED, suggested_score=8, max_score=10,
        rationale="Two source-backed statements disagree.", claims=[claim("EVC_01"), claim("EVC_02", "contradicts")],
        conflict_pairs=[pair],
    )
    assert result.state is EvaluationState.CONFLICTING_EVIDENCE
    assert result.conflict_pairs[0].supporting_claim_id == "EVC_01"


def test_override_requires_rationale_and_preserves_system_suggestion():
    with pytest.raises(ValueError, match="OVERRIDE requires rationale"):
        HumanReview(
            human_review_id="REV_01", evaluation_result_id="EVAL_01", action=ReviewAction.OVERRIDE,
            system_state=EvaluationState.CONFLICTING_EVIDENCE, system_score=4,
            final_state=EvaluationState.PARTIALLY_SATISFIED, final_score=6,
            reviewer_sub="USER_01", reviewed_at="2026-09-23T00:00:00Z",
        )
    review = HumanReview(
        human_review_id="REV_01", evaluation_result_id="EVAL_01", action=ReviewAction.OVERRIDE,
        system_state=EvaluationState.CONFLICTING_EVIDENCE, system_score=4,
        final_state=EvaluationState.PARTIALLY_SATISFIED, final_score=6,
        rationale="Reviewer verified the exception scope.", reviewer_sub="USER_01", reviewed_at="2026-09-23T00:00:00Z",
    )
    assert review.system_state is EvaluationState.CONFLICTING_EVIDENCE


def test_schema_repair_is_bounded_and_not_insufficient_evidence():
    payload = {"requirement_id": "REQ_01"}
    repaired = validate_with_one_repair(payload, SourcePointer, lambda _: {
        "source_pointer_id": "PTR_01", "document_id": "DOC_01", "document_name": "RFP.pdf", "document_type": "PDF",
    })
    assert repaired.source_pointer_id == "PTR_01"
    with pytest.raises(SchemaExecutionFailure):
        validate_with_one_repair(payload, SourcePointer, lambda _: {"still": "invalid"})
