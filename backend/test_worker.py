from contextlib import contextmanager

from backend import worker
from backend.bedrock_adapter import BedrockTelemetry


class FakeBatch:
    def __init__(self, table):
        self.table = table

    def put_item(self, Item):
        self.table.put_item(Item=Item)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeTable:
    def __init__(self, items):
        self.items = items

    def query(self, **kwargs):
        prefix = kwargs["ExpressionAttributeValues"][":prefix"]
        return {"Items": [item for item in self.items if item["sk"].startswith(prefix)]}

    def batch_writer(self):
        return FakeBatch(self)

    def put_item(self, Item):
        self.items.append(Item)

    def update_item(self, **kwargs):
        return None


class FakeBedrock:
    def __init__(self):
        self.telemetry = BedrockTelemetry(1, 100, 20, 80, 0, 4)

    def converse_json(self, **kwargs):
        return worker.SpecialistOutput(state="PARTIALLY_SATISFIED", score=6, rationale="Typed semantic assessment"), self.telemetry


def test_semantic_branch_keeps_route_when_bedrock_returns_typed_output(monkeypatch):
    requirement = {
        "requirement_id": "REQ_1", "requirement_code": "COMP-01", "title": "EU residency", "description": "Data stays in EU",
        "category": "COMPLIANCE", "mandatory": True, "is_disqualifying": True, "weight": 10, "evaluation_type": "SEMANTIC",
        "source_pointer": {"source_pointer_id": "PTR_1", "document_id": "DOC_RFP", "document_name": "RFP.docx", "document_type": "DOCX"}, "validation_status": "VALID",
    }
    chunk = {
        "chunk_id": "CHK_1", "document_id": "DOC_VENDOR", "document_name": "proposal.docx", "document_type": "DOCX",
        "text": "Customer data is hosted in the EU.", "content_hash": "sha256:" + "a" * 64,
        "source_pointer": {"source_pointer_id": "PTR_2", "document_id": "DOC_VENDOR", "document_name": "proposal.docx", "document_type": "DOCX"},
        "vendor_id": "VENDOR_A", "proposal_id": "PROPOSAL_A",
    }
    table = FakeTable([
        {"sk": "REQ#REQ_1", "payload": requirement},
        {"sk": "CHK#CHK_1", "payload": chunk},
    ])
    monkeypatch.setattr(worker, "_clients", lambda: (table, object()))
    monkeypatch.setattr(worker, "BedrockAdapter", FakeBedrock)
    monkeypatch.setenv("BEDROCK_MODEL_ID", "verified-model")
    result = worker._evaluate({"evaluation_id": "EVL_1", "run_id": "RUN_1", "job_id": "RUN_1", "action": "EVALUATE"})
    persisted = next(item for item in table.items if item.get("sk", "").startswith("RES#"))
    assert result["result_count"] == 1
    assert persisted["specialist"] == "COMPLIANCE_SPECIALIST"
