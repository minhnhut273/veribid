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
CloudWatch form the serverless baseline. Bedrock is an optional semantic path
whose model and cache telemetry are verified at deployment time.

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

The authenticated production walkthrough and a measured Bedrock cache
benchmark are recorded under `docs/submission-proof/`. The benchmark used
provider-reported cache telemetry; production Lambda remains unconfigured for
Bedrock until a separate model-selection/deployment decision is approved.
