"""Cognito V2 pre-token trigger for the immutable workspace boundary."""

from __future__ import annotations

import json
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

    response = event.get("response")
    if not isinstance(response, dict):
        response = {}
        event["response"] = response
    overrides = response.get("claimsAndScopeOverrideDetails")
    if not isinstance(overrides, dict):
        overrides = {}
        response["claimsAndScopeOverrideDetails"] = overrides
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
    write_role_present = isinstance(groups, list) and bool({str(group) for group in groups} & {"TenantAdmin", "SourcingLead"})
    default_role_applied = False
    if not groups and not attributes.get("custom:workspace_id"):
        # Only an ungrouped, unprovisioned identity is promoted. Existing
        # Cognito group membership (including Auditor) remains authoritative.
        group_override = {"groupsToOverride": ["TenantAdmin"]}
        for key in ("iamRolesToOverride", "preferredRole"):
            if group_configuration.get(key) is not None:
                group_override[key] = group_configuration[key]
        overrides["groupOverrideDetails"] = group_override
        default_role_applied = True
    # Keep auth diagnostics useful without writing identity, email, token, or group names.
    print(json.dumps({
        "event": "cognito_pre_token_role_decision",
        "trigger_source": event.get("triggerSource"),
        "workspace_attribute_present": bool(attributes.get("custom:workspace_id")),
        "group_count": len(groups) if isinstance(groups, list) else int(bool(groups)),
        "write_role_present": write_role_present,
        "default_role_applied": default_role_applied,
    }, separators=(",", ":")))
    return event
