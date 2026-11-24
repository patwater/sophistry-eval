# Proposal: tell the worker which Bash commands the night runner allows

Cause label: doc gap. `AGENT_LOOP.md` is protected, so that part is a proposal. The `Docs/night-shift.md` part is not protected, but triage may not edit docs, so it is included here for the next day agent or Patrick to apply.

## What happened on 2026-11-24

Four Bash calls were denied across the two tasks (see `permission_denials` in `night/runs/2026-11-24/task-1.json` and `task-2.json`):

- Task 1: `cd /home/runner/...; sed -i ... src/...` and `cd /home/runner/...; cat >> night/runs/2026-11-24/term-tracking/plan.md <<'EOF' ...`.
- Task 2: `grep -nE ... ; test -n "$ANTHROPIC_API_KEY" && ...` and `cat >> night/runs/2026-11-24/summary.md <<'EOF' ... python3 ... git add ... && git commit ...`.

Every denied command started with a prefix that is not in the runner's allowlist (`ALLOWED` in `runner/night_shift.sh`: `make`, `uv`, `python3`, `ls`, `mkdir`, and `git status|diff|log|add|commit|stash`). None of them was a random or flaky denial. Task 2 misread this as "the permission mode denied Bash after the first few commands", gave up on Bash, and left its `TODOS.md` edit uncommitted. That edit is still uncommitted in the working tree after the run.

The worker had no way to know the allowlist. It is not in `AGENT_LOOP.md`, `CLAUDE.md` or `Docs/night-shift.md`.

## Change 1: Docs/night-shift.md

Add this section after the description of what the runner does:

> ### What the worker may run
>
> Night tasks run with `--permission-mode dontAsk`, so any tool call outside the allowlist in `runner/night_shift.sh` is denied without asking. The allowed Bash commands are those starting with `make`, `uv`, `python3`, `ls`, `mkdir`, `git status`, `git diff`, `git log`, `git add`, `git commit` and `git stash`. The rule matches the start of the whole command line, so:
>
> - Do not prefix commands with `cd <dir>;`. The working directory is already the repo root.
> - Do not chain a disallowed command with `;`, `&&` or a pipe. Run one allowed command per Bash call.
> - Use the Read, Grep, Glob, Edit and Write tools instead of `cat`, `grep`, `sed -i`, heredocs or `echo >>`.
> - Do not inspect secret environment variables from Bash. A missing key shows up as a failed API call.
> - A denial means the command shape is outside the list. It does not mean Bash is switched off. Reshape the command and continue, and commit with a plain `git add <paths>` followed by `git commit -m ...`.

## Change 2: AGENT_LOOP.md

Add this bullet to "Working notes":

> - Bash is limited to the allowlist described in `Docs/night-shift.md` under "What the worker may run". Use one allowed command per call and the file tools for reading and editing. A denied command is a shape problem, so reshape it instead of abandoning Bash, and never end a task with uncommitted work.

## Optional validation (runner, protected)

If Patrick wants a check rather than only docs: have `runner/night_shift.sh` fail the task's summary line when `git status --porcelain` is non-empty after a task, and record the leftover paths in `night/runs/<date>/task-<n>-dirty.txt`. Tonight the dirty `TODOS.md` was only visible from the agent's own message.
