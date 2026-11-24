# Night 2026-11-24 summary

## Task 1: term-tracking pass and annotation format — shipped

Source: `Specs/initial-build.md`, proposed answers 1 and 7. There were no `ready` bugs in `TODOS.md`. On 2026-11-21, task 2 planned this work but stopped after one review round, with nothing committed. Tonight's plan started from that one and was reviewed from scratch. The plan and the full review history are in `term-tracking/plan.md`.

What shipped:

- **`Annotation`** gains `start`, `end` and `source`:
  - offsets count Unicode code points into the exact input string;
  - a versioned, strict JSON form (`ANNOTATION_FORMAT = 1`).
- **`sophistry_eval.passes.common`:** `parse_json_object`, `anchor_quote` and `PassOutputError`.
- **`sophistry_eval.passes.term_tracking.track_terms`:**
  - one model call, returning a `TermReport`;
  - strict validation;
  - a system prompt free of fixture content.
- **Docs:**
  - the annotation format in `Docs/overview.md`;
  - the equivocation taxonomy and the immunizing move in `Docs/rubrics.md`;
  - the same-word-only limit in `Docs/testing-strategy.md`;
  - a corrected fixture README.

Reviews:

- **Plan:**
  - The architect approved in round 2.
  - The logician approved in round 3. It caught a part-whole example in the prompt that was the fixture's own move, a substring term match, overlapping quotes, and mislabelled fixture flaws.
- **Diff:**
  - Round 1: the architect found that `annotations_from_json` accepted `"format": 1.0`. It was fixed test-first and recorded in `POSTMORTEMS.md`. The logician approved.
  - Round 2: both approved.

Checks: `make check` is clean apart from the expected `tests/test_e2e_metamorphic.py` failure. 188 tests pass. No protected path was touched.

Deviation: the planned constant `PASS_NAME` is called `SOURCE`, because ruff's S105 rule read "PASS" as a password. Renaming beat suppressing the rule.

Not done, and logged in `TODOS.md`:

- Wiring the pass into `score_text`, which needs a scoring step that is not yet specified.
- Live runs of the pass on the fixtures. No live model calls were made in this task.

New questions for Patrick:

- The spec's near-synonym acceptance test conflicts with the pass's same-word limit.
- Is the scoring step the next spec?

## Task 2: no eligible task, so stopped without code changes

Step 0 passed. There was no `PAUSE` file. The leftover ledger row for task 1 was committed as `Record 2026-11-24 task 1 spend in the cost ledger`. `make check` reported 188 passed, with the only failure the expected `tests/test_e2e_metamorphic.py` one.

Step 1 found nothing to pick up:

- **`TODOS.md`** has no bugs marked `ready`.
- **`Specs/`** has one promoted spec, `initial-build.md`. Proposed answer 1 limits the first build to these pieces, and all of them are on the branch:
  - the term-tracking pass, shipped as task 1 tonight;
  - `ClaudeClient`, `RecordingClient` and `RecordedClient` in `src/sophistry_eval/client.py`;
  - the repeat-and-average helper in `tests/helpers/repeat.py`.
- **What's left in the spec** is wiring `score_text` and the end-to-end test. That needs a scoring step for force, integrity and difficulty, and no spec defines one yet. The remaining passes (claims, modal audit, presupposition load and the adversarial verifier) are explicitly left for later specs.

Agents do not write specs for Patrick, and the loop does not pick up backlog items unless they are marked `ready`. So no work was started, no plan was written, no reviews ran and no code changed.

To give the next night work, Patrick can do either of these:

- promote a spec for the scoring step;
- mark one or more `TODOS.md` backlog items `ready`. Candidates that need no new spec: the input-hash result cache, and recording live `track_terms` replies on the two equivocation fixtures.

Process note: this session's permission mode denied Bash after the first few commands. As a result, the summary and the `TODOS.md` note were written with file tools and are **not committed**. The runner or Patrick needs to commit them.
