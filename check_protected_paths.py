#!/usr/bin/env python3
"""Fail when a diff touches a protected path.

Usage: check_protected_paths.py [--base REF] [--allow PATH ...]

Compares HEAD against BASE (committed changes), plus uncommitted and untracked files.
Exits 0 when clean, 1 when a protected path was touched, 2 on a usage or git error.
"""

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PATTERNS_FILE = REPO_ROOT / "checks" / "protected_paths.txt"


def load_patterns(path: Path) -> list[str]:
    lines = path.read_text().splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def is_protected(changed: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        return changed.startswith(pattern)
    return changed == pattern or fnmatch.fnmatch(changed, pattern)


def violations(changed: list[str], patterns: list[str]) -> list[str]:
    return sorted({c for c in changed if any(is_protected(c, p) for p in patterns)})


def git_lines(*args: str) -> list[str]:
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(f"git {' '.join(args)} failed: {result.stderr.strip()}\n")
        raise SystemExit(2)
    return [line for line in result.stdout.splitlines() if line]


def changed_files(base: str) -> list[str]:
    committed = git_lines("diff", "--name-only", f"{base}...HEAD")
    uncommitted = git_lines("diff", "--name-only", "HEAD")
    untracked = git_lines("ls-files", "--others", "--exclude-standard")
    return sorted(set(committed) | set(uncommitted) | set(untracked))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="main")
    args = parser.parse_args()

    found = violations(changed_files(args.base), load_patterns(PATTERNS_FILE))
    if found:
        sys.stderr.write("Protected paths were touched:\n")
        for item in found:
            sys.stderr.write(f"  {item}\n")
        sys.stderr.write("Revert these and write a proposal in queue/proposals/ instead.\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
