# VeriBid Agent Skill Provenance

This manifest records the project-local agent environment. External skills are vendored into `.agents/skills/`; AWS tooling is intentionally not duplicated.

## Local VeriBid skills

| Skill | Type | Source | Purpose |
|---|---|---|---|
| `veribid-contract-guard` | Local VeriBid | Authored in this repository | Protect domain, evidence, state, review and audit invariants. |
| `veribid-doc-sync` | Local VeriBid | Authored in this repository | Synchronize the owning specification after an explicit contract change. |
| `veribid-api-contract` | Local VeriBid | Authored in this repository | Protect the `/api/v1` DTO, async, upload, idempotency and review boundary. |
| `veribid-agent-runtime` | Local VeriBid | Authored in this repository | Protect retrieval, specialist, verifier, schema and deterministic-tool behavior. |
| `veribid-release-proof` | Local VeriBid | Authored in this repository | Execute P0/P1 release validation and safe submission-proof capture. |

## External vendored skills

Installation method for the successful installs: `npx skills@1.5.18 add <source> --agent codex --copy --yes --skill <name>`.

| Skill | Provider/source | Verified revision | Purpose |
|---|---|---|---|
| `harness-engineering` | GitHub `github/awesome-copilot` | `db8d563aefebf9dd569bc72596c4ebd817847534` | Build deterministic engineering harnesses and checks. |
| `poka-yoke` | GitHub `github/awesome-copilot` | `db8d563aefebf9dd569bc72596c4ebd817847534` | Prevent invalid states and make contract violations hard to introduce. |
| `security-review` | GitHub `github/awesome-copilot` | `db8d563aefebf9dd569bc72596c4ebd817847534` | Review implementation security risks. |
| `agent-owasp-compliance` | GitHub `github/awesome-copilot` | `db8d563aefebf9dd569bc72596c4ebd817847534` | Apply agent-specific OWASP security checks. |
| `pytest-coverage` | GitHub `github/awesome-copilot` | `db8d563aefebf9dd569bc72596c4ebd817847534` | Measure Python test coverage when Python code exists. |
| `github-actions-efficiency` | GitHub `github/awesome-copilot` | `db8d563aefebf9dd569bc72596c4ebd817847534` | Improve GitHub Actions efficiency when CI exists. |
| `vercel-react-best-practices` | Vercel `vercel-labs/agent-skills` | `063bee94c3f4df8453406c830b0a7df0f2860278` | Apply React/Next.js performance guidance when a frontend exists. |
| `web-design-guidelines` | Vercel `vercel-labs/agent-skills` | `063bee94c3f4df8453406c830b0a7df0f2860278` | Review web UI/accessibility when a frontend exists. |

`skills-lock.json` records installer content hashes for the installed external skills. The setup script uses the current upstream revision available at execution time because the current `skills` CLI does not expose a verified ref-pinning flag; reruns therefore require reviewing upstream drift.

## Requested but unavailable or deferred

- `gh-cli`: not present under the verified `github/awesome-copilot` skill catalog at revision `db8d563aefebf9dd569bc72596c4ebd817847534`; no substitute was installed.
- Microsoft `playwright-cli`: the official repository exposes the skill and was verified at `74354ecc7a43da16d91a9bc54fa8db8283a3fcf5`, but this checkout has no frontend/package manifest or existing Playwright dependency. `@playwright/cli` and the project-local Playwright skill were therefore deferred rather than added to an undefined package boundary.

## Existing tooling intentionally reused

The configured AWS CLI profile `my-aws` and existing AWS/Codex skill integrations were detected and reused for read-only verification. This setup does not install AWS Agent Toolkit, AWS MCP, AWS skills, credentials, or duplicate configuration.
