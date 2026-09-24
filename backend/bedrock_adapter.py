"""Bedrock Converse adapter with typed output and measurable cache telemetry."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel

try:
    from .domain import SchemaExecutionFailure
except ImportError:  # Lambda loads modules from the asset root.
    from domain import SchemaExecutionFailure  # type: ignore


@dataclass(frozen=True)
class BedrockTelemetry:
    model_invocations: int
    input_tokens: int | None
    output_tokens: int | None
    cache_read_input_tokens: int | None
    cache_write_input_tokens: int | None
    end_to_end_latency_ms: int | None


@dataclass(frozen=True)
class BedrockResponse:
    text: str
    telemetry: BedrockTelemetry
    request_id: str | None


class BedrockAdapter:
    """One model call boundary; model ID is supplied by deployment config."""

    def __init__(self, model_id: str | None = None, client: Any | None = None):
        self.model_id = model_id or os.environ.get("BEDROCK_MODEL_ID")
        if not self.model_id:
            raise ValueError("BEDROCK_MODEL_ID must be configured after account/model verification")
        if client is None:
            import boto3
            from botocore.config import Config
            client = boto3.client("bedrock-runtime", config=Config(retries={"max_attempts": 5, "mode": "adaptive"}))
        self.client = client

    def converse_text(self, *, system_prompt: str, user_prompt: str, static_context: str = "", max_tokens: int = 512, enable_cache: bool = False, cache_ttl: str | None = None) -> BedrockResponse:
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        system_blocks: list[dict[str, Any]] = []
        if static_context:
            system_blocks.append({"text": static_context})
            if enable_cache:
                cache_point: dict[str, Any] = {"type": "default"}
                if cache_ttl:
                    cache_point["ttl"] = cache_ttl
                system_blocks.append({"cachePoint": cache_point})
        if system_prompt:
            system_blocks.append({"text": system_prompt})
        request: dict[str, Any] = {
            "modelId": self.model_id,
            "messages": [{"role": "user", "content": [{"text": user_prompt}]}],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0},
        }
        if system_blocks:
            request["system"] = system_blocks
        response = self.client.converse(**request)
        usage = response.get("usage", {})
        return BedrockResponse(
            text="".join(block.get("text", "") for block in response.get("output", {}).get("message", {}).get("content", []) if "text" in block),
            telemetry=BedrockTelemetry(
                model_invocations=1,
                input_tokens=usage.get("inputTokens"),
                output_tokens=usage.get("outputTokens"),
                cache_read_input_tokens=usage.get("cacheReadInputTokens"),
                cache_write_input_tokens=usage.get("cacheWriteInputTokens"),
                end_to_end_latency_ms=None,
            ),
            request_id=response.get("ResponseMetadata", {}).get("RequestId"),
        )

    def converse_json(self, *, system_prompt: str, user_prompt: str, output_model: type[BaseModel], static_context: str = "", max_tokens: int = 768, enable_cache: bool = False, repair: Callable[[str], str] | None = None) -> tuple[BaseModel, BedrockTelemetry]:
        first = self.converse_text(system_prompt=system_prompt, user_prompt=user_prompt, static_context=static_context, max_tokens=max_tokens, enable_cache=enable_cache)
        try:
            return output_model.model_validate_json(_strip_json_fence(first.text)), first.telemetry
        except Exception as first_error:
            if repair is None:
                raise SchemaExecutionFailure("Bedrock structured output failed validation") from first_error
            repaired = self.converse_text(system_prompt=system_prompt, user_prompt=repair(first.text), static_context=static_context, max_tokens=max_tokens, enable_cache=enable_cache)
            try:
                return output_model.model_validate_json(_strip_json_fence(repaired.text)), BedrockTelemetry(
                    model_invocations=first.telemetry.model_invocations + repaired.telemetry.model_invocations,
                    input_tokens=_sum_optional(first.telemetry.input_tokens, repaired.telemetry.input_tokens),
                    output_tokens=_sum_optional(first.telemetry.output_tokens, repaired.telemetry.output_tokens),
                    cache_read_input_tokens=_sum_optional(first.telemetry.cache_read_input_tokens, repaired.telemetry.cache_read_input_tokens),
                    cache_write_input_tokens=_sum_optional(first.telemetry.cache_write_input_tokens, repaired.telemetry.cache_write_input_tokens),
                    end_to_end_latency_ms=None,
                )
            except Exception as second_error:
                raise SchemaExecutionFailure("Bedrock structured output failed after one repair") from second_error


def _strip_json_fence(text: str) -> str:
    cleaned = text.strip()
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()
    if not (cleaned.startswith("{") or cleaned.startswith("[")):
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
        if match:
            cleaned = match.group(1).strip()
    cleaned = re.sub(
        r'"(?:\\.|[^"\\])*"|,\s*([\}\]])',
        lambda match: match.group(0) if match.group(1) is None else match.group(1),
        cleaned,
    )
    json.loads(cleaned)  # fail early with a standard parsing error
    return cleaned


def _sum_optional(left: int | None, right: int | None) -> int | None:
    return left + right if left is not None and right is not None else None
