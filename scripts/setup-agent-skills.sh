#!/usr/bin/env bash
set -euo pipefail

# Project-local VeriBid agent environment setup.
# This script never installs globally and never installs AWS tooling.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
SKILLS_CLI="${SKILLS_CLI:-skills@1.5.18}"

command -v npx >/dev/null 2>&1 || {
  echo "ERROR: npx is required to install verified project-local skills." >&2
  exit 1
}

mkdir -p \
  "${REPO_ROOT}/.codex" \
  "${REPO_ROOT}/.agents/skills" \
  "${REPO_ROOT}/scripts"

required_local_skills=(
  veribid-contract-guard
  veribid-doc-sync
  veribid-api-contract
  veribid-agent-runtime
  veribid-release-proof
)

for skill in "${required_local_skills[@]}"; do
  if [[ ! -f "${REPO_ROOT}/.agents/skills/${skill}/SKILL.md" ]]; then
    echo "ERROR: required local VeriBid skill is missing: ${skill}" >&2
    exit 1
  fi
done

install_skill() {
  local source="$1"
  local skill="$2"
  if [[ -f "${REPO_ROOT}/.agents/skills/${skill}/SKILL.md" ]]; then
    echo "Already present; preserving project-local ${skill}"
    return 0
  fi
  echo "Installing project-local ${skill} from ${source}"
  (
    cd "${REPO_ROOT}"
    npx --yes "${SKILLS_CLI}" add "${source}" \
      --agent codex \
      --copy \
      --yes \
      --skill "${skill}"
  )
}

# These names were verified before this script was written. Do not add AWS
# skills/MCP packages here, and do not replace unavailable names casually.
github_skills=(
  harness-engineering
  poka-yoke
  security-review
  agent-owasp-compliance
  pytest-coverage
  github-actions-efficiency
)
for skill in "${github_skills[@]}"; do
  install_skill "github/awesome-copilot" "${skill}"
done

install_skill "vercel-labs/agent-skills" "vercel-react-best-practices"
install_skill "vercel-labs/agent-skills" "web-design-guidelines"

echo "VeriBid project-local agent skills are ready."
echo "AWS Agent Toolkit/MCP was not installed by this script."
