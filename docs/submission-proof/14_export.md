# 14 Export

Status: UNPROVEN current deployment.

The local export renderer now includes both conflict sides, claim IDs, SourcePointer traceability and verifier rationale, and the PDF writer paginates all lines. The Python regression/direct smoke checks were not runnable because `pytest` and `pydantic` are absent locally; the current patch has not been deployed or downloaded from production.
