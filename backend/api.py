"""Contract-first API handlers for the VeriBid MVP boundary.

The Lambda runtime keeps provider payloads behind this DTO boundary. Public
routes are deliberately small; authenticated mutations are scoped by the
Cognito subject and evaluation identifier before any persistence or S3 call.
"""

from __future__ import annotations

import base64
import json
import os
import textwrap
from decimal import Decimal
from pathlib import PurePath
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

try:  # Lambda loads modules from the asset root.
    from health import _demo_fixture  # type: ignore
except ImportError:  # Local package tests.
    from .health import _demo_fixture

try:
    from .domain import EvaluationState, HumanReview, ReviewAction, ddb_safe
except ImportError:
    from domain import EvaluationState, HumanReview, ReviewAction, ddb_safe  # type: ignore


EVALUATION_STATUSES = {
    "DRAFT", "INGESTING", "READY_FOR_EXTRACTION", "EXTRACTING_REQUIREMENTS",
    "READY_FOR_EVALUATION", "EVALUATING", "READY_FOR_REVIEW", "REVIEWING",
    "READY_FOR_EXPORT", "COMPLETED", "FAILED",
}
DOCUMENT_ROLES = {"BUYER_RFP", "BUYER_RUBRIC", "BUYER_POLICY", "VENDOR_PROPOSAL", "VENDOR_PRICING", "VENDOR_APPENDIX"}
SUPPORTED_MEDIA_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _latest_reviews(table: Any, evaluation_id: str) -> dict[str, dict[str, Any]]:
    items = table.query(
        KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
        ExpressionAttributeValues={":pk": f"EVAL#{evaluation_id}", ":prefix": "REV#"},
    ).get("Items", [])
    latest: dict[str, dict[str, Any]] = {}
    for item in items:
        payload = item.get("payload") or {}
        result_id = payload.get("evaluation_result_id")
        if not result_id:
            continue
        current = latest.get(result_id)
        if current is None or str(payload.get("reviewed_at", "")) > str(current.get("reviewed_at", "")):
            latest[result_id] = payload
    return latest


def _audit_item(evaluation_id: str, event_type: str, actor_sub: str, payload: dict[str, Any]) -> dict[str, Any]:
    audit_id = f"AUD_{uuid4().hex[:16]}"
    return {
        "pk": f"EVAL#{evaluation_id}",
        "sk": f"AUD#{_now()}#{audit_id}",
        "payload": {
            "audit_event_id": audit_id,
            "aggregate_type": "EVALUATION",
            "aggregate_id": evaluation_id,
            "event_type": event_type,
            "actor_sub": actor_sub,
            "occurred_at": _now(),
            "payload": payload,
        },
    }


def _pdf_bytes(text: str) -> bytes:
    """Build a tiny dependency-free PDF for the bounded MVP export path."""
    wrapped_lines = [
        wrapped or " "
        for line in text.splitlines()
        for wrapped in (textwrap.wrap(line, width=110, replace_whitespace=False) or [""])
    ] or [" "]
    page_lines = 48
    pages = [wrapped_lines[index:index + page_lines] for index in range(0, len(wrapped_lines), page_lines)]
    page_object_numbers = [5 + index * 2 for index in range(len(pages))]
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for page_number, page in zip(page_object_numbers, pages):
        commands = ["BT", "/F1 10 Tf", "48 760 Td"]
        for index, line in enumerate(page):
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            if index:
                commands.append("0 -14 Td")
            commands.append(f"({escaped}) Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1", errors="replace")
        content_object_number = page_number + 1
        objects.extend([
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents {content_object_number} 0 R >>".encode(),
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        ])
    kids = " ".join(f"{number} 0 R" for number in page_object_numbers)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode()
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)


def _single_line(value: Any, fallback: str = "unavailable") -> str:
    text_value = str(value or fallback)
    return " ".join(text_value.split())


def _source_locator(pointer: dict[str, Any]) -> str:
    locator_parts: list[str] = []
    if pointer.get("page_number"):
        locator_parts.append(f"page {pointer['page_number']}")
    if pointer.get("section"):
        locator_parts.append(f"section {pointer['section']}")
    if pointer.get("line_start"):
        line_end = pointer.get("line_end") or pointer["line_start"]
        locator_parts.append(f"lines {pointer['line_start']}-{line_end}")
    if pointer.get("sheet_name"):
        locator_parts.append(f"sheet {pointer['sheet_name']}")
    if pointer.get("row_start"):
        row_end = pointer.get("row_end") or pointer["row_start"]
        locator_parts.append(f"rows {pointer['row_start']}-{row_end}")
    if pointer.get("chunk_id"):
        locator_parts.append(f"chunk {pointer['chunk_id']}")
    return "; ".join(locator_parts) or "locator unavailable"


def _claim_trace_lines(label: str, claim: dict[str, Any] | None) -> list[str]:
    if not claim:
        return [f"  - {label} evidence: claim not found in the persisted result"]
    pointer = claim.get("source_pointer") or {}
    excerpt = claim.get("evidence_excerpt") or claim.get("claim_text")
    return [
        f"  - {label} evidence:",
        f"    - EvidenceClaim ID: {_single_line(claim.get('evidence_claim_id'))}",
        f"    - Claim / evidence excerpt: {_single_line(excerpt)}",
        f"    - Document: {_single_line(pointer.get('document_name'))} ({_single_line(pointer.get('document_type'))})",
        f"    - SourcePointer ID: {_single_line(pointer.get('source_pointer_id'))}",
        f"    - Source locator: {_source_locator(pointer)}",
        f"    - Content hash: {_single_line(pointer.get('content_hash'))}",
    ]


def _render_export(table: Any, evaluation_id: str) -> str:
    requirements = [item["payload"] for item in table.query(KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)", ExpressionAttributeValues={":pk": f"EVAL#{evaluation_id}", ":prefix": "REQ#"}).get("Items", [])]
    result_items = table.query(KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)", ExpressionAttributeValues={":pk": f"EVAL#{evaluation_id}", ":prefix": "RES#"}).get("Items", [])
    results = [item["payload"] for item in result_items]
    reviews = _latest_reviews(table, evaluation_id)
    by_requirement = {requirement["requirement_id"]: requirement for requirement in requirements}
    lines = [
        "# VeriBid audit export",
        "",
        f"Evaluation: {evaluation_id}",
        "",
        "This export preserves system suggestions and human decisions. VeriBid does not automatically award a vendor.",
        "",
        "## Evidence matrix",
    ]
    for result in results:
        requirement = by_requirement.get(result.get("requirement_id"), {})
        review = reviews.get(result.get("evaluation_result_id"))
        claims_by_id = {claim.get("evidence_claim_id"): claim for claim in result.get("evidence_claims", [])}
        state = (review or {}).get("final_state") or result.get("state")
        score = (review or {}).get("final_score") if review else None
        if score is None:
            score = result.get("suggested_score")
        lines.append(f"- {requirement.get('requirement_code', result.get('requirement_id'))} / {result.get('vendor_id')}: {state} ({score if score is not None else 'n/a'})")
        for claim in result.get("evidence_claims", []):
            pointer = claim.get("source_pointer", {})
            lines.append(f"  - EvidenceClaim {claim.get('evidence_claim_id', 'unassigned')} ({claim.get('relation')}): {_single_line(claim.get('evidence_excerpt') or claim.get('claim_text'))}")
            lines.append(f"    - Document: {_single_line(pointer.get('document_name'))} ({_single_line(pointer.get('document_type'))})")
            lines.append(f"    - SourcePointer {pointer.get('source_pointer_id', 'unassigned')} @ {_source_locator(pointer)}")
        for index, pair in enumerate(result.get("conflict_pairs", []), start=1):
            lines.extend([
                "  - Conflict pair " + str(index) + ":",
                f"    - conflict_type: {_single_line(pair.get('conflict_type'))}",
                f"    - resolution_status: {_single_line(pair.get('resolution_status'))}",
            ])
            lines.extend(_claim_trace_lines("Supporting", claims_by_id.get(pair.get("supporting_claim_id"))))
            lines.extend(_claim_trace_lines("Contradicting", claims_by_id.get(pair.get("contradicting_claim_id"))))
            lines.append(f"    - Verifier rationale: {_single_line(result.get('verifier_rationale') or result.get('rationale'))}")
        if review:
            lines.append(f"  - human_review: {review.get('action')} by {review.get('reviewer_sub')}")
            if review.get("rationale"):
                lines.append(f"    - rationale: {_single_line(review.get('rationale'))}")
    return "\n".join(lines) + "\n"


def _request_id(event: dict[str, Any]) -> str:
    return str(event.get("requestContext", {}).get("requestId") or f"REQST_{uuid4().hex[:16]}")


def _response(status: int, body: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "content-type": "application/json",
            "cache-control": "no-store",
            "access-control-allow-origin": "*",
        },
        "body": json.dumps(body, separators=(",", ":"), default=_json_default),
    }


def _json_default(value: Any) -> Any:
    """Return DynamoDB Decimal values as JSON numbers at the API boundary."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _success(data: Any, event: dict[str, Any], status: int = 200, next_cursor: Any = None) -> dict[str, Any]:
    meta = {"request_id": _request_id(event), "timestamp": _now()}
    if next_cursor is not None or status == 200 and isinstance(data, list):
        meta["next_cursor"] = next_cursor
    return _response(status, {"data": data, "meta": meta}, event)


def _error(status: int, code: str, message: str, event: dict[str, Any], details: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    print(json.dumps({"request_id": _request_id(event), "status_code": status, "error_code": code}, separators=(",", ":")))
    return _response(status, {"error": {"code": code, "message": message, "details": details or [], "request_id": _request_id(event)}}, event)


def _body(event: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("Request body must be a JSON object")
    return value


def _claims(event: dict[str, Any]) -> dict[str, Any]:
    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    return claims if isinstance(claims, dict) else {}


def _owner(event: dict[str, Any]) -> str | None:
    claims = _claims(event)
    return str(claims.get("sub")) if claims.get("sub") else None


def _clients() -> tuple[Any, Any, Any]:
    import boto3
    return (
        boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"]),
        boto3.client("s3"),
        boto3.client("stepfunctions"),
    )


def _key(evaluation_id: str) -> dict[str, str]:
    return {"pk": f"EVAL#{evaluation_id}", "sk": "META"}


def _idempotency(key: str) -> dict[str, str]:
    return {"pk": f"IDEMP#{key}", "sk": "COMMAND"}


def _evaluation(event: dict[str, Any], evaluation_id: str) -> dict[str, Any] | None:
    table, _, _ = _clients()
    item = table.get_item(Key=_key(evaluation_id), ConsistentRead=True).get("Item")
    if item and item.get("owner_sub") != _owner(event):
        return None
    return item


def _create_evaluation(event: dict[str, Any]) -> dict[str, Any]:
    owner = _owner(event)
    if not owner:
        return _error(401, "UNAUTHENTICATED", "A valid Cognito access token is required", event)
    try:
        payload = _body(event)
    except ValueError as exc:
        return _error(400, "VALIDATION_ERROR", str(exc), event)
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        return _error(400, "VALIDATION_ERROR", "name is required", event, [{"field": "name", "reason": "REQUIRED"}])
    table, _, _ = _clients()
    idem = event.get("headers", {}).get("idempotency-key") or event.get("headers", {}).get("Idempotency-Key")
    if idem:
        prior = table.get_item(Key=_idempotency(str(idem)), ConsistentRead=True).get("Item")
        if prior and prior.get("owner_sub") == owner:
            return _success(prior["response"], event, int(prior.get("status", 201)))
    evaluation_id = f"EVL_{uuid4().hex[:16]}"
    created_at = _now()
    data = {"evaluation_id": evaluation_id, "name": name.strip(), "status": "DRAFT", "created_at": created_at}
    table.put_item(Item={**_key(evaluation_id), **data, "owner_sub": owner})
    if idem:
        table.put_item(Item={**_idempotency(str(idem)), "owner_sub": owner, "response": data, "status": 201, "created_at": created_at})
    return _success(data, event, 201)


def _get_evaluation(event: dict[str, Any], evaluation_id: str) -> dict[str, Any]:
    item = _evaluation(event, evaluation_id)
    if not item:
        return _error(404, "NOT_FOUND", "Evaluation was not found", event)
    data = {key: item[key] for key in ("evaluation_id", "name", "status", "created_at") if key in item}
    return _success(data, event)


def _init_document(event: dict[str, Any], evaluation_id: str) -> dict[str, Any]:
    if not _evaluation(event, evaluation_id):
        return _error(404, "NOT_FOUND", "Evaluation was not found", event)
    try:
        payload = _body(event)
    except ValueError as exc:
        return _error(400, "VALIDATION_ERROR", str(exc), event)
    required = ("file_name", "media_type", "document_role")
    missing = [field for field in required if not payload.get(field)]
    if missing:
        return _error(400, "VALIDATION_ERROR", "Required document fields are missing", event, [{"field": field, "reason": "REQUIRED"} for field in missing])
    role = payload["document_role"]
    if role not in DOCUMENT_ROLES:
        return _error(400, "VALIDATION_ERROR", "Unsupported document_role", event, [{"field": "document_role", "reason": "ENUM"}])
    if payload["media_type"] not in SUPPORTED_MEDIA_TYPES:
        return _error(400, "VALIDATION_ERROR", "Only PDF, DOCX and XLSX uploads are supported", event, [{"field": "media_type", "reason": "UNSUPPORTED"}])
    vendor_id, proposal_id = payload.get("vendor_id"), payload.get("proposal_id")
    if (vendor_id is None) != (proposal_id is None):
        return _error(400, "VALIDATION_ERROR", "vendor_id and proposal_id must be supplied together", event, [{"field": "vendor_id/proposal_id", "reason": "PAIR_REQUIRED"}])
    table, s3, _ = _clients()
    owner = _owner(event)
    idem = event.get("headers", {}).get("idempotency-key") or event.get("headers", {}).get("Idempotency-Key")
    if idem:
        prior = table.get_item(Key=_idempotency(str(idem)), ConsistentRead=True).get("Item")
        if prior and prior.get("owner_sub") == owner:
            return _success(prior["response"], event, int(prior.get("status", 201)))
    document_id = f"DOC_{uuid4().hex[:16]}"
    safe_file_name = PurePath(str(payload["file_name"])).name
    if not safe_file_name or safe_file_name in {".", ".."}:
        return _error(400, "VALIDATION_ERROR", "file_name is invalid", event, [{"field": "file_name", "reason": "INVALID"}])
    object_key = f"evaluations/{evaluation_id}/documents/{document_id}/{safe_file_name}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    data = {"document_id": document_id, "evaluation_id": evaluation_id, "file_name": safe_file_name, "media_type": payload["media_type"], "document_role": role, "vendor_id": vendor_id, "proposal_id": proposal_id, "ingestion_status": "AWAITING_UPLOAD", "object_key": object_key, "owner_sub": owner, "created_at": _now()}
    table.put_item(Item={"pk": f"EVAL#{evaluation_id}", "sk": f"DOC#{document_id}", **data})
    url = s3.generate_presigned_url("put_object", Params={"Bucket": os.environ["UPLOADS_BUCKET"], "Key": object_key, "ContentType": payload["media_type"]}, ExpiresIn=900)
    response_data = {"document_id": document_id, "ingestion_status": "AWAITING_UPLOAD", "upload": {"method": "PUT", "url": url, "expires_at": expires_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"), "required_headers": {"Content-Type": payload["media_type"]}}}
    if idem:
        table.put_item(Item={**_idempotency(str(idem)), "owner_sub": owner, "response": response_data, "status": 201, "created_at": _now()})
    return _success(response_data, event, 201)


def _complete_document(event: dict[str, Any], evaluation_id: str, document_id: str) -> dict[str, Any]:
    item = _evaluation(event, evaluation_id)
    if not item:
        return _error(404, "NOT_FOUND", "Evaluation was not found", event)
    table, s3, sfn = _clients()
    key = {"pk": f"EVAL#{evaluation_id}", "sk": f"DOC#{document_id}"}
    document = table.get_item(Key=key, ConsistentRead=True).get("Item")
    if not document or document.get("owner_sub") != _owner(event):
        return _error(404, "NOT_FOUND", "Document was not found", event)
    if document.get("ingestion_status") == "PROCESSING":
        return _success({"document_id": document_id, "ingestion_status": "PROCESSING", "job_id": document.get("job_id")}, event, 202)
    try:
        head = s3.head_object(Bucket=os.environ["UPLOADS_BUCKET"], Key=document["object_key"])
    except Exception:
        return _error(422, "SOURCE_NOT_RESOLVABLE", "Uploaded object was not found; ingestion did not start", event)
    if head.get("ContentLength", 0) <= 0:
        return _error(422, "SOURCE_NOT_RESOLVABLE", "Uploaded object is empty; ingestion did not start", event)
    if head.get("ContentLength", 0) > MAX_UPLOAD_BYTES:
        return _error(413, "PAYLOAD_TOO_LARGE", "Uploaded object exceeds the 25 MiB MVP limit", event)
    expected_type = document.get("media_type")
    actual_type = head.get("ContentType")
    if expected_type and actual_type and actual_type != expected_type:
        return _error(422, "SOURCE_NOT_RESOLVABLE", "Uploaded object content type does not match the initialized document", event, [{"field": "Content-Type", "reason": "MISMATCH"}])
    job_id = f"JOB_INGEST_{uuid4().hex[:16]}"
    table.update_item(Key=key, UpdateExpression="SET ingestion_status = :status, job_id = :job, verified_size = :size, verified_at = :at", ExpressionAttributeValues={":status": "PROCESSING", ":job": job_id, ":size": head.get("ContentLength"), ":at": _now()})
    if os.environ.get("STATE_MACHINE_ARN"):
        sfn.start_execution(stateMachineArn=os.environ["STATE_MACHINE_ARN"], name=job_id, input=json.dumps({"action": "INGEST", "job_id": job_id, "evaluation_id": evaluation_id, "document_id": document_id}))
    return _success({"document_id": document_id, "ingestion_status": "PROCESSING", "job_id": job_id}, event, 202)


def _list_documents(event: dict[str, Any], evaluation_id: str) -> dict[str, Any]:
    if not _evaluation(event, evaluation_id):
        return _error(404, "NOT_FOUND", "Evaluation was not found", event)
    table, _, _ = _clients()
    items = table.query(KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)", ExpressionAttributeValues={":pk": f"EVAL#{evaluation_id}", ":prefix": "DOC#"}).get("Items", [])
    data = [{key: item[key] for key in ("document_id", "file_name", "media_type", "document_role", "vendor_id", "proposal_id", "ingestion_status", "created_at") if key in item} for item in items]
    return _success(data, event, 200, None)


def _start_async(event: dict[str, Any], evaluation_id: str, action: str, prefix: str, payload: dict[str, Any], status: str) -> dict[str, Any]:
    if not _evaluation(event, evaluation_id):
        return _error(404, "NOT_FOUND", "Evaluation was not found", event)
    table, _, sfn = _clients()
    owner = _owner(event)
    idem = event.get("headers", {}).get("idempotency-key") or event.get("headers", {}).get("Idempotency-Key")
    if idem:
        prior = table.get_item(Key=_idempotency(str(idem)), ConsistentRead=True).get("Item")
        if prior and prior.get("owner_sub") == owner:
            return _success(prior["response"], event, int(prior.get("status", 202)))
    job_id = f"{prefix}{uuid4().hex[:16]}"
    response_data = {("run_id" if action == "EVALUATE" else "job_id"): job_id, "status": status}
    table.put_item(Item={"pk": f"EVAL#{evaluation_id}", "sk": f"JOB#{job_id}", "job_id": job_id, "run_id": job_id if action == "EVALUATE" else None, "owner_sub": owner, "status": status, "action": action, "created_at": _now()})
    target_status = {"EXTRACT_REQUIREMENTS": "EXTRACTING_REQUIREMENTS", "EVALUATE": "EVALUATING"}.get(action)
    if target_status:
        table.update_item(
            Key=_key(evaluation_id),
            UpdateExpression="SET #status = :status, updated_at = :at",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": target_status, ":at": _now()},
        )
    if idem:
        table.put_item(Item={**_idempotency(str(idem)), "owner_sub": owner, "response": response_data, "status": 202, "created_at": _now()})
    if os.environ.get("STATE_MACHINE_ARN"):
        sfn.start_execution(stateMachineArn=os.environ["STATE_MACHINE_ARN"], name=job_id, input=json.dumps({"action": action, "job_id": job_id, "run_id": job_id if action == "EVALUATE" else None, "evaluation_id": evaluation_id, **payload}))
    return _success(response_data, event, 202)


def _extract_requirements(event: dict[str, Any], evaluation_id: str) -> dict[str, Any]:
    return _start_async(event, evaluation_id, "EXTRACT_REQUIREMENTS", "JOB_REQ_", {}, "QUEUED")


def _list_requirements(event: dict[str, Any], evaluation_id: str) -> dict[str, Any]:
    if not _evaluation(event, evaluation_id):
        return _error(404, "NOT_FOUND", "Evaluation was not found", event)
    table, _, _ = _clients()
    items = table.query(KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)", ExpressionAttributeValues={":pk": f"EVAL#{evaluation_id}", ":prefix": "REQ#"}).get("Items", [])
    return _success([item["payload"] for item in items], event, 200, None)


def _start_run(event: dict[str, Any], evaluation_id: str) -> dict[str, Any]:
    try:
        payload = _body(event)
    except ValueError as exc:
        return _error(400, "VALIDATION_ERROR", str(exc), event)
    vendor_ids = payload.get("vendor_ids")
    if vendor_ids is not None and (not isinstance(vendor_ids, list) or not all(isinstance(value, str) for value in vendor_ids)):
        return _error(400, "VALIDATION_ERROR", "vendor_ids must be a list of strings", event)
    return _start_async(event, evaluation_id, "EVALUATE", "RUN_", {"vendor_ids": vendor_ids or []}, "QUEUED")


def _get_run(event: dict[str, Any], evaluation_id: str, run_id: str) -> dict[str, Any]:
    if not _evaluation(event, evaluation_id):
        return _error(404, "NOT_FOUND", "Evaluation was not found", event)
    table, _, _ = _clients()
    item = table.get_item(Key={"pk": f"EVAL#{evaluation_id}", "sk": f"RUN#{run_id}"}, ConsistentRead=True).get("Item")
    if not item:
        item = table.get_item(Key={"pk": f"EVAL#{evaluation_id}", "sk": f"JOB#{run_id}"}, ConsistentRead=True).get("Item")
    if not item:
        return _error(404, "NOT_FOUND", "Run was not found", event)
    data = {key: item[key] for key in ("run_id", "job_id", "status", "progress", "telemetry", "created_at", "updated_at") if key in item}
    return _success(data, event)


def _matrix(event: dict[str, Any], evaluation_id: str) -> dict[str, Any]:
    if not _evaluation(event, evaluation_id):
        return _error(404, "NOT_FOUND", "Evaluation was not found", event)
    table, _, _ = _clients()
    requirements = [item["payload"] for item in table.query(KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)", ExpressionAttributeValues={":pk": f"EVAL#{evaluation_id}", ":prefix": "REQ#"}).get("Items", [])]
    result_items = table.query(KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)", ExpressionAttributeValues={":pk": f"EVAL#{evaluation_id}", ":prefix": "RES#"}).get("Items", [])
    results = [item["payload"] for item in result_items]
    specialists = {item["payload"]["evaluation_result_id"]: item.get("specialist") for item in result_items}
    reviews = _latest_reviews(table, evaluation_id)
    vendor_ids = sorted({result["vendor_id"] for result in results})
    vendors = [{"vendor_id": value, "display_name": value} for value in vendor_ids]
    rows = []
    for requirement in requirements:
        cells = []
        for result in results:
            if result["requirement_id"] == requirement["requirement_id"]:
                review = reviews.get(result["evaluation_result_id"])
                cells.append({
                    "vendor_id": result["vendor_id"],
                    "evaluation_result_id": result["evaluation_result_id"],
                    "state": result["state"],
                    "suggested_score": result.get("suggested_score"),
                    "final_state": review.get("final_state") if review else None,
                    "final_score": review.get("final_score") if review else None,
                    "review_status": ("CONFIRMED" if review and review.get("action") in {"ACCEPT", "OVERRIDE"} else "FOLLOWUP_REQUESTED" if review else "PENDING"),
                    "specialist": specialists.get(result["evaluation_result_id"]),
                    "has_conflict": bool(result.get("conflict_pairs")),
                })
        rows.append({"requirement": {key: requirement.get(key) for key in ("requirement_id", "requirement_code", "title", "category", "mandatory", "is_disqualifying", "weight")}, "results": cells})
    return _success({"vendors": vendors, "rows": rows}, event)


def _result_detail(event: dict[str, Any], evaluation_id: str, result_id: str) -> dict[str, Any]:
    if not _evaluation(event, evaluation_id):
        return _error(404, "NOT_FOUND", "Evaluation was not found", event)
    table, _, _ = _clients()
    item = table.get_item(Key={"pk": f"EVAL#{evaluation_id}", "sk": f"RES#{result_id}"}, ConsistentRead=True).get("Item")
    if not item:
        return _error(404, "NOT_FOUND", "Evaluation result was not found", event)
    review = table.query(KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)", ExpressionAttributeValues={":pk": f"EVAL#{evaluation_id}", ":prefix": f"REV#{result_id}#"}, ScanIndexForward=False, Limit=1).get("Items", [])
    data = dict(item["payload"])
    data["specialist"] = item.get("specialist")
    data["human_review"] = review[0].get("payload") if review else None
    data["audit_events"] = [entry.get("payload") for entry in table.query(KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)", ExpressionAttributeValues={":pk": f"EVAL#{evaluation_id}", ":prefix": "AUD#"}).get("Items", []) if entry.get("payload", {}).get("payload", {}).get("evaluation_result_id") == result_id]
    return _success(data, event)


def _review(event: dict[str, Any], evaluation_id: str, result_id: str) -> dict[str, Any]:
    if not _evaluation(event, evaluation_id):
        return _error(404, "NOT_FOUND", "Evaluation was not found", event)
    table, _, _ = _clients()
    item = table.get_item(Key={"pk": f"EVAL#{evaluation_id}", "sk": f"RES#{result_id}"}, ConsistentRead=True).get("Item")
    if not item:
        return _error(404, "NOT_FOUND", "Evaluation result was not found", event)
    try:
        body = _body(event)
        action = ReviewAction(body.get("action"))
        review = HumanReview(human_review_id=f"REV_{uuid4().hex[:16]}", evaluation_result_id=result_id, action=action, system_state=EvaluationState(item["payload"]["state"]), system_score=item["payload"].get("suggested_score"), final_state=body.get("final_state"), final_score=body.get("final_score"), rationale=body.get("rationale"), reviewer_sub=_owner(event) or "unknown", reviewed_at=datetime.now(timezone.utc))
    except ValueError as exc:
        return _error(400, "VALIDATION_ERROR", str(exc), event)
    table.put_item(Item={"pk": f"EVAL#{evaluation_id}", "sk": f"REV#{result_id}#{review.human_review_id}", "payload": ddb_safe(review.model_dump(mode="json")), "created_at": _now(), "owner_sub": _owner(event)})
    table.put_item(Item=_audit_item(evaluation_id, "HUMAN_REVIEW_RECORDED", _owner(event) or "unknown", {"evaluation_result_id": result_id, "action": review.action.value, "system_state": review.system_state.value, "final_state": review.final_state.value if review.final_state else None}))
    return _success(review.model_dump(mode="json"), event, 201)


def _start_export(event: dict[str, Any], evaluation_id: str) -> dict[str, Any]:
    if not _evaluation(event, evaluation_id):
        return _error(404, "NOT_FOUND", "Evaluation was not found", event)
    try:
        body = _body(event)
    except ValueError as exc:
        return _error(400, "VALIDATION_ERROR", str(exc), event)
    format_name = str(body.get("format", "MARKDOWN")).upper()
    if format_name not in {"MARKDOWN", "PDF"}:
        return _error(400, "VALIDATION_ERROR", "format must be MARKDOWN or PDF", event)
    table, _, _ = _clients()
    export_id = f"EXP_{uuid4().hex[:16]}"
    content = _render_export(table, evaluation_id)
    item = {"pk": f"EVAL#{evaluation_id}", "sk": f"EXP#{export_id}", "export_id": export_id, "status": "READY", "format": format_name, "generated_at": _now(), "report_version": 1, "owner_sub": _owner(event)}
    if format_name == "PDF":
        item["content_base64"] = base64.b64encode(_pdf_bytes(content)).decode("ascii")
    else:
        item["content"] = content
    table.put_item(Item=item)
    table.put_item(Item=_audit_item(evaluation_id, "EXPORT_GENERATED", _owner(event) or "unknown", {"export_id": export_id, "format": format_name}))
    return _success({"export_id": export_id, "status": "READY"}, event, 202)


def _get_export(event: dict[str, Any], evaluation_id: str, export_id: str) -> dict[str, Any]:
    if not _evaluation(event, evaluation_id):
        return _error(404, "NOT_FOUND", "Evaluation was not found", event)
    table, _, _ = _clients()
    item = table.get_item(Key={"pk": f"EVAL#{evaluation_id}", "sk": f"EXP#{export_id}"}, ConsistentRead=True).get("Item")
    if not item:
        return _error(404, "NOT_FOUND", "Export was not found", event)
    return _success({key: item[key] for key in ("export_id", "status", "report_version", "generated_at", "format", "content", "content_base64") if key in item}, event)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    path = event.get("rawPath") or "/api/v1/health"
    method = (event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod") or "GET").upper()
    print(json.dumps({"request_id": _request_id(event), "method": method, "path": path, "owner_present": bool(_owner(event))}, separators=(",", ":")))
    if path == "/api/v1/health" and method == "GET":
        return _success({"service": os.getenv("SERVICE_NAME", "veribid-api"), "version": os.getenv("SERVICE_VERSION", "unknown"), "status": "ok", "timestamp": _now()}, event)
    if path == "/api/v1/demo" and method == "GET":
        return _success(_demo_fixture(), event)
    if not _owner(event):
        return _error(401, "UNAUTHENTICATED", "A valid Cognito access token is required", event)
    path_parameters = event.get("pathParameters") or {}
    try:
        if path == "/api/v1/evaluations" and method == "POST":
            return _create_evaluation(event)
        if path == "/api/v1/evaluations/{evaluation_id}" or path_parameters.get("evaluation_id") and path.endswith(path_parameters["evaluation_id"]):
            if method == "GET":
                return _get_evaluation(event, path_parameters["evaluation_id"])
        if path.endswith("/documents") and method == "POST":
            return _init_document(event, path_parameters["evaluation_id"])
        if path.endswith("/documents") and method == "GET":
            return _list_documents(event, path_parameters["evaluation_id"])
        if path.endswith("/complete-upload") and method == "POST":
            return _complete_document(event, path_parameters["evaluation_id"], path_parameters["document_id"])
        if path.endswith("/requirements/extract") and method == "POST":
            return _extract_requirements(event, path_parameters["evaluation_id"])
        if path.endswith("/requirements") and method == "GET":
            return _list_requirements(event, path_parameters["evaluation_id"])
        if path.endswith("/runs") and method == "POST":
            return _start_run(event, path_parameters["evaluation_id"])
        if "/runs/" in path and method == "GET":
            return _get_run(event, path_parameters["evaluation_id"], path_parameters["run_id"])
        if path.endswith("/matrix") and method == "GET":
            return _matrix(event, path_parameters["evaluation_id"])
        if path.endswith("/reviews") and method == "POST":
            return _review(event, path_parameters["evaluation_id"], path_parameters["evaluation_result_id"])
        if "/results/" in path and method == "GET":
            return _result_detail(event, path_parameters["evaluation_id"], path_parameters["evaluation_result_id"])
        if path.endswith("/exports") and method == "POST":
            return _start_export(event, path_parameters["evaluation_id"])
        if "/exports/" in path and method == "GET":
            return _get_export(event, path_parameters["evaluation_id"], path_parameters["export_id"])
    except Exception:
        return _error(500, "INTERNAL_ERROR", "The request could not be completed", event)
    return _error(404, "NOT_FOUND", "Route not found", event)
