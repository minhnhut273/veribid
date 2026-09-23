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

## Product workflow

Upload → Verify → Extract → Retrieve by proposal scope → Specialist evaluation
→ Skeptical Verifier → Evidence Matrix → Human Review → Markdown/PDF export.

## Architecture

Amplify, Cognito, API Gateway, Lambda, Step Functions, S3, DynamoDB and
CloudWatch form the serverless baseline. Bedrock is the configured semantic
path through the verified Claude Sonnet 4.5 global inference profile, with
provider prompt-cache support enabled and deterministic fallbacks kept
authoritative.

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

The authenticated production walkthrough, live CloudWatch telemetry and a
measured Bedrock cache benchmark are recorded under
`docs/submission-proof/`. The benchmark uses provider-reported cache telemetry;
the short production run is recorded separately and is not overstated as a
cache hit.
