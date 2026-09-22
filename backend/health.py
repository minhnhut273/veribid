"""Public API health endpoint for the VeriBid deployment baseline."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json",
            "cache-control": "no-store",
            "access-control-allow-origin": "*",
        },
        "body": json.dumps(body, separators=(",", ":")),
    }


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route the public, read-only baseline endpoints."""
    path = event.get("rawPath") or event.get("path") or "/api/v1/health"
    if path == "/api/v1/demo":
        return _response(200, {"data": _demo_fixture(), "meta": {"read_only": True, "synthetic": True}})
    if path != "/api/v1/health":
        return _response(404, {"error": {"code": "NOT_FOUND", "message": "Route not found"}})
    return _response(200, {
        "data": {
            "service": os.getenv("SERVICE_NAME", "veribid-api"),
            "version": os.getenv("SERVICE_VERSION", "unknown"),
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "meta": {"request_id": getattr(context, "aws_request_id", None)},
    })


def _demo_fixture() -> dict[str, Any]:
    """A synthetic public fixture that retains source-grounding metadata."""
    requirements = [
        {"id": "req-availability", "text": "Monthly availability must be at least 99.99%.", "category": "TECHNICAL"},
        {"id": "req-residency", "text": "Customer data must remain in the EU.", "category": "COMPLIANCE"},
        {"id": "req-tco", "text": "Three-year total cost must not exceed 500,000 USD.", "category": "COMMERCIAL"},
    ]
    vendors = [
        {"vendor_id": "vendor-a", "name": "Northstar Cloud"},
        {"vendor_id": "vendor-b", "name": "Helix Systems"},
        {"vendor_id": "vendor-c", "name": "Juniper Works"},
    ]
    matrix = [
        {"requirement_id": "req-availability", "vendor_id": "vendor-a", "state": "NOT_SATISFIED", "confidence": 0.99, "source_pointers": [{"document_id": "vendor-a-proposal", "page": 12, "locator": "SLA table"}]},
        {"requirement_id": "req-availability", "vendor_id": "vendor-b", "state": "SATISFIED", "confidence": 0.98, "source_pointers": [{"document_id": "vendor-b-proposal", "page": 8, "locator": "Availability commitment"}]},
        {"requirement_id": "req-availability", "vendor_id": "vendor-c", "state": "INSUFFICIENT_EVIDENCE", "confidence": 0.12, "source_pointers": []},
        {"requirement_id": "req-residency", "vendor_id": "vendor-a", "state": "CONFLICTING_EVIDENCE", "confidence": 0.93, "source_pointers": [{"document_id": "vendor-a-proposal", "page": 4, "locator": "EU residency"}, {"document_id": "vendor-a-security", "page": 2, "locator": "Telemetry processing"}], "conflict_pairs": [{"left": "EU-only processing", "right": "Telemetry processed in US"}]},
        {"requirement_id": "req-residency", "vendor_id": "vendor-b", "state": "SATISFIED", "confidence": 0.91, "source_pointers": [{"document_id": "vendor-b-security", "page": 6, "locator": "Data regions"}]},
        {"requirement_id": "req-residency", "vendor_id": "vendor-c", "state": "NOT_SATISFIED", "confidence": 0.87, "source_pointers": [{"document_id": "vendor-c-proposal", "page": 19, "locator": "Hosting locations"}]},
        {"requirement_id": "req-tco", "vendor_id": "vendor-a", "state": "SATISFIED", "confidence": 1.0, "source_pointers": [{"document_id": "vendor-a-pricing", "page": 3, "locator": "Three-year TCO"}], "deterministic_result": {"total_usd": 445000}},
        {"requirement_id": "req-tco", "vendor_id": "vendor-b", "state": "SATISFIED", "confidence": 1.0, "source_pointers": [{"document_id": "vendor-b-pricing", "page": 3, "locator": "Three-year TCO"}], "deterministic_result": {"total_usd": 468000}},
        {"requirement_id": "req-tco", "vendor_id": "vendor-c", "state": "INSUFFICIENT_EVIDENCE", "confidence": 0.05, "source_pointers": []},
    ]
    return {"evaluation_id": "demo-evaluation-001", "title": "Cloud platform procurement — public fixture", "status": "HUMAN_REVIEW", "requirements": requirements, "vendors": vendors, "matrix": matrix}
