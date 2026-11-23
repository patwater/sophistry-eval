# Changelog

## Unreleased

- Term-tracking pass and annotation format 1 (night 2026-11-23, task 1):
  - `Annotation` gains `start` and `end` (code-point offsets with `text[start:end] == quote`) and a required `source` naming the pass.
  - `annotations_to_json` and `annotations_from_json` define serialized format 1:
    - The envelope carries `text_sha256`, so annotations cannot be shown against the wrong text.
    - The format is closed, and reading is strict about keys, types and anchoring.
  - `sophistry_eval.passes.common` provides `parse_json_object`, `anchor_quote` and `PassOutputError`, which later passes will share.
  - `sophistry_eval.passes.term_tracking.track_terms` lists key terms and their senses and flags equivocations, with both uses anchored. The system prompt can be swapped, malformed replies raise, and text containing `\r` is refused. Each quote must contain the term as a whole word.
  - Docs:
    - `Docs/overview.md` documents the format and offset rules.
    - `Docs/rubrics.md` defines what term tracking checks, including equivocation versus part-whole slide.
    - The fixture README lists four known limits of the equivocation pair.
  - Not yet wired into `score_text`, since no scoring step exists. The e2e test still fails, as expected.

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
