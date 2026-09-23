# VeriBid submission claim register

Only claims classified `VERIFIED` are written as completed product facts in
`article.md`. `DESIGN-INTENT` describes diagrams or future product direction;
`BLOCKED` must not be presented as completed evidence.

| ID | Claim | Class | Evidence / boundary |
|---|---|---|---|
| C-01 | The public root and `/demo` are reachable over HTTP 200. | VERIFIED | `docs/submission-proof/01_live_app.md` |
| C-02 | Amplify job 6 succeeded and the stack reached `UPDATE_COMPLETE`. | VERIFIED | `02_amplify_deploy.md`, `03_aws_resources.md` |
| C-03 | The deployment action used the dedicated non-root `veribid-deploy` identity. | VERIFIED | `04_agent_connected.md`, `05_agent_aws_action.md` |
| C-04 | The fresh authenticated evaluation produced a 3 × 3 Evidence Matrix for three synthetic vendors. | VERIFIED | `07_evidence_matrix.md` |
| C-05 | Vendor A preserved both residency sides as `CONFLICTING_EVIDENCE` with `DATA_RESIDENCY · UNRESOLVED`. | VERIFIED | `08_source_grounding.md`, `09_contradiction.md` |
| C-06 | Vendor C abstained as `INSUFFICIENT_EVIDENCE — no resolvable source claim.` | VERIFIED | `10_abstention.md` |
| C-07 | Vendor B exposed `numeric_threshold_check · SATISFIED` as deterministic evidence. | VERIFIED | `11_deterministic_tool.md` |
| C-08 | ACCEPT, blocked empty-rationale OVERRIDE, and rationale-backed OVERRIDE were observed; the original suggestion remained. | VERIFIED | `12_human_review.md`, `13_audit_trace.md` |
| C-09 | Markdown and PDF export records reached READY; Markdown retained both conflict sides and source trace. | VERIFIED | `14_export.md` |
| C-10 | One controlled cold/warm pair reported 4,801 cache-write and 4,801 cache-read tokens. | VERIFIED | `15_prompt_cache.md`, `CACHE_BENCHMARK.md`; sample size one pair only |
| C-11 | The MVP supports text-based DOCX, text-layer PDF, and XLSX evidence. | VERIFIED | `SUBMISSION_DRAFT.md`, implementation audit; scanned/image-heavy PDF is out of scope |
| C-12 | Amplify, Cognito, API Gateway, Lambda, Step Functions, S3, DynamoDB, Bedrock, and CloudWatch are in the deployed baseline. | VERIFIED | `03_aws_resources.md`, `17_architecture_diagram.md` |
| C-13 | The architecture diagram in this package is an explanatory design asset, not AWS Console evidence. | DESIGN-INTENT | `assets/aws_architecture.svg`, `assets/dual_path.svg` |
| C-14 | p50/p95, production-wide cache hit rate, guaranteed savings, latency improvement, customer usage, or market size. | BLOCKED | No supporting measurement or customer evidence; do not publish as facts |
| C-15 | Scanned-PDF/Textract support, AgentCore, or a dedicated vector database are deployed MVP capabilities. | BLOCKED | Explicitly outside current MVP boundary |
| C-16 | The project is original and was not previously published. | BLOCKED | Requires user confirmation before Publish |
| C-17 | A local downloaded export file or real product screenshots are included in this repository package. | BLOCKED | Browser download/screenshot files were not captured; do not fabricate |

