"""Explicit specialist routing; the router never crosses proposal scope."""

from __future__ import annotations

from enum import StrEnum

from .domain import Requirement, RequirementCategory


class Specialist(StrEnum):
    TECHNICAL = "TECHNICAL_SPECIALIST"
    COMMERCIAL = "COMMERCIAL_SPECIALIST"
    COMPLIANCE = "COMPLIANCE_SPECIALIST"


def route_requirement(requirement: Requirement) -> Specialist:
    if requirement.category is RequirementCategory.TECHNICAL:
        return Specialist.TECHNICAL
    if requirement.category is RequirementCategory.COMMERCIAL:
        return Specialist.COMMERCIAL
    if requirement.category is RequirementCategory.COMPLIANCE:
        return Specialist.COMPLIANCE
    raise ValueError(f"unsupported requirement category: {requirement.category}")
