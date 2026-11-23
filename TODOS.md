# TODOS

Unrelated issues the agent notices go here. Bugs marked `ready` are picked up first by the night loop.

## Ready

(none yet)

## Backlog

- `PAUSE` is in `.gitignore`, so the runner's pause mechanism cannot reach CI without `git add -f`. Decide whether to remove it from `.gitignore` or keep the force-add convention that `Docs/night-shift.md` now describes.

- Replace the synthetic equivocation fixtures with controlled edits of a public domain essay once `corpus/public_domain/` has one.
- Add a recorded-response model client for offline tests.
- Add a repeat-and-average helper in `tests/helpers` for noisy scores.

## NEEDS INPUT FROM PATRICK

- Review the proposed answers to the open questions in `Specs/initial-build.md`. The spec is promoted, so the night loop will use them as written unless he edits them first.
- Pick or swap the twelve Substack and Medium articles in `corpus/urls.csv`. They are a convenience sample from web searches and nobody has read them.
- Trigger the first night by hand with `workflow_dispatch` and read the triage report. The workflow is manual-only now, so nothing runs on its own.
- Apply the proposal in `queue/proposals/2026-11-21-claude-md-spec-reference.md` (CLAUDE.md still describes the spec as a draft).
