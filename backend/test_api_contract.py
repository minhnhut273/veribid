import json

from backend import api


class FakeTable:
    def __init__(self):
        self.items = {}

    def get_item(self, Key, **kwargs):
        return {"Item": self.items.get((Key["pk"], Key["sk"]))}

    def put_item(self, Item, **kwargs):
        self.items[(Item["pk"], Item["sk"])] = Item

    def update_item(self, Key, **kwargs):
        item = self.items.setdefault((Key["pk"], Key["sk"]), dict(Key))
        values = kwargs["ExpressionAttributeValues"]
        expression_names = kwargs.get("ExpressionAttributeNames", {})
        for assignment in kwargs["UpdateExpression"].replace("SET ", "").split(", "):
            field, value_key = [part.strip() for part in assignment.split(" = ")]
            item[expression_names.get(field, field)] = values[value_key]

    def query(self, **kwargs):
        values = kwargs["ExpressionAttributeValues"]
        pk = values[":pk"]
        prefix = values[":prefix"]
        return {"Items": [item for (item_pk, item_sk), item in self.items.items() if item_pk == pk and item_sk.startswith(prefix)]}


class FakeS3:
    def __init__(self):
        self.head = {"ContentLength": 10, "ContentType": "application/pdf"}

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        return f"https://signed.example/{Params['Key']}"

    def head_object(self, **kwargs):
        if self.head is None:
            raise RuntimeError("missing")
        return self.head


class FakeStepFunctions:
    def __init__(self):
        self.calls = []

    def start_execution(self, **kwargs):
        self.calls.append(kwargs)


def event(path, method="GET", body=None, params=None, idem=None):
    headers = {"idempotency-key": idem} if idem else {}
    return {"rawPath": path, "body": json.dumps(body) if body is not None else None, "headers": headers, "pathParameters": params or {}, "requestContext": {"requestId": "req-test", "http": {"method": method}, "authorizer": {"jwt": {"claims": {"sub": "user-1"}}}}}


def test_create_evaluation_is_idempotent(monkeypatch):
    table, s3, sfn = FakeTable(), FakeS3(), FakeStepFunctions()
    monkeypatch.setattr(api, "_clients", lambda: (table, s3, sfn))
    first = api.handler(event("/api/v1/evaluations", "POST", {"name": "RFP"}, idem="same-key"), None)
    second = api.handler(event("/api/v1/evaluations", "POST", {"name": "RFP"}, idem="same-key"), None)
    first_data, second_data = json.loads(first["body"])["data"], json.loads(second["body"])["data"]
    assert first["statusCode"] == second["statusCode"] == 201
    assert first_data["evaluation_id"] == second_data["evaluation_id"]


def test_upload_requires_supported_media_and_vendor_pair(monkeypatch):
    table, s3, sfn = FakeTable(), FakeS3(), FakeStepFunctions()
    table.put_item(Item={"pk": "EVAL#EVL_1", "sk": "META", "owner_sub": "user-1", "evaluation_id": "EVL_1", "name": "RFP", "status": "DRAFT", "created_at": "now"})
    monkeypatch.setattr(api, "_clients", lambda: (table, s3, sfn))
    unsupported = api.handler(event("/api/v1/evaluations/EVL_1/documents", "POST", {"file_name": "a.txt", "media_type": "text/plain", "document_role": "BUYER_RFP"}, {"evaluation_id": "EVL_1"}), None)
    partial = api.handler(event("/api/v1/evaluations/EVL_1/documents", "POST", {"file_name": "a.pdf", "media_type": "application/pdf", "document_role": "VENDOR_PROPOSAL", "vendor_id": "VEN_A"}, {"evaluation_id": "EVL_1"}), None)
    assert unsupported["statusCode"] == partial["statusCode"] == 400


def test_complete_upload_verifies_object_before_starting_worker(monkeypatch):
    table, s3, sfn = FakeTable(), FakeS3(), FakeStepFunctions()
    monkeypatch.setenv("UPLOADS_BUCKET", "bucket")
    monkeypatch.setenv("STATE_MACHINE_ARN", "arn:aws:states:us-east-1:123:stateMachine:test")
    table.put_item(Item={"pk": "EVAL#EVL_1", "sk": "META", "owner_sub": "user-1", "evaluation_id": "EVL_1", "name": "RFP", "status": "DRAFT", "created_at": "now"})
    table.put_item(Item={"pk": "EVAL#EVL_1", "sk": "DOC#DOC_1", "document_id": "DOC_1", "owner_sub": "user-1", "object_key": "evaluations/EVL_1/documents/DOC_1/rfp.pdf", "media_type": "application/pdf", "ingestion_status": "AWAITING_UPLOAD"})
    monkeypatch.setattr(api, "_clients", lambda: (table, s3, sfn))
    response = api.handler(event("/api/v1/evaluations/EVL_1/documents/DOC_1/complete-upload", "POST", {}, {"evaluation_id": "EVL_1", "document_id": "DOC_1"}), None)
    body = json.loads(response["body"])
    assert response["statusCode"] == 202
    assert body["data"]["ingestion_status"] == "PROCESSING"
    assert json.loads(sfn.calls[0]["input"])["action"] == "INGEST"


def test_complete_upload_rejects_missing_object(monkeypatch):
    table, s3, sfn = FakeTable(), FakeS3(), FakeStepFunctions()
    monkeypatch.setenv("UPLOADS_BUCKET", "bucket")
    s3.head = None
    table.put_item(Item={"pk": "EVAL#EVL_1", "sk": "META", "owner_sub": "user-1", "evaluation_id": "EVL_1", "name": "RFP", "status": "DRAFT", "created_at": "now"})
    table.put_item(Item={"pk": "EVAL#EVL_1", "sk": "DOC#DOC_1", "document_id": "DOC_1", "owner_sub": "user-1", "object_key": "missing", "media_type": "application/pdf", "ingestion_status": "AWAITING_UPLOAD"})
    monkeypatch.setattr(api, "_clients", lambda: (table, s3, sfn))
    response = api.handler(event("/api/v1/evaluations/EVL_1/documents/DOC_1/complete-upload", "POST", {}, {"evaluation_id": "EVL_1", "document_id": "DOC_1"}), None)
    assert response["statusCode"] == 422
    assert sfn.calls == []


def test_complete_upload_rejects_oversized_object(monkeypatch):
    table, s3, sfn = FakeTable(), FakeS3(), FakeStepFunctions()
    monkeypatch.setenv("UPLOADS_BUCKET", "bucket")
    s3.head = {"ContentLength": 25 * 1024 * 1024 + 1, "ContentType": "application/pdf"}
    table.put_item(Item={"pk": "EVAL#EVL_1", "sk": "META", "owner_sub": "user-1", "evaluation_id": "EVL_1", "name": "RFP", "status": "DRAFT", "created_at": "now"})
    table.put_item(Item={"pk": "EVAL#EVL_1", "sk": "DOC#DOC_1", "document_id": "DOC_1", "owner_sub": "user-1", "object_key": "large", "media_type": "application/pdf", "ingestion_status": "AWAITING_UPLOAD"})
    monkeypatch.setattr(api, "_clients", lambda: (table, s3, sfn))
    response = api.handler(event("/api/v1/evaluations/EVL_1/documents/DOC_1/complete-upload", "POST", {}, {"evaluation_id": "EVL_1", "document_id": "DOC_1"}), None)
    assert response["statusCode"] == 413
    assert sfn.calls == []


def test_human_review_is_append_only_and_matrix_exposes_final_decision(monkeypatch):
    table, s3, sfn = FakeTable(), FakeS3(), FakeStepFunctions()
    evaluation_id = "EVL_1"
    table.put_item(Item={"pk": f"EVAL#{evaluation_id}", "sk": "META", "owner_sub": "user-1", "evaluation_id": evaluation_id, "name": "RFP", "status": "READY_FOR_REVIEW", "created_at": "now"})
    requirement = {"requirement_id": "REQ_1", "requirement_code": "TECH-01", "title": "Availability", "category": "TECHNICAL", "mandatory": True, "is_disqualifying": False, "weight": 10}
    result = {"evaluation_result_id": "RES_1", "requirement_id": "REQ_1", "vendor_id": "VEN_A", "proposal_id": "PROP_A", "state": "NOT_SATISFIED", "suggested_score": 2, "max_score": 10, "rationale": "deterministic result", "evidence_claims": [], "conflict_pairs": [], "deterministic_result": {"tool": "numeric_threshold_check", "input": {}, "passed": False, "authoritative_state": "NOT_SATISFIED", "result": None}}
    table.put_item(Item={"pk": f"EVAL#{evaluation_id}", "sk": "REQ#REQ_1", "payload": requirement})
    table.put_item(Item={"pk": f"EVAL#{evaluation_id}", "sk": "RES#RES_1", "payload": result, "specialist": "TECHNICAL_SPECIALIST"})
    monkeypatch.setattr(api, "_clients", lambda: (table, s3, sfn))
    response = api.handler(event(f"/api/v1/evaluations/{evaluation_id}/results/RES_1/reviews", "POST", {"action": "OVERRIDE", "final_state": "PARTIALLY_SATISFIED", "final_score": 6, "rationale": "Reviewed the SLA exception."}, {"evaluation_id": evaluation_id, "evaluation_result_id": "RES_1"}), None)
    assert response["statusCode"] == 201
    assert table.items[(f"EVAL#{evaluation_id}", "RES#RES_1")]["payload"]["state"] == "NOT_SATISFIED"
    matrix = api.handler(event(f"/api/v1/evaluations/{evaluation_id}/matrix", "GET", params={"evaluation_id": evaluation_id}), None)
    cell = json.loads(matrix["body"])["data"]["rows"][0]["results"][0]
    assert cell["state"] == "NOT_SATISFIED"
    assert cell["final_state"] == "PARTIALLY_SATISFIED"
    assert cell["final_score"] == 6.0
    assert cell["review_status"] == "CONFIRMED"
    assert any(item["sk"].startswith("AUD#") for item in table.items.values())


def test_export_contains_evidence_trace_and_pdf_payload(monkeypatch):
    table, s3, sfn = FakeTable(), FakeS3(), FakeStepFunctions()
    evaluation_id = "EVL_1"
    table.put_item(Item={"pk": f"EVAL#{evaluation_id}", "sk": "META", "owner_sub": "user-1", "evaluation_id": evaluation_id, "name": "RFP", "status": "READY_FOR_EXPORT", "created_at": "now"})
    table.put_item(Item={"pk": f"EVAL#{evaluation_id}", "sk": "RES#RES_1", "payload": {"evaluation_result_id": "RES_1", "requirement_id": "REQ_1", "vendor_id": "VEN_A", "proposal_id": "PROP_A", "state": "SATISFIED", "suggested_score": 9, "max_score": 10, "rationale": "source", "evidence_claims": [{"relation": "supports", "claim_text": "Availability is committed.", "source_pointer": {"document_name": "proposal.pdf", "page_number": 4}}], "conflict_pairs": []}})
    table.put_item(Item={"pk": f"EVAL#{evaluation_id}", "sk": "REQ#REQ_1", "payload": {"requirement_id": "REQ_1", "requirement_code": "TECH-01"}})
    monkeypatch.setattr(api, "_clients", lambda: (table, s3, sfn))
    started = api.handler(event(f"/api/v1/evaluations/{evaluation_id}/exports", "POST", {"format": "PDF"}, {"evaluation_id": evaluation_id}), None)
    export_id = json.loads(started["body"])["data"]["export_id"]
    fetched = api.handler(event(f"/api/v1/evaluations/{evaluation_id}/exports/{export_id}", "GET", params={"evaluation_id": evaluation_id, "export_id": export_id}), None)
    payload = json.loads(fetched["body"])["data"]
    assert fetched["statusCode"] == 200
    assert payload["status"] == "READY"
    assert payload["content_base64"].startswith("JVBERi0xLjQ")
