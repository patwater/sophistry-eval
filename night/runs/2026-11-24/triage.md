# Triage for night 2026-11-24

## Needs Patrick's decision

1. Give the next night work. Nothing is eligible: no `ready` bugs, and the rest of `Specs/initial-build.md` needs a scoring step that no spec defines. Promote a scoring spec, mark a `TODOS.md` backlog item `ready`, or mark `score_text` and the end-to-end test as deferred. Until then every task will stop with no changes. See `queue/proposals/2026-11-24-empty-work-queue.md`.
2. Commit or discard the uncommitted `TODOS.md` edit on `night/2026-11-24`. Task 2 added a line under "NEEDS INPUT FROM PATRICK" but could not commit it, so it is not in the PR as pushed.
3. Approve or reject two new proposals: `2026-11-24-bash-allowlist-docs.md` (tell the worker which Bash commands are allowed) and `2026-11-24-empty-work-queue.md` (stop early when nothing is eligible).
4. Still pending from 2026-11-21: `queue/proposals/2026-11-21-claude-md-spec-reference.md`.
5. Answer the spec question task 1 raised. The first acceptance test asks term tracking to flag a near-synonym swap, but the v0.1 pass only flags shifts where the same word appears at both uses.

## What shipped

Task 1 shipped the term-tracking pass and a versioned annotation format in commit `c0aa9fc`. The plan was approved by both personas (architect in round 2, logician in round 3), and the diff was approved in round 2 after a test-first fix for a float `format` version, which was recorded in `POSTMORTEMS.md`. `make check` shows 188 passed and only the expected `tests/test_e2e_metamorphic.py` failure. No protected path was touched. No live model calls were made, so the pass has not been tried on real replies yet.

## What failed or was blocked, and why

- Task 2 was blocked with no eligible work. Cause: spec gap. The promoted spec's remaining acceptance tests depend on an unspecified scoring step. The task handled this correctly and cheaply. Proposal: `2026-11-24-empty-work-queue.md`.
- Four Bash calls were denied across both tasks, and task 2 left `TODOS.md` uncommitted as a result. Cause: doc gap. Each denied command began with a prefix outside the runner's allowlist (`cd ...;`, `grep`, `cat >>`), but the worker had no record of the allowlist and wrongly concluded Bash had been switched off. This is deterministic configuration, not a flaky runner. Proposal: `2026-11-24-bash-allowlist-docs.md`.
- The `tests/test_e2e_metamorphic.py` failure is the expected one. It raises `NotImplementedError` from `score_text` before any model call, so noisy model scores cannot explain it. There were no repeated runs and no score variance to check tonight.

## Cost

Worker spend was $5.03 ($4.76 for task 1 at 87 turns, $0.27 for task 2 at 12 turns). The actual `NIGHT_SPEND_CAP_USD` value is not in the run logs. Against the suggested $10 cap, that is about half. The run stopped on the task cap of 2, not the spend cap. Triage is capped separately at $1.

## Smaller notes

- Task 1 reports 87 turns while the runner passes `--max-turns 80` by default. Either the turn count includes something the limit does not, or the limit is not being enforced. This is worth a look before relying on it.
- `make check` exits with status 2 every night because of the expected end-to-end failure. That means the runner cannot tell a new failure from the expected one by exit status alone. Tonight I confirmed by reading the logs that the only failure was the expected one.

Note: the triage agent tried to write outside its boundary and those changes were reverted.
