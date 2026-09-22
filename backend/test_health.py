import json

from backend.health import handler


def test_health_returns_contract_envelope():
    response = handler({}, type("Context", (), {"aws_request_id": "test-request"})())
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["data"]["status"] == "ok"
    assert body["meta"]["request_id"] == "test-request"


def test_demo_is_read_only_and_source_grounded():
    response = handler({"rawPath": "/api/v1/demo"}, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["meta"] == {"read_only": True, "synthetic": True}
    assert len(body["data"]["vendors"]) == 3
    assert all("source_pointers" in cell for cell in body["data"]["matrix"])
    assert any(cell["state"] == "CONFLICTING_EVIDENCE" for cell in body["data"]["matrix"])
