---
name: veribid-doc-sync
description: Synchronize VeriBid specifications after an explicit contract change or a confirmed material cross-spec mismatch. Do not trigger merely because product code was changed.
---

# VeriBid Documentation Synchronization

Use the specifications under `Document/Phase_1/` as the source set. Identify the authority owner for the changed concern before editing anything:

- product scope: Product Brief / PRD;
- behavior and acceptance: Functional Requirements;
- entities and evidence semantics: Data + Evidence Model;
- agent behavior: AI / Agent Specification and Agent Orchestration;
- public boundary: API Contract;
- infrastructure: AWS System Architecture;
- lifecycle ordering: User Flow and Main Evaluation Sequence;
- gates and proof: Deployment + Test Checklist.

Update the owning contract first. Synchronize only affected downstream documents, preserve existing revision/version notes, and distinguish breaking API/schema/persistence/runtime drift from minor documentation drift. Never mass-rewrite every document, and never mutate Word/PDF/drawio artifacts just because a feature was coded without an explicit documentation request or confirmed contract change.
