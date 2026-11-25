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
