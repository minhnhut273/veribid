---
name: veribid-agent-runtime
description: Use for VeriBid Bedrock prompts, retrieval, evaluator routing, Skeptical Verifier, structured outputs, prompt-cache telemetry, or deterministic tool delegation. Do not use for ordinary API/UI work without agent-runtime behavior.
---

# VeriBid Agent Runtime

Consult the AI / Agent Specification, Agent Orchestration document and Main Evaluation Sequence before changing runtime behavior. Preserve this topology:

`Requirement × Vendor × Proposal` -> vendor-scoped retrieval -> Router -> exactly one primary specialist -> deterministic tool when required -> Skeptical Verifier -> verified result -> Human Review.

Rules:

- Filter by both `vendor_id` and `proposal_id` before retrieval and preserve source metadata for every chunk.
- Route to Technical, Commercial or Compliance; do not implement free-form multi-agent voting or debate.
- Use semantic Bedrock reasoning for extraction and interpretation, but deterministic code for booleans, thresholds, SLA, TCO, formulas and weighted arithmetic.
- Require resolvable SourcePointers for factual claims. Missing or unresolvable support abstains as `INSUFFICIENT_EVIDENCE`; material sourced contradiction returns `CONFLICTING_EVIDENCE` with explicit `conflict_pairs`.
- Keep a stable RFP/rubric/shared-policy prefix before vendor evidence. Count a prompt-cache hit only when runtime telemetry reports cache-read usage; latency alone is not evidence.
- Validate structured output by type and invariant, attempt at most one bounded repair, then fail closed. Never map execution/schema failure to an evidentiary state.
- Keep raw model/provider payloads behind the agent/domain boundary and persist the exact evidence, verifier and telemetry trace needed by the API.
