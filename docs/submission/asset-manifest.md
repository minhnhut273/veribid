# Submission asset manifest

Security rule: inspect every asset before upload. Remove secrets, JWTs,
presigned URLs, account identifiers, and confidential vendor material.

| Asset | Type | Status | Intended use | Source / next action |
|---|---|---|---|---|
| `cover.png` | illustrative evidence card | READY_WITH_BOUNDARY | Builder cover / hero | Generated from verified matrix/conflict values; replace or augment with a real app capture |
| `conflict_story.png` | illustrative evidence card | READY_WITH_BOUNDARY | Vendor A contradiction | Generated from verified excerpts and SourcePointers; not a UI screenshot |
| `evidence_matrix.png` | illustrative evidence card | READY_WITH_BOUNDARY | Matrix section | Generated from the verified 3 × 3 synthetic fixture; not a UI screenshot |
| `abstention.png` | illustrative evidence card | READY_WITH_BOUNDARY | Vendor C section | Generated from verified `INSUFFICIENT_EVIDENCE`; not a UI screenshot |
| `dual_path.svg` / `dual_path.png` | explanatory diagram | READY | Semantic vs deterministic path | SVG source plus rendered PNG; generated from verified architecture/contract boundaries; not console evidence |
| `aws_architecture.svg` / `aws_architecture.png` | explanatory diagram | READY | AWS architecture section | SVG source plus rendered PNG; generated from deployed service inventory and architecture proof |
| `coding_agent_aws.png` | evidence card | READY_WITH_BOUNDARY | Development story | Generated from verified delivery episodes; not a CI screenshot |
| `prompt_cache.png` | evidence card | READY_WITH_BOUNDARY | Cache section | Generated from verified provider telemetry; not a CloudWatch screenshot |
| `human_review_export.png` | evidence card | READY_WITH_BOUNDARY | Review/export section | Generated from verified review/export records; not a UI screenshot |

No evidence card is represented as a completed screenshot in the article. The
SVG/PNG visuals are explanatory assets and are clearly classified as
`DESIGN-INTENT` in the claim register.

The rendered PNG diagrams are committed and publicly reachable from the
repository. Builder preview image rendering remains unverified until the
platform's native image upload or a visible image node is confirmed.
