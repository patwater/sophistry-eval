import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def _load_checker() -> ModuleType:
    path = Path(__file__).parent.parent / "checks" / "check_protected_paths.py"
    spec = importlib.util.spec_from_file_location("check_protected_paths", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load_checker()
PATTERNS = checker.load_patterns(checker.PATTERNS_FILE)


@pytest.mark.parametrize(
    "path",
    [
        "CLAUDE.md",
        "AGENT_LOOP.md",
        ".claude/agents/architect.md",
        "runner/night_shift.sh",
        ".github/workflows/night-shift.yml",
        "checks/check_protected_paths.py",
        "Makefile",
        ".env.local",
        "queue/approvals/2026-11-21-approve.md",
    ],
)
def test_protected_paths_are_flagged(path: str) -> None:
    assert checker.violations([path], PATTERNS) == [path]


@pytest.mark.parametrize(
    "path",
    [
        "src/sophistry_eval/pipeline.py",
        "tests/test_types.py",
        "Docs/overview.md",
        "queue/proposals/2026-11-21-fix.md",
        "TODOS.md",
        "night/runs/2026-11-21/summary.md",
    ],
)
def test_ordinary_paths_are_allowed(path: str) -> None:
    assert checker.violations([path], PATTERNS) == []
