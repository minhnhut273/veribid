# Prompt Cache Benchmark

Status: PASS — provider telemetry confirmed a cold write and warm read.

Run `python scripts/run_cache_benchmark.py` only after verifying the selected
Bedrock model, region, prompt-cache support and credentials. Record the exact
model ID and the two actual `cacheWriteInputTokens` / `cacheReadInputTokens`
responses. A repeated request is not evidence of a hit unless the provider
usage fields report the cache read.

Executed 2026-09-23 UTC with AWS profile `my-aws` and model
`global.anthropic.claude-sonnet-4-5-20250929-v1:0`:

| Run | Elapsed | inputTokens | outputTokens | cacheWriteInputTokens | cacheReadInputTokens |
|---|---:|---:|---:|---:|---:|
| cold | 9282 ms | 21 | 16 | 4801 | 0 |
| warm | 2239 ms | 21 | 16 | 0 | 4801 |

Both responses included a Bedrock request ID. The warm request is treated as
a cache hit because the provider returned `cacheReadInputTokens=4801`; latency
is recorded only as a secondary observation.
