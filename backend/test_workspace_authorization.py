"""Runnable Sprint 1 checks for Cognito-group and workspace authorization."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import api
from backend.cognito_pre_token import handler as pre_token_handler


class FakeTable:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], dict] = {}

    def get_item(self, Key, **kwargs):
        return {"Item": self.items.get((Key["pk"], Key["sk"]))}

    def put_item(self, Item, **kwargs):
        self.items[(Item["pk"], Item["sk"])] = Item


class FakeS3:
    pass


class FakeStepFunctions:
    pass


def event(path: str, method: str, workspace_id: str, groups: list[str], body=None, params=None):
    return {
        "rawPath": path,
        "body": json.dumps(body) if body is not None else None,
        "headers": {},
        "pathParameters": params or {},
        "requestContext": {
            "requestId": "workspace-auth-test",
            "http": {"method": method},
            "authorizer": {"jwt": {"claims": {
                "sub": f"user-{workspace_id}",
                "workspace_id": workspace_id,
                "custom:workspace_id": workspace_id,
                "cognito:groups": groups,
            }}},
        },
    }


class WorkspaceAuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.table = FakeTable()
        self.clients = (self.table, FakeS3(), FakeStepFunctions())
        self.clients_patch = patch.object(api, "_clients", return_value=self.clients)
        self.clients_patch.start()
        self.addCleanup(self.clients_patch.stop)

    def test_workspace_members_share_read_access_but_other_workspaces_do_not(self) -> None:
        created = api.handler(event(
            "/api/v1/evaluations", "POST", "workspace-a", ["TenantAdmin"], {"name": "RFP"}
        ), None)
        self.assertEqual(created["statusCode"], 201)
        evaluation_id = json.loads(created["body"])["data"]["evaluation_id"]
        stored = self.table.items[(f"EVAL#{evaluation_id}", "META")]
        self.assertEqual(stored["workspace_id"], "workspace-a")

        same_workspace = api.handler(event(
            f"/api/v1/evaluations/{evaluation_id}", "GET", "workspace-a", ["Auditor"],
            params={"evaluation_id": evaluation_id},
        ), None)
        other_workspace = api.handler(event(
            f"/api/v1/evaluations/{evaluation_id}", "GET", "workspace-b", ["TenantAdmin"],
            params={"evaluation_id": evaluation_id},
        ), None)
        self.assertEqual(same_workspace["statusCode"], 200)
        self.assertEqual(other_workspace["statusCode"], 404)

    def test_auditor_is_read_only(self) -> None:
        response = api.handler(event(
            "/api/v1/evaluations", "POST", "workspace-a", ["Auditor"], {"name": "RFP"}
        ), None)
        self.assertEqual(response["statusCode"], 403)
        self.assertEqual(json.loads(response["body"])["error"]["code"], "FORBIDDEN")

    def test_pre_token_trigger_emits_workspace_claim_and_preserves_existing_groups(self) -> None:
        token_event = {
            "request": {
                "userAttributes": {"sub": "user-1", "custom:workspace_id": "workspace-a"},
                "groupConfiguration": {
                    "groupsToOverride": ["Auditor"],
                    "iamRolesToOverride": ["arn:aws:iam::123456789012:role/auditor"],
                    "preferredRole": "arn:aws:iam::123456789012:role/auditor",
                },
            },
            "response": {},
        }
        result = pre_token_handler(token_event, None)
        details = result["response"]["claimsAndScopeOverrideDetails"]
        self.assertEqual(details["accessTokenGeneration"]["claimsToAddOrOverride"]["workspace_id"], "workspace-a")
        self.assertEqual(details["idTokenGeneration"]["claimsToAddOrOverride"]["workspace_id"], "workspace-a")
        self.assertNotIn("cognito:groups", details["accessTokenGeneration"]["claimsToAddOrOverride"])
        self.assertNotIn("groupOverrideDetails", details)
        self.assertEqual(token_event["request"]["groupConfiguration"]["groupsToOverride"], ["Auditor"])

    def test_pre_token_refresh_handles_null_claim_override_details(self) -> None:
        token_event = {
            "triggerSource": "TokenGeneration_RefreshTokens",
            "request": {
                "userAttributes": {"sub": "user-1"},
                "groupConfiguration": {"groupsToOverride": []},
            },
            "response": {"claimsAndScopeOverrideDetails": None},
        }

        result = pre_token_handler(token_event, None)

        details = result["response"]["claimsAndScopeOverrideDetails"]
        self.assertEqual(
            details["accessTokenGeneration"]["claimsToAddOrOverride"]["workspace_id"],
            "WS_user_1",
        )
        self.assertEqual(details["groupOverrideDetails"]["groupsToOverride"], ["TenantAdmin"])

    def test_self_signup_user_without_explicit_workspace_id_can_create_evaluations(self) -> None:
        token_event = {
            "userName": "a-different-login-alias@example.com",
            "request": {
                "userAttributes": {"sub": "123e4567-e89b-12d3-a456-426614174000"},
                "groupConfiguration": {"groupsToOverride": [], "iamRolesToOverride": [], "preferredRole": None},
            },
            "response": {},
        }
        result = pre_token_handler(token_event, None)
        details = result["response"]["claimsAndScopeOverrideDetails"]
        claims = details["accessTokenGeneration"]["claimsToAddOrOverride"]
        self.assertEqual(claims["workspace_id"], "WS_123e4567_e89b_12d3_a456_426614174000")
        self.assertEqual(details["groupOverrideDetails"]["groupsToOverride"], ["TenantAdmin"])
        self.assertNotIn("cognito:groups", claims)

        self_signup_event = {
            "rawPath": "/api/v1/evaluations",
            "body": json.dumps({"name": "Self Signup RFP"}),
            "headers": {},
            "pathParameters": {},
            "requestContext": {
                "requestId": "self-signup-test",
                "http": {"method": "POST"},
                "authorizer": {"jwt": {"claims": {
                    "sub": "123e4567-e89b-12d3-a456-426614174000",
                    **claims,
                    "cognito:groups": details["groupOverrideDetails"]["groupsToOverride"],
                }}},
            },
        }
        response = api.handler(self_signup_event, None)
        self.assertEqual(response["statusCode"], 201)
        evaluation_id = json.loads(response["body"])["data"]["evaluation_id"]
        stored = self.table.items[(f"EVAL#{evaluation_id}", "META")]
        self.assertEqual(stored["workspace_id"], claims["workspace_id"])

    def test_new_account_with_existing_auditor_group_is_not_promoted(self) -> None:
        token_event = {
            "request": {
                "userAttributes": {"sub": "auditor-sub"},
                "groupConfiguration": {"groupsToOverride": ["Auditor"]},
            },
            "response": {},
        }
        result = pre_token_handler(token_event, None)
        self.assertNotIn("groupOverrideDetails", result["response"]["claimsAndScopeOverrideDetails"])

        auditor_event = {
            "rawPath": "/api/v1/evaluations",
            "body": json.dumps({"name": "Should remain read-only"}),
            "headers": {},
            "pathParameters": {},
            "requestContext": {
                "requestId": "auditor-self-signup-test",
                "http": {"method": "POST"},
                "authorizer": {"jwt": {"claims": {
                    "sub": "auditor-sub",
                    "workspace_id": "WS_auditor_sub",
                    "cognito:groups": ["Auditor"],
                }}},
            },
        }
        response = api.handler(auditor_event, None)
        self.assertEqual(response["statusCode"], 403)

    def test_authenticated_user_without_a_cognito_group_fails_closed(self) -> None:
        no_group_event = {
            "rawPath": "/api/v1/evaluations",
            "body": json.dumps({"name": "No role"}),
            "headers": {},
            "pathParameters": {},
            "requestContext": {
                "requestId": "missing-role-test",
                "http": {"method": "POST"},
                "authorizer": {"jwt": {"claims": {"sub": "user-1", "workspace_id": "workspace-a"}}},
            },
        }
        response = api.handler(no_group_event, None)
        self.assertEqual(response["statusCode"], 403)


if __name__ == "__main__":
    unittest.main()
