# Proposal: handle an empty work queue before spending a task

Cause label: spec gap. `AGENT_LOOP.md` and `runner/night_shift.sh` are protected, so this is a proposal.

## What happened on 2026-11-24

Task 2 found no eligible work. `TODOS.md` has no bugs marked `ready`, and the one promoted spec, `Specs/initial-build.md`, has all of its first-build scope on the branch. What remains in that spec (wiring `score_text` and the end-to-end test) depends on a scoring step for force, integrity and difficulty that no spec defines. The task correctly stopped without code changes, at a cost of $0.27 and 12 turns.

The root gap is in the spec: `Specs/initial-build.md` lists acceptance tests that need a scoring step but does not specify one or mark it as out of scope. The loop gap is that `AGENT_LOOP.md` step 1 does not say what to do when nothing is eligible, so each further task spends money rediscovering the same answer.

## Change 1: for Patrick (spec, not an agent edit)

Either promote a spec for the scoring step, or edit `Specs/initial-build.md` to mark `score_text` and the end-to-end test as deferred to a named later spec. Alternatively, mark one or more `TODOS.md` backlog items `ready`. The worker named two that need no new spec: the input-hash result cache, and recording live `track_terms` replies on the two equivocation fixtures (the second needs a live API key and spend).

## Change 2: AGENT_LOOP.md step 1

Append to step 1:

> If no `ready` bug and no unfinished promoted spec remains, or the only unfinished parts depend on work no spec defines, do not start a task. Add one line to `night/runs/<date>/summary.md` saying what is blocked and on what, add the question to "NEEDS INPUT FROM PATRICK" in `TODOS.md` if it is not already there, commit both, and create the file `night/runs/<date>/NO_WORK` so the runner stops launching tasks.

## Change 3: runner/night_shift.sh

At the top of the task loop, next to the `PAUSE` check, add:

```bash
[ -e "$RUN_DIR/NO_WORK" ] && { STOP_REASON="no eligible work"; break; }
```

This turns tonight's pattern into one cheap task instead of one per remaining slot, and makes the stop reason say what actually happened.
