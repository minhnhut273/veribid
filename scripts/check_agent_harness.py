"""Validate the repository-local VeriBid agent harness.

This check intentionally uses only the Python standard library so it can run
before an application package, virtual environment, or CI provider exists.
It checks the operating contract and provenance of the vendored skills; it
does not validate product behavior or contact AWS/GitHub.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_LOCAL_SKILLS = {
    "veribid-contract-guard",
    "veribid-doc-sync",
    "veribid-api-contract",
    "veribid-agent-runtime",
    "veribid-release-proof",
}
REQUIRED_EXTERNAL_SKILLS = {
    "harness-engineering",
    "poka-yoke",
    "security-review",
    "agent-owasp-compliance",
    "pytest-coverage",
    "github-actions-efficiency",
    "vercel-react-best-practices",
    "web-design-guidelines",
}


def read_text(relative_path: str) -> str:
    path = ROOT / relative_path
    if not path.is_file():
        raise ValueError(f"missing required file: {relative_path}")
    return path.read_text(encoding="utf-8")


def main() -> int:
    errors: list[str] = []

    try:
        agents = read_text("AGENTS.md")
        sources = read_text(".agents/SOURCES.md")
        setup = read_text("scripts/setup-agent-skills.sh")
        lock = json.loads(read_text("skills-lock.json"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1

    required_agent_markers = (
        "VeriBid Repository Constitution",
        "Document/Phase_1/",
        "## Implementation and Shipping Mode",
        "authorized to implement application code",
        "python scripts/check_agent_harness.py",
    )
    for marker in required_agent_markers:
        if marker not in agents:
            errors.append(f"AGENTS.md is missing required marker: {marker}")

    if "AWS tooling is intentionally not duplicated" not in sources:
        errors.append(".agents/SOURCES.md must document the AWS tooling boundary")
    if "AWS Agent Toolkit/MCP was not installed" not in setup:
        errors.append("setup script must state that AWS tooling is not installed")
    if "never installs AWS tooling" not in setup:
        errors.append("setup script must keep the no-global-AWS-install rule")

    locked_skills = lock.get("skills")
    if not isinstance(locked_skills, dict):
        errors.append("skills-lock.json must contain a skills object")
        locked_skills = {}

    for skill in sorted(REQUIRED_LOCAL_SKILLS | REQUIRED_EXTERNAL_SKILLS):
        skill_path = ROOT / ".agents" / "skills" / skill / "SKILL.md"
        if not skill_path.is_file():
            errors.append(f"missing vendored skill entrypoint: {skill_path.relative_to(ROOT)}")
        if skill in REQUIRED_LOCAL_SKILLS and f"`{skill}`" not in sources:
            errors.append(f".agents/SOURCES.md has no provenance entry for: {skill}")
        if skill in REQUIRED_EXTERNAL_SKILLS and skill not in locked_skills:
            errors.append(f"skills-lock.json has no entry for: {skill}")

    for relative_path in (
        "docs/implementation/STATUS.md",
        "docs/implementation/EXECUTION_PLAN.md",
        "docs/implementation/DECISIONS.md",
        "docs/submission-proof/README.md",
        "docs/harness/adoption-report.md",
    ):
        if not (ROOT / relative_path).is_file():
            errors.append(f"missing harness/documentation surface: {relative_path}")

    if errors:
        print("FAIL: agent harness validation")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS: VeriBid repository-local agent harness is structurally valid")
    print(f"- local skills checked: {len(REQUIRED_LOCAL_SKILLS)}")
    print(f"- external skills checked: {len(REQUIRED_EXTERNAL_SKILLS)}")
    print("- product implementation and AWS state were not inspected by this check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
