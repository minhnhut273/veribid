"""Contract-first API handlers for the VeriBid MVP boundary.

The Lambda runtime keeps provider payloads behind this DTO boundary. Public
routes are deliberately small; authenticated mutations are scoped by the
Cognito subject and evaluation identifier before any persistence or S3 call.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

try:  # Lambda loads modules from the asset root.
    from health import _demo_fixture  # type: ignore
except ImportError:  # Local package tests.
    from .health import _demo_fixture


EVALUATION_STATUSES = {
    "DRAFT", "INGESTING", "READY_FOR_EXTRACTION", "EXTRACTING_REQUIREMENTS",
    "READY_FOR_EVALUATION", "EVALUATING", "READY_FOR_REVIEW", "REVIEWING",
    "READY_FOR_EXPORT", "COMPLETED", "FAILED",
}
DOCUMENT_ROLES = {"BUYER_RFP", "BUYER_RUBRIC", "BUYER_POLICY", "VENDOR_PROPOSAL", "VENDOR_PRICING", "VENDOR_APPENDIX"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
        "body": json.dumps(body, separators=(",", ":")),
    }


def _success(data: Any, event: dict[str, Any], status: int = 200, next_cursor: Any = None) -> dict[str, Any]:
    meta = {"request_id": _request_id(event), "timestamp": _now()}
    if next_cursor is not None or status == 200 and isinstance(data, list):
        meta["next_cursor"] = next_cursor
    return _response(status, {"data": data, "meta": meta}, event)


def _error(status: int, code: str, message: str, event: dict[str, Any], details: list[dict[str, Any]] | None = None) -> dict[str, Any]:
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
    vendor_id, proposal_id = payload.get("vendor_id"), payload.get("proposal_id")
    if (vendor_id is None) != (proposal_id is None):
        return _error(400, "VALIDATION_ERROR", "vendor_id and proposal_id must be supplied together", event, [{"field": "vendor_id/proposal_id", "reason": "PAIR_REQUIRED"}])
    table, s3, _ = _clients()
    document_id = f"DOC_{uuid4().hex[:16]}"
    object_key = f"evaluations/{evaluation_id}/documents/{document_id}/{payload['file_name']}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    data = {"document_id": document_id, "evaluation_id": evaluation_id, "file_name": payload["file_name"], "media_type": payload["media_type"], "document_role": role, "vendor_id": vendor_id, "proposal_id": proposal_id, "ingestion_status": "AWAITING_UPLOAD", "object_key": object_key, "owner_sub": _owner(event), "created_at": _now()}
    table.put_item(Item={"pk": f"EVAL#{evaluation_id}", "sk": f"DOC#{document_id}", **data})
    url = s3.generate_presigned_url("put_object", Params={"Bucket": os.environ["UPLOADS_BUCKET"], "Key": object_key, "ContentType": payload["media_type"]}, ExpiresIn=900)
    return _success({"document_id": document_id, "ingestion_status": "AWAITING_UPLOAD", "upload": {"method": "PUT", "url": url, "expires_at": expires_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"), "required_headers": {"Content-Type": payload["media_type"]}}}, event, 201)


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
    job_id = f"JOB_INGEST_{uuid4().hex[:16]}"
    table.update_item(Key=key, UpdateExpression="SET ingestion_status = :status, job_id = :job, verified_size = :size, verified_at = :at", ExpressionAttributeValues={":status": "PROCESSING", ":job": job_id, ":size": head.get("ContentLength"), ":at": _now()})
    if os.environ.get("STATE_MACHINE_ARN"):
        sfn.start_execution(stateMachineArn=os.environ["STATE_MACHINE_ARN"], name=job_id, input=json.dumps({"job_id": job_id, "evaluation_id": evaluation_id, "document_id": document_id}))
    return _success({"document_id": document_id, "ingestion_status": "PROCESSING", "job_id": job_id}, event, 202)


def _list_documents(event: dict[str, Any], evaluation_id: str) -> dict[str, Any]:
    if not _evaluation(event, evaluation_id):
        return _error(404, "NOT_FOUND", "Evaluation was not found", event)
    table, _, _ = _clients()
    items = table.query(KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)", ExpressionAttributeValues={":pk": f"EVAL#{evaluation_id}", ":prefix": "DOC#"}).get("Items", [])
    data = [{key: item[key] for key in ("document_id", "file_name", "media_type", "document_role", "vendor_id", "proposal_id", "ingestion_status", "created_at") if key in item} for item in items]
    return _success(data, event, 200, None)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    path = event.get("rawPath") or "/api/v1/health"
    method = (event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod") or "GET").upper()
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
    except Exception:
        return _error(500, "INTERNAL_ERROR", "The request could not be completed", event)
    return _error(404, "NOT_FOUND", "Route not found", event)
