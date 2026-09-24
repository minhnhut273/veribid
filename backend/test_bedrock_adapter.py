import json

from pydantic import BaseModel
import pytest

from backend.bedrock_adapter import BedrockAdapter, _strip_json_fence
from backend.domain import SchemaExecutionFailure


class Output(BaseModel):
    state: str


class FakeBedrock:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def converse(self, **request):
        self.requests.append(request)
        return next(self.responses)


def response(text: str, read: int = 0, write: int = 0):
    return {"output": {"message": {"content": [{"text": text}]}}, "usage": {"inputTokens": 100, "outputTokens": 20, "cacheReadInputTokens": read, "cacheWriteInputTokens": write}, "ResponseMetadata": {"RequestId": "req-1"}}


def test_converse_sets_max_tokens_and_exposes_cache_usage():
    fake = FakeBedrock([response('{"state":"SATISFIED"}', read=80)])
    result = BedrockAdapter("verified-model-id", fake).converse_text(system_prompt="Return JSON", user_prompt="Evaluate", static_context="x" * 100, max_tokens=256, enable_cache=True)
    assert result.telemetry.cache_read_input_tokens == 80
    assert fake.requests[0]["inferenceConfig"]["maxTokens"] == 256
    assert any(block.get("cachePoint", {}).get("type") == "default" for block in fake.requests[0]["system"])


def test_structured_output_allows_one_repair_then_fails_closed():
    fake = FakeBedrock([response("not json"), response('{"state":"SATISFIED"}')])
    model, telemetry = BedrockAdapter("verified-model-id", fake).converse_json(system_prompt="", user_prompt="Evaluate", output_model=Output, repair=lambda text: "Return only valid JSON")
    assert model.state == "SATISFIED"
    assert telemetry.model_invocations == 2
    failing = FakeBedrock([response("bad"), response("still bad")])
    with pytest.raises(SchemaExecutionFailure):
        BedrockAdapter("verified-model-id", failing).converse_json(system_prompt="", user_prompt="Evaluate", output_model=Output, repair=lambda text: "Repair")


def test_json_cleanup_preserves_trailing_comma_like_text_inside_strings():
    raw = r'{"state":"SATISFIED","note":"literal ,} and ,] plus \"quoted\" text","items":[1,2,],}'
    cleaned = json.loads(_strip_json_fence(raw))

    assert cleaned == {
        "state": "SATISFIED",
        "note": 'literal ,} and ,] plus "quoted" text',
        "items": [1, 2],
    }
