# Submission asset manifest

Security rule: inspect every asset before upload. Remove secrets, JWTs,
presigned URLs, account identifiers, and confidential vendor material.

| Asset | Type | Status | Intended use | Source / next action |
|---|---|---|---|---|
| `cover.png` | real product screenshot | BLOCKED | Builder cover / hero | Capture redacted Evidence Matrix view from the live app |
| `conflict_story.png` | real product screenshot | BLOCKED | Vendor A contradiction | Capture both excerpts and SourcePointers from authenticated UI |
| `evidence_matrix.png` | real product screenshot | BLOCKED | Matrix section | Capture the fresh 3 × 3 matrix with synthetic data only |
| `abstention.png` | real product screenshot | BLOCKED | Vendor C section | Capture explicit `INSUFFICIENT_EVIDENCE` detail |
| `dual_path.svg` / `dual_path.png` | explanatory diagram | READY | Semantic vs deterministic path | SVG source plus rendered PNG; generated from verified architecture/contract boundaries; not console evidence |
| `aws_architecture.svg` / `aws_architecture.png` | explanatory diagram | READY | AWS architecture section | SVG source plus rendered PNG; generated from deployed service inventory and architecture proof |
| `coding_agent_aws.png` | redacted proof screenshot | BLOCKED | Development story | Capture CI/deployment proof without account IDs or credentials |
| `prompt_cache.png` | telemetry proof screenshot | BLOCKED | Cache section | Capture/redact provider telemetry or use the text-only claim |
| `human_review_export.png` | real product screenshot | BLOCKED | Review/export section | Capture review state and export trace from synthetic evaluation |

No blocked asset is represented as a completed screenshot in the article. The
two SVGs are safe explanatory visuals and are clearly classified as
`DESIGN-INTENT` in the claim register.

The rendered PNG diagrams are committed and publicly reachable from the
repository. Builder preview image rendering remains unverified until the
platform's native image upload or a visible image node is confirmed.
