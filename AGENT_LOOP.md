# Night loop

Follow these steps in order for each task. A night run attempts a limited number of tasks (the runner sets the cap) and stops at the spend cap.

## Steps

0. Stop immediately if a file named `PAUSE` exists in the repo root. Then clean the working tree by committing or stashing leftovers. Run `make check` and fix any failures before taking new work. The one expected failure while the end-to-end test is unimplemented is `tests/test_e2e_metamorphic.py`. Do not hide it.
1. Pick the next task. Bugs in `TODOS.md` marked `ready` come first. After that, pick a spec in `Specs/` whose filename does not start with `draft-`.
2. Read the spec, the relevant pages in `Docs/`, and the relevant code.
3. Write a testing plan, write the tests, and run them. They should fail for the right reason.
4. Write an internal plan to `night/runs/<date>/<task>/plan.md`.
5. Run every review persona on the plan, each as a fresh subagent. Revise and repeat until all approve, up to three rounds. If they never approve, mark the task blocked in `night/runs/<date>/summary.md` and move on.
6. Implement the change and update `Docs/`. Run `make check` and the relevant tests until clean.
7. Run the full test suite to catch regressions.
8. Run the review personas on the implementation diff and loop until approved, up to three rounds.
9. Log unrelated issues in `TODOS.md`. Put any proposed change to a protected file in `queue/proposals/` as a new file instead of making it.
10. Add a `CHANGELOG.md` entry and write a detailed commit message that explains the why.
11. Move to the next task until the task cap, the spend cap or a hard block is reached. Then write a short summary to `night/runs/<date>/summary.md` and stop.

## Stop conditions

Stop the task and record why in the summary if any of these happens:

- Any edit to a protected path would be needed or has been made. Revert it and write a proposal.
- A failing check that three honest attempts cannot fix.
- A missing credential or an unreachable service.
- The spend cap or the turn limit.

## Working notes

- Scoring behavior must be validated with the tests described in `Docs/testing-strategy.md`, not by reading outputs and deciding they look fine.
- LLM scoring is noisy. When a test depends on model scores, use the repeat-and-average helper in `tests/helpers` once it exists, and report the variance in the plan.
- Keep the commit history stacked on the night branch, with one commit per task at minimum.
- Mistakes go in `POSTMORTEMS.md` with a cause and a process fix, and the process fix is made first.
