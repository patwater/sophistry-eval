# Proposal: document the worker's shell allowlist, and refresh stale night-shift notes

Cause label: doc gap. Source: night 2026-11-23, tasks 1 and 2.

The triage agent may not edit `Docs/`, so this is a proposal. `Docs/night-shift.md` is not a protected path, so a day session or the next night can apply it directly once approved.

## What happened

Both worker invocations had a Bash call denied by the permission system (`permission_denials` in `night/runs/2026-11-23/task-1.json` and `task-2.json`):

- Task 1: `make protected; echo "exit=$?"; uv run ruff check . && uv run ruff format --check . | tail -1; git status --short`
- Task 2: `cat >> night/runs/2026-11-23/summary.md <<'EOF' ... EOF` followed by `git add ... && git commit ...`

Each started with or contained commands outside the allowlist in `runner/night_shift.sh` (`echo`, `tail`, `cat`), chained with `;`, `&&` and `|`. The workers recovered (task 1's protected check was confirmed by the runner, and task 2 later committed `c62ea5f`), so nothing failed, but each denial costs turns and money and could hide a skipped check. The worker had no way to know the rule, because no doc states it.

## Change

1. In `Docs/night-shift.md`, under "How a night works", add:

   > Worker shell access is an allowlist (see `ALLOWED` in `runner/night_shift.sh`): `make`, `uv`, `python3`, `ls`, `mkdir`, and `git status`, `diff`, `log`, `add`, `commit`, `stash`. Run one allowed command per Bash call. Do not chain with `;`, `&&` or `|`, and do not use `cat`, `echo`, `tail` or heredocs. Use the Write or Edit tool to create or append to files, and `git commit -F <file>` with a message file written by Write. A denied command is reported in the invocation's `permission_denials`, which triage reads.

2. In the same file, update "Not verified": the subagent tool does work under `dontAsk` with the current list. Task 1 on 2026-11-23 spawned 10 persona subagents (4 architect, 6 logician-rhetorician) with none refused. Remove that bullet or mark it verified with the date.

3. In "Not built yet", replace "the first night shift builds it from the promoted spec" with "term tracking shipped on 2026-11-23; the scoring step waits on the open question about how annotations become integrity".

Optionally, also add one line to the "Working notes" in `AGENT_LOOP.md` (protected, so Patrick applies it): "Shell access is an allowlist; see `Docs/night-shift.md` before running Bash."

## Why

The fix is a doc fix, not a widening of the allowlist. The allowlist is deliberately narrow, and the worker should adapt to it rather than the runner loosening it.
