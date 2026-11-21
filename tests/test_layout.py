"""The repo layout that CLAUDE.md and checks/protected_paths.txt describe must actually exist.

A flat upload once put every file in the repo root, which silently broke every path in the
docs. This test fails loudly if that happens again.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "CLAUDE.md",
    "AGENT_LOOP.md",
    "REVIEW_PERSONAS.md",
    "CHANGELOG.md",
    "POSTMORTEMS.md",
    "TODOS.md",
    "Makefile",
    "pyproject.toml",
    ".gitignore",
    "Specs/README.md",
    "Specs/SPEC_TEMPLATE.md",
    "Docs/overview.md",
    "Docs/rubrics.md",
    "Docs/testing-strategy.md",
    "Docs/night-shift.md",
    "checks/protected_paths.txt",
    "checks/check_protected_paths.py",
    "runner/night_shift.sh",
    "runner/triage.sh",
    "runner/report.sh",
    "runner/parse_usage.py",
    ".github/workflows/night-shift.yml",
    ".claude/agents/architect.md",
    ".claude/agents/logician-rhetorician.md",
    ".claude/agents/night-triage.md",
    "corpus/urls.csv",
    "ledger/costs.csv",
    "src/sophistry_eval/pipeline.py",
    "tests/fixtures/equivocation/clean.txt",
    "tests/fixtures/equivocation/planted.txt",
]

REQUIRED_DIRS = [
    "corpus/public_domain",
    "corpus/cache",
    "queue/proposals",
    "queue/approvals",
    "night/runs",
]


@pytest.mark.parametrize("rel", REQUIRED_FILES)
def test_required_file_exists(rel: str) -> None:
    assert (ROOT / rel).is_file(), f"missing {rel}"


@pytest.mark.parametrize("rel", REQUIRED_DIRS)
def test_required_dir_exists(rel: str) -> None:
    assert (ROOT / rel).is_dir(), f"missing directory {rel}"


def test_no_stray_files_in_repo_root() -> None:
    """Only known top-level files may sit in the root. Everything else belongs in a folder."""
    allowed = {
        "CLAUDE.md",
        "AGENT_LOOP.md",
        "REVIEW_PERSONAS.md",
        "CHANGELOG.md",
        "POSTMORTEMS.md",
        "TODOS.md",
        "Makefile",
        "pyproject.toml",
        "uv.lock",
        "LICENSE",
        ".gitignore",
        "PAUSE",
        ".night.lock",
    }
    strays = sorted(p.name for p in ROOT.iterdir() if p.is_file() and p.name not in allowed)
    assert not strays, f"unexpected files in repo root: {strays}"
