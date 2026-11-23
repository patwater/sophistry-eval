# Plan: model client layer and repeat-and-average helper

Night 2026-11-21, task 1 of 2. Source: `Specs/initial-build.md`, proposed answers 1, 4 and 5.

## Scope

Answer 1 says the first night builds term tracking plus three supporting pieces: the real Claude client behind `ModelClient`, a recorded-response client for offline tests, and the repeat-and-average helper. The night allows two tasks. This task builds the three supporting pieces. Term tracking is the next task, and it will be the first code that uses them.

In scope:

1. `ClaudeClient` in `src/sophistry_eval/client.py`, implementing `ModelClient`.
2. `RecordingClient` (wraps a live client and writes its replies to disk) and `RecordedClient` (replays them offline) in the same module.
3. `tests/helpers/repeat.py` with `Stat`, `measure`, `ScoreStats`, `measure_scores` and `clears_noise`.
4. Doc updates: `Docs/overview.md` (status and client layer), `Docs/testing-strategy.md` (how to record and replay, and how variance is reported), `Docs/night-shift.md` ("Not built yet" list).

Out of scope, deferred to the term-tracking task or later:

- Any pass, any change to `Annotation` (the offsets from answer 7 arrive with the first pass that produces annotations), and any change to `pipeline.score_text`.
- Rewriting `tests/test_e2e_metamorphic.py` to use the helper. How it gets a client (live or recorded) and how often equivocation must be flagged across runs are decisions for the term-tracking task. It stays as the one expected failure.
- The input-hash result cache from `Docs/overview.md`. A replay file is not a cache. It is strict and fails on a miss. Logged in `TODOS.md`.
- A live smoke test. `pyproject.toml` registers only the `e2e` marker and is protected, so a `live` marker needs a proposal. Logged in `TODOS.md` as a question for Patrick.

## Design

### ClaudeClient

- `PRIMARY_MODEL = "claude-sonnet-5-5"` and `COMPARISON_MODEL = "claude-haiku-5-5"` (answer 4). The model is a constructor argument, so nothing is hard-coded to one model.
- The constructor takes optional `messages_api`, an object with the SDK's `messages.create` shape, typed by a small `Protocol`. Tests inject a fake that returns real `anthropic.types.Message` objects. When it is omitted, the client builds `anthropic.Anthropic().messages`.
- If `ANTHROPIC_API_KEY` is unset and no `messages_api` is given, it raises `MissingCredentialError`, naming the variable and never its value. This maps onto the stop condition "missing credential".
- `complete(system, prompt)` sends one user message with `max_tokens` (default 4096, configurable). It joins the text blocks and returns them.
- When the reply has `stop_reason == "max_tokens"` it raises `TruncatedReplyError`. A truncated reply is usually half a JSON object, and quietly parsing it would corrupt scores.
- `temperature` is an optional constructor argument. When it is `None` it is not sent, and the API default applies. `settings` exposes `{"max_tokens": ..., "temperature": ...}`, which recordings pin (see below).
- `usage` is a `UsageTotals(calls, input_tokens, output_tokens)`. It counts every call that returned, including truncated ones, because the tokens were spent. This is the "cost can be counted" hook from the overview. Converting tokens into dollars is left out, because prices change. That belongs with the ledger later.
- No retries in the client. The SDK already retries transient errors by default (2 retries).

### RecordingClient and RecordedClient

- A recording is a JSON file: `{"format": 1, "model": <name>, "settings": {...}, "replies": {<key>: [reply, reply, ...]}}`.
- The key is `prompt_key(system, prompt)`, a public helper in `client.py` that returns the SHA-256 of a length-prefixed encoding of the two strings, so that `("ab","c")` and `("a","bc")` differ. The system prompt is part of the key, so changing a pass's instructions invalidates its recordings. Model and settings are pinned in the header rather than in the key, because one file holds one configuration. The future input-hash cache must build its key from `prompt_key`, plus model and settings (logged in `TODOS.md`), so that the two hash schemes cannot drift apart.
- The wrapped client must expose `model` and `settings`, typed by a `RecordableClient` protocol. `RecordingClient` refuses to add to a file whose model **or settings** differ (`ValueError`, naming the mismatch). For example, raising `max_tokens` after a truncation cannot silently replay old replies.
- Cost passthrough: a `Metered` protocol (runtime-checkable, `usage: UsageTotals`). `ClaudeClient` satisfies it. `RecordingClient.usage` returns the inner client's `usage` when the inner client is `Metered`, and `None` otherwise. `ModelClient` itself does not change. Replay costs nothing, so `RecordedClient` has no usage.
- Several writers on one file: every write re-reads the file, appends, and atomically replaces it, all under the same call. Two recorders on one path therefore never overwrite each other with a stale copy. This is not safe across processes running at the same moment, and nothing needs that yet.
- **Only hashes are stored, never prompt text.** Prompts carry essay text, and most corpus essays are copyrighted (CLAUDE.md says do not commit it). Replies can contain short quoted spans. So a recording of a non-public-domain essay still goes under the gitignored `corpus/cache/` and is never committed. Recordings of the original fixtures and of public domain text may be committed under `tests/fixtures/recordings/`. This rule goes into `Docs/testing-strategy.md`.
- A repeated identical call appends to the list for its key. Replay returns the nth recorded reply on the nth call for that key. This keeps the recorded variance, so an offline stability test cannot report a false zero spread.
- Replay is strict. An unknown key, or more calls than were recorded, raises `RecordingMissingError`. It never falls back to a live call.
- It writes the file after every call, so a crash partway through a paid run keeps what it has. It extends an existing file and does not overwrite it.
- An unknown `format` value is rejected with `ValueError`.

### Repeat-and-average helper (`tests/helpers/repeat.py`)

- `Stat(values)`, frozen, with `mean`, sample `stdev` (`statistics.stdev`, n − 1), `runs` and `summary()`, which returns `"mean 0.800, stdev 0.100, runs 3"` for pasting into plans. It requires at least 2 values, because one run cannot estimate spread.
- `measure(fn, runs)` calls `fn` `runs` times and returns a `Stat`.
- `measure_scores(fn, runs)` returns `ScoreStats` with one `Stat` each for force, integrity, difficulty and sophistry. Sophistry is averaged over each run's own product, not recomputed from the axis means, since the mean of a product is not the product of the means.
- `DEFAULT_RUNS = 5`, citing answer 5, so later tests cannot quietly use fewer runs and still claim to follow it.
- `clears_noise(clean, perturbed, k=2.0)` takes two `Stat`s. It computes the drop itself as `clean.mean - perturbed.mean` and returns `drop > k * clean.stdev`, strictly greater. Taking `Stat`s means a caller cannot pass a single-run difference or flip the sign. This is answer 5's rule, followed literally.
- What the rule is and is not, stated in the docstring and in `Docs/testing-strategy.md`:
  - It is a heuristic gate, not a significance test.
  - With n = 5, the sample stdev has roughly 35% relative error.
  - Comparing a difference of means with one text's per-run σ is conservative compared with the standard error of the difference, which is about 0.63σ when the two spreads are equal.
  - It ignores the perturbed text's spread.
  - When the clean runs are identical (σ = 0), any positive drop clears it. A test pins this. So `clears_noise` is never the only check, and it always goes with the fixed minimum drop (`MIN_INTEGRITY_DROP = 0.15`).
  - A stricter rule, such as a σ floor or a combined standard error, would change answer 5, and that is Patrick's call. Recorded in `TODOS.md` under questions for Patrick.

## Testing plan

All tests are offline. No live model calls this task, so there are no model scores whose variance needs reporting.

`tests/test_client.py` (written, currently failing with an ImportError):

- The default models match answer 4.
- `ClaudeClient` sends model, system and a single user message, and returns the text. It joins multiple text blocks. It uses the model it was given. It counts calls and tokens across calls. It raises on `max_tokens` truncation and still counts that call's usage. It raises `MissingCredentialError` naming the variable when there is no key (the test no longer claims to check leakage, since there is no value to leak). It omits temperature unless one is given. It exposes `settings`. It satisfies `ModelClient`.
- Recording also: the file pins the settings, a `max_tokens` mismatch is refused, two recorders on one path interleave without loss, `usage` passes through from a metered inner client and is `None` otherwise, and `prompt_key` separates `("ab","c")` from `("a","bc")`.
- Record then replay gives the same replies, in any key order. Repeated identical calls replay in recorded order (variance preserved). More calls than were recorded fail. An unrecorded prompt fails and never goes live. The system prompt is part of the key. The recording file does not contain the prompt or system text. The file records the model and format 1. Recording extends an existing file. Recording refuses a model mismatch. An unknown format is rejected. Both clients satisfy `ModelClient`.

`tests/test_repeat_helper.py` (written, currently failing with an ImportError):

- `measure` gives the mean, sample stdev and raw values, and calls `fn` once per run. It rejects fewer than 2 runs. Constant input gives zero spread.
- `measure_scores` handles each axis separately. Sophistry is the mean of per-run products, checked with a case where that differs from the product of the means (0 vs 0.25).
- `DEFAULT_RUNS == 5`.
- `clears_noise`: above k·σ passes, below fails, and k is adjustable. Exactly equal fails, checked with in-range values that are exact in binary floating point (clean 0.5, 0.75, 1.0 has mean 0.75 and σ exactly 0.25. Perturbed 0.25, 0.25 drops exactly 0.5). A rise in the perturbed mean never passes (sign convention). Zero clean spread lets a 0.001 drop pass (pinned on purpose).
- `summary()` has a fixed format.

Regression: run `make check`. The only failure allowed is `tests/test_e2e_metamorphic.py`.

## Review history

Round 1, both REVISE.

- Architect: pin the settings in the recording, pass usage through, define behavior with several writers, share the key helper with the future cache, and fix the inexact equality test. All addressed above.
- Logician: fix the inexact equality test, have `clears_noise` take `Stat`s and fix the sign, document the 2σ rule's limits and pin σ = 0, add `DEFAULT_RUNS`, and rename the missing-key test. All addressed above.

Round 2:

- Architect: APPROVE, with two notes for implementation: check that the passed-through `usage` really is a `UsageTotals`, and repeat the header check at write time. Both done.
- Logician: REVISE. The "above" case was exactly on the boundary (a drop of 1.0 against 2σ = 1.0), which contradicted the equality test, and the fixtures used negative scores. Fixed with in-range exact values.

Round 3: logician APPROVE. Both personas approved the plan.

## Deviations found during implementation

1. **No temperature setting.** The installed SDK (anthropic 2.12.0) has no `temperature` parameter on `messages.create` for any overload (mypy: `Unexpected keyword argument "temperature"`). Passing it through `extra_body` would bypass the SDK, so it was dropped. `settings` is `{"max_tokens": ...}`, and the recording header pins only that. There is no sampling control, and replies vary from run to run at the API's default. Documented in `ClaudeClient`'s docstring and in `Docs/testing-strategy.md`.
2. **SDK adapter.** As the Risks section expected, the real overloaded `Messages.create` does not match the `MessagesAPI` protocol, so `_SDKMessages` wraps it with a typed signature. A test builds the default client with a dummy key, which needs no network.
3. **`tests` is now a package** (`tests/__init__.py`), and the helper is imported as `tests.helpers.repeat`. mypy only searches `src` (`mypy_path` in the protected `pyproject.toml`), so `helpers.repeat` could not be resolved. With `tests` as a package, pytest puts the repo root on `sys.path`, and mypy resolves the same name. No config was loosened.
4. Added a test that a header mismatch is caught at write time, following the architect's round 2 note.

## Diff review

Round 1:

- **Architect: APPROVE**, with two notes. Both were fixed in this diff:
  - Stop reasons other than end of turn, and empty replies, now raise `UnusableReplyError`, so they never reach a recording. `TruncatedReplyError` is a subclass.
  - A malformed recording now raises `ValueError` instead of `KeyError`, and the field types are checked.
- **Logician: REVISE.** All six points were addressed:
  1. The "conservative" claim is now scoped. It holds at about 0.63σ only with five runs each and equal spreads, it fails past r ≈ 2, and it assumes σ is well estimated. Fixed in the docstring and in `Docs/testing-strategy.md`.
  2. "The model id pins it" is gone. The docstring now says there is no sampling control.
  3. The settings test now checks that `max_tokens` reaches the API.
  4. A new test checks that the recorder keys replies with `prompt_key`.
  5. The model-client test now says mypy is the real check.
  6. The header is also checked before the paid call. One test shows the inner client is never called, and a racing test keeps the write-time check covered.

Round 2: both APPROVE. Their non-blocking follow-ups were done before the commit:

- Two doc lines now describe `UnusableReplyError`.
- New tests cover a `stop_sequence` stop being accepted, a whitespace-only reply being refused, and `measure_scores` rejecting fewer than 2 runs.

## Risks

- `mypy --strict` on the `messages_api` Protocol against the real overloaded `Messages.create`. If the real object does not match structurally, the default path wraps it in a typed adapter function rather than loosening types.
- `tests/helpers` imported as `helpers` relies on pytest's default rootdir `sys.path` insertion for `tests/`. It already resolves (the current failure is "No module named helpers.repeat", not "helpers").
