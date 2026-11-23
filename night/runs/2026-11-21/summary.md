# Night 2026-11-21 summary

## Task 1: model client layer and repeat-and-average helper — shipped

Source: `Specs/initial-build.md`, proposed answers 1, 4 and 5. There were no `ready` bugs in `TODOS.md`. The plan and review history are in `client-layer/plan.md`.

What shipped:

- `ClaudeClient` (`claude-sonnet-5-5` primary, `claude-haiku-5-5` comparison).
  - It counts tokens.
  - It raises on a missing key, on truncation, on a refusal or other incomplete stop, and on an empty reply.
- `RecordingClient` and `RecordedClient` for strict offline replay.
  - Recordings hold hashes only, never prompt text.
  - Each file pins the model and `max_tokens`.
  - Repeated prompts replay in recorded order, so offline variance is preserved.
- `tests/helpers/repeat.py`: `Stat`, `measure`, `measure_scores`, `DEFAULT_RUNS = 5`, and `clears_noise`, the 2σ gate from answer 5. Its limits are written up in `Docs/testing-strategy.md`.

Reviews:

- Plan: architect approved in round 2. Logician approved in round 3, after catching a test whose "above the threshold" case sat exactly on the boundary.
- Diff: both approved in round 2.

Checks: `make check` is clean apart from the expected `tests/test_e2e_metamorphic.py` failure. 121 tests pass. No protected path was touched.

Deviations from the plan, with reasons in `client-layer/plan.md`:

- No temperature setting, because the installed SDK has no such parameter.
- A typed adapter around the SDK's `messages.create`.
- `tests/` is now a package, so mypy resolves `tests.helpers` without the protected config being changed.

Questions added to `TODOS.md` for Patrick: a `live` pytest marker, whether the 2σ rule is strict enough, and sampling control given that there is no temperature parameter.

No live model calls were made in this task.
