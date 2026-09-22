# VeriBid

VeriBid is an evidence-driven bid evaluation engine for the workflow:

`Upload -> Verify -> Human Review -> Defensible Export`

The public read-only demo is live at [main.d2jw7e2fbiu6od.amplifyapp.com](https://main.d2jw7e2fbiu6od.amplifyapp.com/).
The deployed public API health route is
[`/api/v1/health`](https://jzmjnr4tq4.execute-api.us-east-1.amazonaws.com/api/v1/health).

## Local checks

```powershell
.venv\Scripts\python.exe -m pytest backend\test_health.py -q
Push-Location frontend; npm ci; npm run build; npm run test; Pop-Location
Push-Location infra; npm ci; npm run build; npm run synth; Pop-Location
```

AWS deployment uses the project-local CDK CLI and the configured `my-aws`
profile. Never commit credentials, tokens, or complete presigned URLs.

## Contract and evidence

The authoritative specifications live under `Document/Phase_1/`. The active
implementation ledger is under `docs/implementation/`; release evidence belongs
under `docs/submission-proof/`. AI suggestions never autonomously award a
vendor, and every user-visible factual assessment must resolve to a
`SourcePointer` or abstain.
