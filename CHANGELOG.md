# Changelog

## Unreleased

- Paused the night shift by committing a `PAUSE` file (force-added, because `.gitignore` lists it), and documented how to pause and resume in `Docs/night-shift.md`.
- Removed the nightly schedule from `.github/workflows/night-shift.yml`, so the night shift runs only when triggered by hand. Done in a day session at Patrick's request.
- Promoted the initial build spec: `Specs/draft-initial-build.md` is now `Specs/initial-build.md`, at Patrick's direction.
- Added Bostrom's *Letter from Utopia* and twelve Substack and Medium articles to `corpus/urls.csv` (URL only), with `tests/test_corpus.py` to keep the file well-formed.
- Restored the intended directory layout from the kit zip, and added `tests/test_layout.py` to guard it. See `POSTMORTEMS.md`.
- Added proposed answers to the open questions in the initial build spec.
- Night shift kit: router, loop, review personas, triage orchestrator, runner, checks, and the first failing end-to-end test.
- Project skeleton: `sophistry_eval` package with `combine` and a placeholder `score_text`.
