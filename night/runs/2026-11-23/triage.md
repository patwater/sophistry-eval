# Night shift triage for 2026-11-23

## Needs your decision

1. **Decide how annotations feed the integrity score.** Nothing else in the promoted spec is buildable until you do, so the next night will idle like task 2 did. The proposal `queue/proposals/2026-11-23-scoring-rule-open-question.md` drafts it as open question 9 with three options. If you would rather not decide yet, mark a backlog item in `TODOS.md` as `ready` (the input-hash cache is the obvious one).
2. **Review and merge the term-tracking commit** `7cc0ef3` on `night/2026-11-23`. It is the first real pass and it changes the shared `Annotation` type (new `start`, `end` and `source` fields, and JSON format 1).
3. **Approve or reject three pending proposals:** the two new ones from tonight, and `2026-11-21-claude-md-spec-reference.md`, which is still waiting.
4. **Lower priority, in `TODOS.md`:** the fixture pair is weaker than assumed (the clean control has its own modal slip and force is not matched), so decide whether to qualify the e2e docstring, loosen `MAX_FORCE_CHANGE`, or replace the fixtures. There is also a small inflected-versus-derived wording point in the prompt.

## What shipped

Task 1 built the term-tracking pass, annotation format 1 with code-point offsets and a text hash, shared pass helpers, and rubric and overview docs. It finished the task that night 2026-11-21 stopped on. Both personas approved the plan and the diff, the logician only in round 3, the last round allowed. The reviews did real work: the logician caught a prompt-versus-validation mismatch that a round 1 fix had introduced, and found flaws in the fixture pair. `make check` shows 182 passing and one failure, the expected `tests/test_e2e_metamorphic.py`. The runner's protected-path check passed after both tasks.

## What failed or stalled, and why

- **Task 2, no eligible task. Cause: spec gap.** The only remaining work is the scoring step, and the spec never says how pass annotations become an integrity score. The worker correctly refused to invent the rule. Proposal: `2026-11-23-scoring-rule-open-question.md`.
- **Denied shell commands in both tasks. Cause: doc gap.** Each worker ran one chained command (using `;`, `&&`, `|`, `echo`, `tail` or `cat`) that the allowlist blocked. Both recovered, so nothing broke, but no doc tells the worker the rule. Proposal: `2026-11-23-worker-shell-allowlist-doc.md`. The same proposal records that persona subagents now work under `dontAsk` (10 ran tonight, none refused), so that "not verified" note can go.
- **The e2e test failure is not a regression and not noise.** It raises `NotImplementedError` because `score_text` is unbuilt. No live model calls were made tonight, so there are no repeated runs and no variance to check.

Minor note: `stop-reason.txt` says "task cap reached", although task 2 actually stopped for lack of work. The runner cannot tell the two apart. This does not need action now.

## Cost

Worker spend was $5.01 ($4.75 for task 1 and $0.26 for task 2). The cap appears to be $10, inferred from the worker's note and the suggested value in `Docs/night-shift.md`, so about half the cap went unused. Task 1 used 18 turns of an 80-turn limit.
