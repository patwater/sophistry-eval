# TODOS

Unrelated issues the agent notices go here. Bugs marked `ready` are picked up first by the night loop.

## Ready

(none yet)

## Backlog

- `PAUSE` is in `.gitignore`, so the runner's pause mechanism cannot reach CI without `git add -f`. Decide whether to remove it from `.gitignore` or keep the force-add convention that `Docs/night-shift.md` now describes.

- Replace the synthetic equivocation fixtures with controlled edits of a public domain essay once `corpus/public_domain/` has one.
- Build the input-hash result cache from `Docs/overview.md`. Its key must come from `client.prompt_key` plus the model and call settings, so it cannot drift from the recording key. A recording is not a cache: it is strict and fails on a miss.
- `RecordingClient` re-reads the file before every write, which is safe for several recorders in one process but not for separate processes writing at the same moment. Add a file lock if parallel recording is ever needed.
- Rewrite `tests/test_e2e_metamorphic.py` to use `measure_scores` with `DEFAULT_RUNS` and to gate with both `MIN_INTEGRITY_DROP` and `clears_noise`. This belongs with the term-tracking task.
- Turn the token counts in `ClaudeClient.usage` into dollars for `ledger/costs.csv` once the first pass makes live calls.

## NEEDS INPUT FROM PATRICK

- Review the proposed answers to the open questions in `Specs/initial-build.md`. The spec is promoted, so the night loop will use them as written unless he edits them first.
- Pick or swap the twelve Substack and Medium articles in `corpus/urls.csv`. They are a convenience sample from web searches and nobody has read them.
- Trigger the first night by hand with `workflow_dispatch` and read the triage report. The workflow is manual-only now, so nothing runs on its own.
- Apply the proposal in `queue/proposals/2026-11-21-claude-md-spec-reference.md` (CLAUDE.md still describes the spec as a draft).
- Should there be a `live` pytest marker for tests that call the real API? `pyproject.toml` registers only `e2e` and is protected. A tiny live smoke test of `ClaudeClient` would confirm the model ids and the key in CI.
- Open question 5's 2σ rule is a heuristic, as written up in `Docs/testing-strategy.md`. With five runs it lets any positive drop through when the clean runs are identical, and it ignores the perturbed text's spread. The fixed 0.15 minimum covers this for now. Do you want a σ floor or a combined standard error instead?
- The installed SDK (anthropic 2.12.0) has no temperature parameter, so run-to-run spread is whatever the API gives. If you expected to control sampling for the stability checks, say how.
