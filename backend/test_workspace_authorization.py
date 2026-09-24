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

    def test_pre_token_trigger_emits_workspace_claim(self) -> None:
        token_event = {"request": {"userAttributes": {"custom:workspace_id": "workspace-a"}}, "response": {}}
        result = pre_token_handler(token_event, None)
        self.assertEqual(
            result["response"]["claimsAndScopeOverrideDetails"]["accessTokenGeneration"]["claimsToAddOrOverride"]["workspace_id"],
            "workspace-a",
        )


if __name__ == "__main__":
    unittest.main()
