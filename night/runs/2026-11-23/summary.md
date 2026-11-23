# Night 2026-11-23 summary

## Task 1: term-tracking pass and annotation format 1 — shipped

Source: `Specs/initial-build.md`, proposed answers 1 and 7. There were no `ready` bugs in `TODOS.md`. This finishes the task that night 2026-11-21 planned but stopped on after its first plan review. The plan and the full review history are in `term-tracking/plan.md`.

What shipped:

- **`Annotation`.** It gains `start` and `end` (code-point offsets with `text[start:end] == quote`) and a required `source`.
- **Annotation format 1.** `annotations_to_json` and `annotations_from_json` write and read it.
  - The envelope carries `text_sha256`.
  - The format is closed: unknown keys are rejected, and so are wrong types, including `format: true` or `1.0`.
  - Anchors are checked on both read and write.
- **`sophistry_eval.passes.common`.** It provides `parse_json_object`, `anchor_quote` (unique spans only) and `PassOutputError`.
- **`sophistry_eval.passes.term_tracking.track_terms`.** It reports key terms and their senses, and equivocations with both uses anchored. Each equivocation becomes one annotation at the shifted use.
  - Validation is strict. Bad replies raise rather than being dropped.
  - Text containing `\r` is refused.
  - The term must appear as a whole word in both quotes.
- **Docs.**
  - `Docs/overview.md` covers the format and offset rules.
  - `Docs/rubrics.md` has a new term-tracking section, which separates equivocation from part-whole slides and covers the figurative-to-literal case.
  - The fixture README lists five known limits of the equivocation pair.

Reviews:

- Plan: architect approved in round 2, logician in round 3.
- Diff: architect approved in round 2, logician in round 3.
- Worth noting: the logician found that the clean control has a modal slip and that the pair is not matched on force. Both are documented as fixture limits, and the purer-pair TODO now lists four conditions. In the diff review, the logician also caught a control wording that it had itself approved at plan stage, and a prompt-versus-validation mismatch that I introduced in a round 1 fix.

Checks: `make check` is clean apart from the expected `tests/test_e2e_metamorphic.py` failure. 182 tests pass. No protected path was touched. No live model calls were made, so there is no variance to report.

Deviation from the plan: `PASS_NAME` was renamed `SOURCE_NAME`, because ruff's S105 flagged it as a password. The rename avoids the false positive without suppressing the rule.

Not done, logged in `TODOS.md`:

- the scoring step and wiring into `score_text`, so the e2e test still fails;
- the input-hash cache;
- a purer fixture pair;
- inflected and synonym forms.

New questions for Patrick:

- how annotations should feed the integrity score;
- the e2e docstring's claim that the pair's prose style is similar;
- an inflected-versus-derived wording note.
