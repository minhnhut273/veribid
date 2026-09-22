# Synthetic procurement fixtures

These controlled fixtures are safe for local and hackathon acceptance tests;
they contain no real supplier information.

| Package | Scope | Required signal |
|---|---|---|
| Buyer RFP | buyer | availability `>= 99.99%`, EU residency and three-year TCO limit `500000 USD` |
| Buyer rubric | buyer | TECHNICAL, COMMERCIAL and COMPLIANCE categories with weighted review |
| Vendor A | `VENDOR_A / PROPOSAL_A` | `99.90%`, EU statement plus US telemetry conflict, and `120000/40000/15000` USD inputs |
| Vendor B | `VENDOR_B / PROPOSAL_B` | `99.995%`, EU-only statement, and a passing TCO |
| Vendor C | `VENDOR_C / PROPOSAL_C` | missing or partial evidence to produce abstention |

The public `/demo` response is the precomputed read-only projection of this
scenario. Parser tests create minimal PDF/DOCX/XLSX documents in temporary
directories, preserving the same source-pointer and vendor-scope invariants.
