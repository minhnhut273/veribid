# VeriBid — Evidence-Driven Bid Evaluation Engine

`#commercial-potential` `#startup`

## Problem

Enterprise bid evaluation is spread across PDFs, spreadsheets and manual
review. Teams need a defensible chain from requirement to source evidence to a
human decision.

## Solution

VeriBid creates a scoped evaluation workspace, extracts atomic requirements,
keeps vendor/proposal evidence isolated, applies deterministic calculations,
and presents an Evidence Matrix for Human Review.

## Target user and commercial value

The initial customer is a procurement, compliance or security review team at
an enterprise or regulated mid-market organization that must compare several
vendor proposals against a common RFP and defend the decision later. VeriBid
reduces review time and audit risk by making every material conclusion
traceable to source evidence while keeping the final decision with a human
reviewer.

## Product workflow

Upload → Verify → Extract → Retrieve by proposal scope → Specialist evaluation
→ Skeptical Verifier → Evidence Matrix → Human Review → Markdown/PDF export.

## Architecture

Amplify, Cognito, API Gateway, Lambda, Step Functions, S3, DynamoDB and
CloudWatch form the serverless baseline. Bedrock is the configured semantic
path through the verified Claude Sonnet 4.5 global inference profile, with
provider prompt-cache support enabled and deterministic fallbacks kept
authoritative.

The coding agent is connected to the AWS environment through the repository's
AWS CLI/CDK workflow. It contributed to the deployed vertical slice by
inspecting the live stack, validating the public API and Amplify routes,
testing the authenticated workflow contracts, and recording deployment and
CloudWatch evidence. The semantic path uses Bedrock; the deterministic
Python/Lambda path owns thresholds, TCO and other arithmetic; the Skeptical
Verifier preserves contradictions or abstains when evidence is insufficient.

## Claim boundary

The system never autonomously awards a vendor. Numeric thresholds and TCO are
owned by deterministic tools; factual semantic claims require SourcePointers;
conflicts and insufficient evidence remain visible; a reviewer can accept or
override with rationale while the original system result remains preserved.

## Live references

- Application: https://main.d2jw7e2fbiu6od.amplifyapp.com/
- Public demo: https://main.d2jw7e2fbiu6od.amplifyapp.com/demo
- API health: https://jzmjnr4tq4.execute-api.us-east-1.amazonaws.com/api/v1/health
- GitHub: https://github.com/minhnhut273/veribid

The fresh post-remediation authenticated synthetic replay is recorded under
`docs/submission-proof/`: evaluation `EVL_4f323aba9796446f` completed the
three-vendor workflow, including conflict, abstention, deterministic evidence,
ACCEPT/OVERRIDE review and READY Markdown/PDF export records. The deployment
used the non-root `veribid-deploy` identity; Amplify job 6 succeeded and the
Step Functions run was `RUN_d35820c4850d472f`. The benchmark uses
provider-reported cache telemetry: one controlled cold/warm pair recorded
4,801 cache-write tokens and 4,801 cache-read tokens. This is not presented
as p50, p95, a production-wide hit rate or guaranteed cost savings.

Current format boundary: text-based DOCX, text-layer PDF and XLSX
workbook/sheet/row evidence are supported. Scanned or image-heavy PDF and
Textract are outside the current MVP.
