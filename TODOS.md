# TODOS

Unrelated issues the agent notices go here. Bugs marked `ready` are picked up first by the night loop.

## Ready

(none yet)

## Backlog

- Replace the synthetic equivocation fixtures with controlled edits of a public domain essay once `corpus/public_domain/` has one.
- Build the input-hash result cache from `Docs/overview.md`. Its key must come from `client.prompt_key` plus the model and call settings, so it cannot drift from the recording key. A recording is not a cache: it is strict and fails on a miss. The cache also needs a bypass, such as a flag or a separate client, that repeated runs (`score_runs` in `tests/helpers/metamorphic.py`) can use. Otherwise every repeat is identical and the 2σ noise gate is empty.
- `RecordingClient` re-reads the file before every write, which is safe for several recorders in one process but not for separate processes writing at the same moment. Add a file lock if parallel recording is ever needed.
- Wire `track_terms` into `score_text`. That needs a scoring step for force, integrity and difficulty, which the spec has not yet described. (The `source` question is settled: the e2e gate matches by `kind` only. See `tests/helpers/metamorphic.py`.)
- Let the e2e test choose its client, live or recorded and the primary or the comparison model, through a fixture or an environment variable. This waits on how `score_text` builds its default client. One e2e run makes 10 `score_text` calls, so recording it once and replaying it offline saves the most.
- Make a purer equivocation fixture pair: one controlled term shift, with evidence, concessions and the claim's strength kept matched, so force and difficulty are not confounded. The current pair's limits are in `tests/fixtures/equivocation/README.md`.
- Term tracking requires the term as a whole word in both quotes, so an equivocation carried only by a pronoun or a near-synonym cannot be reported. A later pass could link a near-synonym explicitly.
- Run `track_terms` live on the equivocation fixtures with `RecordingClient` and `measure`, and commit the recordings under `tests/fixtures/recordings/`. Nothing has yet checked that the prompt finds the planted shift and leaves `clean.txt` alone.
- Turn the token counts in `ClaudeClient.usage` into dollars for `ledger/costs.csv` once the first pass makes live calls.

## NEEDS INPUT FROM PATRICK

- Review the proposed answers to the open questions in `Specs/initial-build.md`. The spec is promoted, so the night loop will use them as written unless he edits them first.
- Pick or swap the twelve Substack and Medium articles in `corpus/urls.csv`. They are a convenience sample from web searches and nobody has read them.
- Trigger the first night by hand with `workflow_dispatch` and read the triage report before trusting the schedule.
- Apply the proposal in `queue/proposals/2026-11-21-claude-md-spec-reference.md` (CLAUDE.md still describes the spec as a draft).
- Should there be a `live` pytest marker for tests that call the real API? `pyproject.toml` registers only `e2e` and is protected. A tiny live smoke test of `ClaudeClient` would confirm the model ids and the key in CI.
- Open question 5's 2σ rule is a heuristic, as written up in `Docs/testing-strategy.md`. With five runs it lets any positive drop through when the clean runs are identical, and it ignores the perturbed text's spread. The fixed 0.15 minimum covers this for now. Do you want a σ floor or a combined standard error instead?
- The e2e gate requires the equivocation flag in **every** planted run and in **no** clean run (`tests/helpers/metamorphic.py`). Answer 5 does not say how flags are counted across runs. This strict rule was chosen because a reader of any one run would see the miss or the false alarm, but it may be flaky with a noisy model. Keep it, or use a majority?
- The installed SDK (anthropic 2.12.0) has no temperature parameter, so run-to-run spread is whatever the API gives. If you expected to control sampling for the stability checks, say how.
