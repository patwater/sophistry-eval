# Changelog

## Unreleased

- Term-tracking pass and the shared annotation format (night 2026-11-24, task 1):
  - `Annotation` now has `start` and `end` offsets, counted in Unicode code points into the exact input string, and a required `source` naming the pass. It validates its fields, including that the quote length matches the offsets.
  - `annotations_to_json` and `annotations_from_json` define a versioned wrapper, `{"format": 1, "annotations": [...]}`, with fixed key names. Reading is strict: another format, a missing or unknown key, or a wrongly typed value is rejected, and any new field bumps `ANNOTATION_FORMAT`.
  - `sophistry_eval.passes.common` holds the helpers every pass needs: `parse_json_object`, `anchor_quote`, which rejects a missing or ambiguous quote and never guesses, and `PassOutputError`.
  - `sophistry_eval.passes.term_tracking.track_terms` makes one model call and returns a `TermReport` holding terms, equivocations and annotations. Validation is strict, so a malformed reply raises and is never partly used. The checks are whole-word term matching, non-overlapping uses, distinct senses, and an equivocated term listed with two senses. The system prompt never mentions fixture content.
  - Docs: the overview gains the annotation format and the rule that every pass gets the same string. The rubrics gain a term-tracking section (equivocation against part-whole slide and rate-versus-total) and the immunizing move. Testing strategy notes that v0.1 term tracking catches only same-word shifts.
  - The equivocation fixture README now locates the planted shift correctly and lists the other flaws in both texts.
  - The pass is not yet wired into `score_text`, because no scoring step exists. The end-to-end test still fails, as expected.

- Model client layer (night 2026-11-21, task 1):
  - `ClaudeClient`, with Sonnet 5.5 as the default and Haiku 5.5 as the comparison model. It counts tokens and raises on a missing key, a truncated reply, a refusal or other incomplete stop, or an empty reply, so unusable replies never reach a recording.
  - `RecordingClient` and `RecordedClient` for strict offline replay. Recordings hold hashes only, never prompt text, and pin the model and `max_tokens`.
  - The repeat-and-average helper in `tests/helpers/repeat.py`, with `DEFAULT_RUNS = 5` and the 2σ `clears_noise` gate, whose limits are documented in `Docs/testing-strategy.md`.
  - `tests` is now a package so mypy and pytest resolve `tests.helpers` the same way.

- Promoted the initial build spec: `Specs/draft-initial-build.md` is now `Specs/initial-build.md`, at Patrick's direction.
- Added Bostrom's *Letter from Utopia* and twelve Substack and Medium articles to `corpus/urls.csv` (URL only), with `tests/test_corpus.py` to keep the file well-formed.
- Restored the intended directory layout from the kit zip, and added `tests/test_layout.py` to guard it. See `POSTMORTEMS.md`.
- Added proposed answers to the open questions in the initial build spec.
- Night shift kit: router, loop, review personas, triage orchestrator, runner, checks, and the first failing end-to-end test.
- Project skeleton: `sophistry_eval` package with `combine` and a placeholder `score_text`.
