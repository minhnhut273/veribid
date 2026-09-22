"""Step Functions worker for verified ingestion and deterministic fixture runs."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

try:
    from .deterministic import numeric_threshold_check, tco_calculator
    from .domain import EvaluationState, Requirement, RequirementCategory, EvaluationType
    from .ingestion import parse_document
    from .verifier import new_conflict_pair, verify_candidate
except ImportError:  # Lambda handler modules are loaded from the asset root.
    from deterministic import numeric_threshold_check, tco_calculator  # type: ignore
    from domain import EvaluationState, Requirement, RequirementCategory, EvaluationType  # type: ignore
    from ingestion import parse_document  # type: ignore
    from verifier import new_conflict_pair, verify_candidate  # type: ignore

try:
    from .bedrock_adapter import BedrockAdapter
except ImportError:
    from bedrock_adapter import BedrockAdapter  # type: ignore

from pydantic import BaseModel


class SpecialistOutput(BaseModel):
    state: EvaluationState
    score: float | None = None
    rationale: str


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clients():
    import boto3
    return boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"]), boto3.client("s3")


def _query(table: Any, evaluation_id: str, prefix: str) -> list[dict[str, Any]]:
    return table.query(KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)", ExpressionAttributeValues={":pk": f"EVAL#{evaluation_id}", ":prefix": prefix}).get("Items", [])


def _ingest(event: dict[str, Any]) -> dict[str, Any]:
    table, s3 = _clients()
    evaluation_id, document_id = event["evaluation_id"], event["document_id"]
    key = {"pk": f"EVAL#{evaluation_id}", "sk": f"DOC#{document_id}"}
    document = table.get_item(Key=key, ConsistentRead=True).get("Item")
    if not document:
        raise ValueError("document not found")
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, document["file_name"])
        s3.download_file(os.environ["UPLOADS_BUCKET"], document["object_key"], path)
        chunks = parse_document(path, document_id, document["media_type"], document.get("vendor_id"), document.get("proposal_id"))
        with table.batch_writer() as batch:
            for chunk in chunks:
                batch.put_item(Item={"pk": f"EVAL#{evaluation_id}", "sk": f"CHK#{chunk.chunk_id}", "document_id": document_id, "payload": chunk.model_dump(mode="json"), "vendor_id": chunk.vendor_id, "proposal_id": chunk.proposal_id})
    table.update_item(Key=key, UpdateExpression="SET ingestion_status = :status, chunk_count = :count, processed_at = :at", ExpressionAttributeValues={":status": "READY", ":count": len(chunks), ":at": _now()})
    table.update_item(Key={"pk": f"EVAL#{evaluation_id}", "sk": f"JOB#{event['job_id']}"}, UpdateExpression="SET #status = :status, updated_at = :at", ExpressionAttributeNames={"#status": "status"}, ExpressionAttributeValues={":status": "COMPLETED", ":at": _now()})
    return {"job_id": event.get("job_id"), "status": "COMPLETED", "document_id": document_id, "chunk_count": len(chunks)}


def _extract_requirements(event: dict[str, Any]) -> dict[str, Any]:
    table, _ = _clients()
    evaluation_id = event["evaluation_id"]
    chunks = _query(table, evaluation_id, "CHK#")
    buyer_chunks = [item["payload"] for item in chunks if item["payload"].get("vendor_id") is None]
    requirements: list[Requirement] = []
    patterns = [
        ("availability", "TECH-01", "Availability commitment", RequirementCategory.TECHNICAL, EvaluationType.NUMERIC, r"(\d+\.\d+)\s*%", 99.99),
        ("residency", "COMP-01", "EU data residency", RequirementCategory.COMPLIANCE, EvaluationType.SEMANTIC, None, None),
        ("tco", "COMM-01", "Three-year total cost", RequirementCategory.COMMERCIAL, EvaluationType.FORMULA, None, 500000),
        ("cost", "COMM-01", "Three-year total cost", RequirementCategory.COMMERCIAL, EvaluationType.FORMULA, None, 500000),
    ]
    seen: set[str] = set()
    for chunk in buyer_chunks:
        text = chunk.get("text", "")
        lower = text.lower()
        for keyword, code, title, category, eval_type, regex, threshold in patterns:
            if keyword not in lower or code in seen:
                continue
            seen.add(code)
            requirements.append(Requirement(
                requirement_id=f"REQ_{uuid4().hex[:16]}", requirement_code=code, title=title,
                description=text[:500], category=category, mandatory=True, is_disqualifying=category is RequirementCategory.COMPLIANCE,
                weight=10, evaluation_type=eval_type, threshold=threshold,
                source_pointer=chunk["source_pointer"], validation_status="VALID",
            ))
    with table.batch_writer() as batch:
        for requirement in requirements:
            batch.put_item(Item={"pk": f"EVAL#{evaluation_id}", "sk": f"REQ#{requirement.requirement_id}", "payload": requirement.model_dump(mode="json")})
    table.update_item(Key={"pk": f"EVAL#{evaluation_id}", "sk": "META"}, UpdateExpression="SET #status = :status, requirement_count = :count", ExpressionAttributeNames={"#status": "status"}, ExpressionAttributeValues={":status": "READY_FOR_EVALUATION", ":count": len(requirements)})
    table.update_item(Key={"pk": f"EVAL#{evaluation_id}", "sk": f"JOB#{event['job_id']}"}, UpdateExpression="SET #status = :status, updated_at = :at", ExpressionAttributeNames={"#status": "status"}, ExpressionAttributeValues={":status": "COMPLETED", ":at": _now()})
    return {"job_id": event.get("job_id"), "status": "COMPLETED", "requirement_count": len(requirements)}


def _evaluate(event: dict[str, Any]) -> dict[str, Any]:
    table, _ = _clients()
    evaluation_id, run_id = event["evaluation_id"], event["run_id"]
    requirements = [Requirement.model_validate(item["payload"]) for item in _query(table, evaluation_id, "REQ#")]
    chunks = [item["payload"] for item in _query(table, evaluation_id, "CHK#")]
    vendor_chunks: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for chunk in chunks:
        vendor_id, proposal_id = chunk.get("vendor_id"), chunk.get("proposal_id")
        if vendor_id and proposal_id:
            vendor_chunks.setdefault((vendor_id, proposal_id), []).append(chunk)
    result_count = 0
    telemetry_totals = {"model_invocations": 0, "input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_write_input_tokens": 0, "end_to_end_latency_ms": 0}
    bedrock = BedrockAdapter() if os.environ.get("BEDROCK_MODEL_ID") else None
    with table.batch_writer() as batch:
        for requirement in requirements:
            for (vendor_id, proposal_id), scoped_chunks in vendor_chunks.items():
                claims = []
                conflict_pairs = []
                texts = " ".join(chunk.get("text", "") for chunk in scoped_chunks)
                lower = texts.lower()
                deterministic = None
                if requirement.requirement_code == "TECH-01":
                    values = [float(value) for value in re.findall(r"(\d+\.\d+)\s*%", texts)]
                    deterministic = numeric_threshold_check(operator=">=", required_value=requirement.threshold or 99.99, actual_value=max(values) if values else 0, unit="%") if values else None
                elif requirement.requirement_code == "COMM-01":
                    numbers = [float(value.replace(",", "")) for value in re.findall(r"(?:\$|USD\s*)([\d,]+)", texts, re.IGNORECASE)]
                    deterministic = tco_calculator(annual_license=numbers[0], implementation_fee=numbers[1], support_per_year=numbers[2], contract_years=3) if len(numbers) >= 3 else None
                if "eu" in lower or "europe" in lower:
                    claims.append({"claim_text": "The proposal references EU processing or hosting.", "relation": "supports", "confidence": 0.9, "source_pointer": next(chunk["source_pointer"] for chunk in scoped_chunks if "eu" in chunk.get("text", "").lower() or "europe" in chunk.get("text", "").lower())})
                if "processed in the us" in lower or "processed in us" in lower or "united states" in lower:
                    claims.append({"claim_text": "The proposal references processing in the United States.", "relation": "contradicts", "confidence": 0.9, "source_pointer": next(chunk["source_pointer"] for chunk in scoped_chunks if "us" in chunk.get("text", "").lower() or "united states" in chunk.get("text", "").lower())})
                try:
                    from .domain import EvidenceClaim
                except ImportError:
                    from domain import EvidenceClaim  # type: ignore
                evidence_claims = [EvidenceClaim(evidence_claim_id=f"EVC_{uuid4().hex[:16]}", **claim) for claim in claims]
                if len(evidence_claims) >= 2 and any(claim.relation == "supports" for claim in evidence_claims) and any(claim.relation == "contradicts" for claim in evidence_claims):
                    conflict_pairs = [new_conflict_pair(evidence_claims[0].evidence_claim_id, evidence_claims[1].evidence_claim_id, "DATA_RESIDENCY")]
                suggested_state = EvaluationState.SATISFIED if evidence_claims else EvaluationState.INSUFFICIENT_EVIDENCE
                suggested_score = 10 if evidence_claims else None
                rationale = "Deterministic or source-grounded fixture evaluation."
                if bedrock and requirement.evaluation_type is EvaluationType.SEMANTIC and not conflict_pairs and evidence_claims:
                    specialist, specialist_telemetry = bedrock.converse_json(
                        system_prompt="Return only the typed JSON assessment. Never invent evidence and abstain when the supplied source claims are insufficient.",
                        user_prompt=json.dumps({"requirement": requirement.description, "vendor_id": vendor_id, "proposal_id": proposal_id, "claims": [claim.model_dump(mode="json") for claim in evidence_claims]}, sort_keys=True),
                        output_model=SpecialistOutput,
                        static_context="VeriBid canonical states: SATISFIED, PARTIALLY_SATISFIED, NOT_SATISFIED, CONFLICTING_EVIDENCE, INSUFFICIENT_EVIDENCE.",
                        max_tokens=256,
                        enable_cache=os.environ.get("PROMPT_CACHE_ENABLED") == "true",
                        repair=lambda text: "Repair the previous output into JSON with exactly state, score, rationale fields. Output JSON only.",
                    )
                    suggested_state, suggested_score, rationale = specialist.state, specialist.score, specialist.rationale
                    for key in telemetry_totals:
                        value = getattr(specialist_telemetry, key)
                        if value is not None:
                            telemetry_totals[key] += value
                result = verify_candidate(evaluation_result_id=f"EVAL_{uuid4().hex[:16]}", requirement_id=requirement.requirement_id, vendor_id=vendor_id, proposal_id=proposal_id, suggested_state=suggested_state, suggested_score=suggested_score, max_score=10, rationale=rationale, claims=evidence_claims, conflict_pairs=conflict_pairs, deterministic_result=deterministic)
                result_id = result.evaluation_result_id
                batch.put_item(Item={"pk": f"EVAL#{evaluation_id}", "sk": f"RES#{result_id}", "run_id": run_id, "payload": result.model_dump(mode="json")})
                result_count += 1
    telemetry = {**telemetry_totals, "cache_read_input_tokens": telemetry_totals["cache_read_input_tokens"] or None, "cache_write_input_tokens": telemetry_totals["cache_write_input_tokens"] or None}
    table.put_item(Item={"pk": f"EVAL#{evaluation_id}", "sk": f"RUN#{run_id}", "run_id": run_id, "status": "COMPLETED", "progress": {"total_items": result_count, "completed_items": result_count, "failed_items": 0}, "telemetry": telemetry, "updated_at": _now()})
    table.update_item(Key={"pk": f"EVAL#{evaluation_id}", "sk": f"JOB#{run_id}"}, UpdateExpression="SET #status = :status, updated_at = :at", ExpressionAttributeNames={"#status": "status"}, ExpressionAttributeValues={":status": "COMPLETED", ":at": _now()})
    try:
        import boto3
        boto3.client("cloudwatch").put_metric_data(Namespace="VeriBid", MetricData=[
            {"MetricName": "RunCompleted", "Value": 1, "Unit": "Count"},
            {"MetricName": "ModelInvocations", "Value": telemetry["model_invocations"], "Unit": "Count"},
            {"MetricName": "CacheReadInputTokens", "Value": telemetry["cache_read_input_tokens"] or 0, "Unit": "Count"},
            {"MetricName": "CacheWriteInputTokens", "Value": telemetry["cache_write_input_tokens"] or 0, "Unit": "Count"},
        ])
    except Exception:
        # Metrics must not convert a completed evaluation into an execution failure.
        pass
    return {"run_id": run_id, "status": "COMPLETED", "result_count": result_count, "telemetry": telemetry}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    action = event.get("action")
    if action == "INGEST":
        return _ingest(event)
    if action == "EXTRACT_REQUIREMENTS":
        return _extract_requirements(event)
    if action == "EVALUATE":
        return _evaluate(event)
    raise ValueError(f"unsupported workflow action: {action}")
