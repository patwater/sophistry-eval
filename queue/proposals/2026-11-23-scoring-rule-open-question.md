# Proposal: add the scoring rule as an open question in the spec

Cause label: spec gap. Source: night 2026-11-23, task 2 (no eligible task).

`Specs/` is Patrick's to write, so this is a proposal and not an edit.

## What happened

Task 2 found no work it was allowed to take. The only remaining work under `Specs/initial-build.md` is the scoring step and the wiring of `pipeline.score_text`, which is also what would make `tests/test_e2e_metamorphic.py` pass. The spec says the output is "the scores for force, integrity, difficulty and sophistry strength" and that each pass produces annotations, but it never says how annotations become an integrity score. The worker correctly refused to invent that rule and logged the question in `TODOS.md` under "NEEDS INPUT FROM PATRICK". The night spent $0.26 discovering it had nothing to do.

The question lives only in `TODOS.md`, so it is easy to miss, and the spec's numbered open questions (which Patrick reviews as a yes-or-no list) do not include it. Answers 3 and 8 cover difficulty and force, but nothing covers integrity.

## Change

Add a ninth item to "Open questions for Patrick, with proposed answers" in `Specs/initial-build.md`. Suggested text, for Patrick to accept, edit or replace:

> 9. **How do pass annotations become the integrity score?** Options: (a) a fixed penalty per annotation of each kind, (b) a model-rated severity per annotation, summed and clipped, or (c) a separate integrity rating call that sees the text plus all annotations and must cite them. Proposed: (c) for v0.1, because it keeps one model-rated number per axis (matching answer 8 for force), and the e2e test checks the direction of the change rather than its size. Force and difficulty are rated in the same scoring step, without seeing the annotations, so a planted flaw cannot leak into force through the annotation list. The step records which annotations it cited, so a rank-order disagreement can be traced.

Once the answer is in the spec, the scoring step becomes eligible work and the next night can build it, together with the `measure_scores` rewrite of the e2e test that `TODOS.md` already ties to it.

## Why the process fix comes first

Without this, every night until Patrick answers will repeat task 2's outcome. Putting the question in the spec, where answers are expected, removes the gap instead of relying on a TODO line.
