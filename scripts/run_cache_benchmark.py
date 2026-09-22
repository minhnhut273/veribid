"""Run a real cold/warm Bedrock prompt-cache benchmark.

This script refuses to invent measurements. It requires BEDROCK_MODEL_ID and
valid AWS credentials; the caller must verify model support and region first.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from backend.bedrock_adapter import BedrockAdapter


def main() -> int:
    model_id = os.environ.get("BEDROCK_MODEL_ID")
    if not model_id:
        raise SystemExit("BEDROCK_MODEL_ID is required; no benchmark was run")
    static_context = "VeriBid evidence evaluation contract. " * 600
    adapter = BedrockAdapter(model_id)
    samples = []
    for label in ("cold", "warm"):
        started = time.perf_counter()
        response = adapter.converse_text(
            system_prompt="Return one short sentence.",
            user_prompt="Assess the supplied evidence without inventing facts.",
            static_context=static_context,
            max_tokens=64,
            enable_cache=True,
            cache_ttl="5m",
        )
        telemetry = response.telemetry
        samples.append({"run": label, "elapsed_ms": round((time.perf_counter() - started) * 1000), "input_tokens": telemetry.input_tokens, "output_tokens": telemetry.output_tokens, "cache_read_input_tokens": telemetry.cache_read_input_tokens, "cache_write_input_tokens": telemetry.cache_write_input_tokens, "request_id_present": bool(response.request_id)})
    output = {"model_id": model_id, "samples": samples, "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
