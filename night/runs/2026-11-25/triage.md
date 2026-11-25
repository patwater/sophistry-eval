# Triage for night 2026-11-25

## Needs your decision

1. **Can a night task make live model calls, and with what limit?** Live calls made through `ClaudeClient` are not in the ledger and do not count against the nightly cap. The recorded live run of `track_terms` is the only thing that will show whether the prompt works, and it has now been put off twice. The proposal in `queue/proposals/2026-11-25-worker-shell-permissions-doc.md` leaves a blank for your rule.
2. **Approve the shell-permissions doc proposal** (same file). Task 2 could not check for the API key because a compound shell command was denied, so it fell back to offline work.
3. **The e2e flag rule:** should the planted equivocation flag be required in every one of five runs, or in a majority? The night chose every run and recorded it as your call in `TODOS.md`.
4. **A carried-over item:** `queue/proposals/2026-11-21-claude-md-spec-reference.md` (CLAUDE.md still names the draft spec) is still waiting.
5. **The scoring step is not specified:** `score_text` cannot be built until the spec says how force, integrity and difficulty are scored. Until then the e2e test fails by design.

## What shipped

Both tasks shipped and are committed on `night/2026-11-25`, each with a CHANGELOG entry.

- **Task 1, term-tracking pass and annotation format (`9b01d44`).** This adds a versioned annotation JSON with code-point offsets and a text hash, strict quote anchoring, and `track_terms`. The plan was approved in round 3 and the diff in round 1. There are 171 passing tests.
- **Task 2, the open question 5 gate for the e2e test (`25e2606`).** This adds five runs per fixture, five checks reported together with their variance, and a matcher shared with the pass. The plan was approved in round 3 and the diff in round 1. There are 198 passing tests.

After each task, `make check` was clean apart from the one expected failure. That failure is `tests/test_e2e_metamorphic.py` raising `NotImplementedError` from `score_text`, which `AGENT_LOOP.md` allows. The runner's protected-path check passed after both tasks (it printed nothing and exited 0).

## What failed or was deferred, and why

- **The live run of `track_terms` was deferred (not a hard block).** Cause: **doc gap.** The worker's check, `[ -n "$ANTHROPIC_API_KEY" ] && echo ...; cat ...`, was denied under `dontAsk` because `[`, `echo` and `cat` are not on the allowlist. Nothing in `Docs/` explains the allowlist, the allowed way to check the key, or the spend policy for live calls. Proposal: `queue/proposals/2026-11-25-worker-shell-permissions-doc.md`.
- **A minor accuracy point.** Task 2's summary says `make protected` passes, but its own `make check ...; make protected` command was also denied. The runner's independent check did pass, so the claim holds, but the worker may not have verified it itself. The proposal above covers this too (one allowed command per call).

## Noise

No live model calls were made, so there are no repeated scored runs and no variance to look at. The failing e2e test is a `NotImplementedError` and has nothing to do with noisy scores.

## Cost

| Item | Cost (USD) | Turns |
|---|---|---|
| Task 1 | 2.83 | 9 |
| Task 2 | 3.13 | 53 |
| **Total** | **5.96** | |

The total is about 60% of the $10 cap that task 1 reported. The night stopped at the task cap (2), not the spend cap. One caveat: task 1's saved JSON came from a background task notification (`origin.kind` is `task-notification`), and 9 turns looks low for a task with six reviewer runs. The turn count, and possibly the cost, may be undercounted. The cost does match the model-usage total in the same file, so the dollar figure is probably right. Worth watching on the next night.
