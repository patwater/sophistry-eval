# Night 2026-11-25 summary

## Task 1: term-tracking pass and annotation format — shipped

Source: `Specs/initial-build.md`, proposed answers 1 and 7. There were no `ready` bugs in `TODOS.md`. This picks up the 2026-11-21 task 2 plan. That plan had one review round and then stopped at the spend cap, with nothing implemented. The plan, the review history and the deviations are in `term-tracking/plan.md`.

What shipped:

- `Annotation` gains `start` and `end` (Unicode code-point offsets into the exact input text) and a required `source`, with validation.
  - The serialized form is version 1: `{"format", "text_sha256", "annotations"}`, through `annotations_to_json` and `annotations_from_json`.
  - The reader refuses another format, missing keys, wrong types and a hash mismatch.
- `sophistry_eval.passes.common`: `PassOutputError`, `parse_json_object` and `anchor_quote`. A quote that is missing or ambiguous is rejected, never guessed.
- `sophistry_eval.passes.term_tracking.track_terms(text, *, client, system_prompt=...) -> TermReport`.
  - The report holds the terms, the equivocations (both uses anchored) and the annotations (anchored at the shifted use, with `source="term_tracking"`).
  - Validation is strict. Quotes must be unique, contain the term as a whole word, and not overlap, and the two senses must differ.
- Docs:
  - `Docs/overview.md` covers the annotation format, the offset unit and the status.
  - `Docs/rubrics.md` covers term tracking versus a part-whole slide.
  - The fixture README and the e2e docstring now state that the fixture pair is confounded on force and difficulty.

Reviews:

- Plan:
  - Round 1 was on 2026-11-21.
  - In round 2, both personas asked for changes:
    - the offset unit;
    - `text_sha256`;
    - the span rule changed to no overlap;
    - a whole-word match;
    - a narrower figures exclusion;
    - the force confound documented.
  - Both approved in round 3.
- Diff: both approved in round 1. One optional test tightening was applied.

Checks: `make check` is clean apart from the expected `tests/test_e2e_metamorphic.py` failure. 171 tests pass. No protected path was touched, and `make protected` passes.

Not done, and logged in `TODOS.md`:

- Wiring the pass into `score_text`, which needs a scoring step the spec does not describe yet.
- A purer fixture pair.
- Equivocations carried by a near-synonym or a pronoun.
- A first live recorded run on the fixtures.

**No live model calls were made**, so no variance is reported. The prompt has not yet been tested against a real model.

## Task 2: the open question 5 gate in the end-to-end test — shipped

Source: `Specs/initial-build.md`, proposed answer 5, and the `TODOS.md` backlog item asking for the e2e test to use the repeat helper. There were no `ready` bugs. Plan, review history and one deviation are in `e2e-gate/plan.md`.

Why this task and not the recorded live run of `track_terms`: this session could not confirm that the API key was available, so I chose the offline item. The live run stays in `TODOS.md`.

What shipped:

- `tests/helpers/metamorphic.py`:
  - `score_runs` (five runs, every `Evaluation` kept);
  - `planted_flaw_failures`, with five checks, all reported at once with `Stat.summary()` variance lines:
    - no equivocation in any clean run;
    - an equivocation quoting "efficiency" in every planted run;
    - an integrity drop of at least 0.15;
    - the strict 2σ `clears_noise` gate;
    - force within 0.15.
- `tests/test_e2e_metamorphic.py` uses the gate. It still fails with `NotImplementedError`, as expected.
- `summarize_scores` was added to the repeat helper.
- The whole-word matcher is shared between the term-tracking pass and the gate (`passes.common.contains_whole_word`).
- Docs and TODOS were updated. The fixture README now describes the planted part-whole slide correctly ("the whole community" is only in `clean.txt`).

Reviews:

- Plan:
  - The Architect asked for changes in round 1 (cache, client and cost) and approved in round 2.
  - The Logician asked for changes in rounds 1 and 2 and approved in round 3. Its requests were:
    - anchor the planted flag on the term, and state that this is necessary but not sufficient;
    - exact boundary and message assertions;
    - share the matcher;
    - label the every-run flag rule as an interpretation, not part of answer 5.
- Diff: both approved in round 1. The non-blocking notes were applied.

Checks: `make check` is clean apart from the expected `tests/test_e2e_metamorphic.py` failure. 198 tests pass. `make protected` passes.

New questions for Patrick in `TODOS.md`: should the e2e flag rule require every run or a majority? New backlog item: let the e2e test choose its client (live, recorded or comparison model). Note that one e2e run will make 10 `score_text` calls.

**No live model calls were made**, so no variance is reported.
