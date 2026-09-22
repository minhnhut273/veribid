# VeriBid

VeriBid is an evidence-driven bid evaluation engine for the workflow:

`Upload -> Verify -> Human Review -> Defensible Export`

The public read-only demo is live at [main.d2jw7e2fbiu6od.amplifyapp.com](https://main.d2jw7e2fbiu6od.amplifyapp.com/).
The deployed public API health route is
[`/api/v1/health`](https://jzmjnr4tq4.execute-api.us-east-1.amazonaws.com/api/v1/health).

## Local checks

```powershell
.venv\Scripts\python.exe -m pytest backend -q
Push-Location frontend; npm ci; npm run build; npm run test; Pop-Location
Push-Location infra; npm ci; npm run build; npm run synth; Pop-Location
```

The authenticated `/app` workflow creates an evaluation, uploads buyer and
vendor PDF/DOCX/XLSX files directly to private S3 with a presigned PUT,
extracts typed requirements, starts the scoped evaluation workflow, presents
the Evidence Matrix, records Human Review, and downloads Markdown/PDF audit
exports. The public `/demo` path remains synthetic and read-only.

## Architecture

Amplify hosts the React application. Cognito protects the HTTP API, API
Gateway invokes the Python Lambda boundary, S3 stores private upload objects,
DynamoDB stores the aggregate and append-only evidence/review records, and
Step Functions invokes the bounded worker pipeline. Bedrock is optional at
deployment time until a currently available account/model pair is verified;
deterministic threshold and TCO tools remain authoritative regardless of model
availability.

The live foundation URL is [the Amplify application](https://main.d2jw7e2fbiu6od.amplifyapp.com/),
with [the public demo](https://main.d2jw7e2fbiu6od.amplifyapp.com/demo) and
[API health](https://jzmjnr4tq4.execute-api.us-east-1.amazonaws.com/api/v1/health).

## Security and limitations

S3 is private, uploads are verified with `HEAD` before asynchronous ingestion,
and authenticated routes scope records by Cognito subject and evaluation.
Vendor and proposal IDs remain paired through parsing and evaluation. The MVP
does not award a vendor, does not include marketplace/ERP/payment features,
and requires a deployment-time Bedrock access/model check before semantic AI
calls are enabled.

AWS deployment uses the project-local CDK CLI and the configured `my-aws`
profile. Never commit credentials, tokens, or complete presigned URLs.

## Contract and evidence

The authoritative specifications live under `Document/Phase_1/`. The active
implementation ledger is under `docs/implementation/`; release evidence belongs
under `docs/submission-proof/`. AI suggestions never autonomously award a
vendor, and every user-visible factual assessment must resolve to a
`SourcePointer` or abstain.
