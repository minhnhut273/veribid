"""Authoritative deterministic tools for VeriBid scoring."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

try:
    from .domain import DeterministicResult, EvaluationState
except ImportError:
    from domain import DeterministicResult, EvaluationState  # type: ignore


def numeric_threshold_check(*, operator: str, required_value: float, actual_value: float, unit: str) -> DeterministicResult:
    """Compare numeric values in Decimal space; the result owns the state."""
    try:
        required = Decimal(str(required_value))
        actual = Decimal(str(actual_value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("threshold values must be numeric") from exc
    checks = {
        ">=": actual >= required,
        ">": actual > required,
        "<=": actual <= required,
        "<": actual < required,
        "==": actual == required,
    }
    if operator not in checks:
        raise ValueError(f"unsupported threshold operator: {operator}")
    passed = checks[operator]
    return DeterministicResult(
        tool="numeric_threshold_check",
        input={"operator": operator, "required_value": float(required), "actual_value": float(actual), "unit": unit},
        passed=passed,
        authoritative_state=EvaluationState.SATISFIED if passed else EvaluationState.NOT_SATISFIED,
    )


def tco_calculator(*, annual_license: float, implementation_fee: float, support_per_year: float, contract_years: int, currency: str = "USD") -> DeterministicResult:
    """Calculate total cost; never infer missing cost components."""
    if contract_years < 1:
        raise ValueError("contract_years must be positive")
    try:
        annual = Decimal(str(annual_license))
        implementation = Decimal(str(implementation_fee))
        support = Decimal(str(support_per_year))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("TCO inputs must be numeric") from exc
    total = annual * contract_years + implementation + support * contract_years
    return DeterministicResult(
        tool="tco_calculator",
        input={"annual_license": float(annual), "implementation_fee": float(implementation), "support_per_year": float(support), "contract_years": contract_years},
        result={"tco": float(total), "currency": currency},
    )


def tco_limit_check(*, annual_license: float, implementation_fee: float, support_per_year: float, contract_years: int, maximum_total: float, currency: str = "USD") -> DeterministicResult:
    """Calculate TCO and own the pass/fail state against the buyer limit."""
    calculated = tco_calculator(annual_license=annual_license, implementation_fee=implementation_fee, support_per_year=support_per_year, contract_years=contract_years, currency=currency)
    total = calculated.result["tco"] if calculated.result else None
    if total is None:
        raise ValueError("TCO calculation did not return a total")
    return DeterministicResult(
        tool="tco_limit_check",
        input={**calculated.input, "maximum_total": maximum_total},
        passed=total <= maximum_total,
        authoritative_state=EvaluationState.SATISFIED if total <= maximum_total else EvaluationState.NOT_SATISFIED,
        result=calculated.result,
    )


def insufficient_evidence(tool: str, missing_fields: list[str]) -> DeterministicResult:
    return DeterministicResult(tool=tool, input={"missing_fields": missing_fields}, authoritative_state=EvaluationState.INSUFFICIENT_EVIDENCE)


def weighted_score(scores: list[tuple[float, float]]) -> float:
    """Return weighted arithmetic only; callers decide review state."""
    if not scores or any(weight < 0 for _, weight in scores):
        raise ValueError("scores must contain non-negative weights")
    total_weight = sum(weight for _, weight in scores)
    if total_weight == 0:
        raise ValueError("total weight must be positive")
    return sum(score * weight for score, weight in scores) / total_weight
