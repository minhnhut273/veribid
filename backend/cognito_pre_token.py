"""Cognito V2 pre-token trigger for the immutable workspace boundary."""

from __future__ import annotations

from typing import Any


def _personal_workspace_id(sub: str) -> str:
    return f"WS_{sub.replace('-', '_')}"


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    attributes = event.get("request", {}).get("userAttributes", {})
    workspace_id = attributes.get("custom:workspace_id")
    if not workspace_id:
        subject = attributes.get("sub")
        if not subject:
            raise ValueError("Cognito pre-token event is missing the immutable user sub")
        workspace_id = _personal_workspace_id(str(subject))

    response = event.setdefault("response", {})
    overrides = response.setdefault("claimsAndScopeOverrideDetails", {})
    claim_overrides = {"workspace_id": str(workspace_id)}
    overrides["accessTokenGeneration"] = {
        "claimsToAddOrOverride": claim_overrides,
    }
    overrides["idTokenGeneration"] = {
        "claimsToAddOrOverride": claim_overrides,
    }
    request = event.get("request", {})
    group_configuration = request.get("groupConfiguration") or {}
    groups = group_configuration.get("groupsToOverride") or []
    if not groups and not attributes.get("custom:workspace_id"):
        # Only an ungrouped, unprovisioned identity is promoted. Existing
        # Cognito group membership (including Auditor) remains authoritative.
        group_override = {"groupsToOverride": ["TenantAdmin"]}
        for key in ("iamRolesToOverride", "preferredRole"):
            if group_configuration.get(key) is not None:
                group_override[key] = group_configuration[key]
        overrides["groupOverrideDetails"] = group_override
    return event
