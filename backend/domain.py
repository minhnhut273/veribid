"""Typed VeriBid domain contracts and invariant checks.

These models are the boundary between extraction/agent adapters and persisted
domain/API data. Provider-specific payloads must be converted here first.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def ddb_safe(value: Any) -> Any:
    """Convert JSON-shaped model data to values accepted by DynamoDB's serializer."""
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: ddb_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [ddb_safe(item) for item in value]
    return value


class EvaluationState(StrEnum):
    SATISFIED = "SATISFIED"
    PARTIALLY_SATISFIED = "PARTIALLY_SATISFIED"
    NOT_SATISFIED = "NOT_SATISFIED"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class RequirementCategory(StrEnum):
    TECHNICAL = "TECHNICAL"
    COMMERCIAL = "COMMERCIAL"
    COMPLIANCE = "COMPLIANCE"


class EvaluationType(StrEnum):
    SEMANTIC = "SEMANTIC"
    BOOLEAN = "BOOLEAN"
    NUMERIC = "NUMERIC"
    FORMULA = "FORMULA"


class ReviewAction(StrEnum):
    ACCEPT = "ACCEPT"
    OVERRIDE = "OVERRIDE"
    REQUEST_FOLLOWUP = "REQUEST_FOLLOWUP"


class ReviewStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FOLLOWUP_REQUESTED = "FOLLOWUP_REQUESTED"


class DocumentRole(StrEnum):
    BUYER_RFP = "BUYER_RFP"
    BUYER_RUBRIC = "BUYER_RUBRIC"
    BUYER_POLICY = "BUYER_POLICY"
    VENDOR_PROPOSAL = "VENDOR_PROPOSAL"
    VENDOR_PRICING = "VENDOR_PRICING"
    VENDOR_APPENDIX = "VENDOR_APPENDIX"


class IngestionStatus(StrEnum):
    AWAITING_UPLOAD = "AWAITING_UPLOAD"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class RunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"


class SourcePointer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_pointer_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    document_name: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)
    section: str | None = None
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    sheet_name: str | None = None
    row_start: int | None = Field(default=None, ge=1)
    row_end: int | None = Field(default=None, ge=1)
    chunk_id: str | None = None
    content_hash: str | None = None
    resolvable: bool = True


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requirement_id: str = Field(min_length=1)
    requirement_code: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: RequirementCategory
    mandatory: bool
    is_disqualifying: bool
    weight: float = Field(ge=0)
    evaluation_type: EvaluationType
    threshold: float | None = None
    source_pointer: SourcePointer
    validation_status: Literal["VALID", "INVALID"]


class EvidenceClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_claim_id: str = Field(min_length=1)
    claim_text: str = Field(min_length=1)
    relation: Literal["supports", "contradicts", "neutral"]
    confidence: float = Field(ge=0, le=1)
    source_pointer: SourcePointer

    @model_validator(mode="after")
    def must_be_resolvable(self) -> "EvidenceClaim":
        if not self.source_pointer.resolvable:
            raise ValueError("evidence claims require resolvable SourcePointers")
        return self


class ConflictPair(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    supporting_claim_id: str = Field(min_length=1)
    contradicting_claim_id: str = Field(min_length=1)
    conflict_type: str = Field(min_length=1)
    resolution_status: Literal["UNRESOLVED", "RESOLVED"]


class DeterministicResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool: str = Field(min_length=1)
    input: dict[str, Any]
    passed: bool | None = None
    authoritative_state: EvaluationState | None = None
    result: dict[str, Any] | None = None


class HumanReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    human_review_id: str = Field(min_length=1)
    evaluation_result_id: str = Field(min_length=1)
    action: ReviewAction
    system_state: EvaluationState
    system_score: float | None = Field(default=None, ge=0)
    final_state: EvaluationState | None = None
    final_score: float | None = Field(default=None, ge=0)
    rationale: str | None = None
    reviewed_at: datetime
    reviewer_sub: str = Field(min_length=1)

    @model_validator(mode="after")
    def enforce_action_contract(self) -> "HumanReview":
        if self.action is ReviewAction.OVERRIDE:
            if not self.rationale or not self.rationale.strip():
                raise ValueError("OVERRIDE requires rationale")
            if self.final_state is None or self.final_score is None:
                raise ValueError("OVERRIDE requires final_state and final_score")
        if self.action is ReviewAction.ACCEPT and self.final_state is not None:
            raise ValueError("ACCEPT does not replace the system suggestion")
        if self.action is ReviewAction.REQUEST_FOLLOWUP and self.final_state is not None:
            raise ValueError("REQUEST_FOLLOWUP cannot silently finalize a result")
        return self


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    audit_event_id: str = Field(min_length=1)
    aggregate_type: str = Field(min_length=1)
    aggregate_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    actor_sub: str = Field(min_length=1)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any]


class EvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_result_id: str = Field(min_length=1)
    requirement_id: str = Field(min_length=1)
    vendor_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    state: EvaluationState
    suggested_score: float | None = Field(default=None, ge=0)
    max_score: float = Field(ge=0)
    rationale: str = Field(min_length=1)
    evidence_claims: tuple[EvidenceClaim, ...] = ()
    conflict_pairs: tuple[ConflictPair, ...] = ()
    deterministic_result: DeterministicResult | None = None
    human_review: HumanReview | None = None

    @model_validator(mode="after")
    def enforce_evidence_and_history(self) -> "EvaluationResult":
        if self.state is EvaluationState.CONFLICTING_EVIDENCE and not self.conflict_pairs:
            raise ValueError("CONFLICTING_EVIDENCE requires explicit conflict_pairs")
        if self.state is not EvaluationState.INSUFFICIENT_EVIDENCE and not self.evidence_claims and self.deterministic_result is None:
            raise ValueError("visible factual states require evidence claims or a deterministic result")
        if self.deterministic_result and self.deterministic_result.authoritative_state:
            if self.deterministic_result.authoritative_state is not self.state:
                raise ValueError("deterministic authoritative_state must remain authoritative")
        if self.human_review and self.human_review.system_state is not self.state:
            raise ValueError("human review must preserve the original system suggestion")
        return self


class SchemaExecutionFailure(RuntimeError):
    """Typed model/schema failure; never convert this into insufficient evidence."""


def validate_with_one_repair(payload: Any, model: type[BaseModel], repair: Callable[[Any], Any] | None = None) -> BaseModel:
    """Validate once, allow one bounded repair, then fail closed."""
    try:
        return model.model_validate(payload)
    except Exception as first_error:
        if repair is None:
            raise SchemaExecutionFailure("typed output validation failed") from first_error
        try:
            return model.model_validate(repair(payload))
        except Exception as second_error:
            raise SchemaExecutionFailure("typed output validation failed after one repair") from second_error


def ensure_vendor_scope(vendor_id: str | None, proposal_id: str | None, expected_vendor_id: str | None, expected_proposal_id: str | None) -> None:
    """Reject partial or cross-proposal scope before retrieval/evaluation."""
    if (vendor_id is None) != (proposal_id is None):
        raise ValueError("vendor_id and proposal_id must be supplied together")
    if vendor_id != expected_vendor_id or proposal_id != expected_proposal_id:
        raise PermissionError("VENDOR_SCOPE_VIOLATION")
