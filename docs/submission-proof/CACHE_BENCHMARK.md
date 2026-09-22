# Prompt Cache Benchmark

Status: NOT RUN — no measured cache telemetry is claimed.

Run `python scripts/run_cache_benchmark.py` only after verifying the selected
Bedrock model, region, prompt-cache support and credentials. Record the exact
model ID and the two actual `cacheWriteInputTokens` / `cacheReadInputTokens`
responses. A repeated request is not evidence of a hit unless the provider
usage fields report the cache read.
