"""Cognito V2 pre-token trigger for the immutable workspace boundary."""

from __future__ import annotations

from typing import Any


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    attributes = event.get("request", {}).get("userAttributes", {})
    workspace_id = attributes.get("custom:workspace_id")
    if not workspace_id:
        user_name = event.get("userName") or attributes.get("sub") or "user"
        workspace_id = f"WS_{user_name.replace('-', '_')}"

    response = event.setdefault("response", {})
    overrides = response.setdefault("claimsAndScopeOverrideDetails", {})
    claim_overrides = {
        "workspace_id": str(workspace_id),
        "cognito:groups": "TenantAdmin",
    }
    overrides["accessTokenGeneration"] = {
        "claimsToAddOrOverride": claim_overrides,
    }
    overrides["idTokenGeneration"] = {
        "claimsToAddOrOverride": claim_overrides,
    }
    return event
