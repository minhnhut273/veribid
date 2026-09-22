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
