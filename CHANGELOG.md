# Changelog

## Unreleased

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
