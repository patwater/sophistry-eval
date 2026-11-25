# Testing strategy

Real essays have no known right answer, so validation is layered. Each layer answers a different question, and the layers get more expensive and more subjective as you go down.

## Layer 1: metamorphic tests on real essays

Take an essay and make a controlled edit whose effect on the scores is known in direction. Examples:

- Swap a key term for a near-synonym with a different sense partway through. Integrity must drop, the term-tracking pass must flag it, and force must stay roughly flat.
- Delete a premise that carries the conclusion. Integrity must drop.
- Change a "may" into a "must" with no new support. The modal audit must flag it, and integrity must drop.
- Add rhetorical flourish to a weak essay without changing its reasoning. Force may rise, and integrity must not.

These need no human labels. They are the closest thing to a known right answer on real text, and they should be the backbone of the end-to-end tests.

## Layer 2: rank-order checks on a corpus

Compare famous essays with random essays from Substack and the public internet. Fame is only a weak proxy for integrity, so treat this as a sanity check. The stronger version compares scores with Patrick's hand ratings of about 20 pieces for force, integrity and difficulty, and reports rank correlation. Calibration candidates include Gorgias's Encomium of Helen, Swift's A Modest Proposal, Federalist 10, and Orwell's essay on politics and the English language.

## Layer 3: stability

Run each essay several times and measure the spread of each score. Compare the spread with the effect sizes from Layer 1, since an effect smaller than the noise cannot be detected. Also check that scores do not swing with essay length or paragraph order, and compare at least two models.

## Corpus rules

Only public domain text is committed, under `corpus/public_domain/`. Other essays are listed by URL in `corpus/urls.csv` and cached in `corpus/cache/`, which is gitignored. The fixtures under `tests/fixtures/` that were written for this project are original.

## Recording and replaying model replies

Wrap a live client in `RecordingClient(inner, path)` to record, and use `RecordedClient(path)` to replay offline.

- **Keys and contents.** Replies are keyed by `prompt_key(system, prompt)`, a SHA-256 hash. The file holds only hashes and replies, never prompt text. It pins the model and call settings (today only `max_tokens`) and refuses to mix them in one file.
- **Repeated prompts.** Each repeated prompt appends a reply. Replay returns the replies in recorded order, so the spread of repeated runs survives offline.
- **Unusable replies.** A truncated, refused, otherwise incomplete or empty reply raises `UnusableReplyError` in `ClaudeClient`, so it is never recorded.
- **Strict replay.** Replay never goes live. An unknown prompt, or more calls than were recorded, raises `RecordingMissingError`. Changing a pass's system prompt invalidates its recordings, which is intended. Re-record them.
- **Where recordings live.** Replies can quote spans of the essay. Recordings of the original fixtures and of public domain text may be committed under `tests/fixtures/recordings/`. Recordings of any other essay go under the gitignored `corpus/cache/` and are never committed.
- **No temperature setting.** The installed SDK's `messages.create` takes no temperature parameter, so run-to-run spread is whatever the API gives for that model.

## Handling variance

`tests/helpers/repeat.py` provides the repeat-and-average helper.

- **Runs.** `measure_scores(fn, runs=DEFAULT_RUNS)` runs a scorer five times (open question 5) and returns a `Stat` per axis.
- **Sophistry.** The sophistry `Stat` is the mean of each run's own product, not the product of the axis means.
- **Reporting.** Paste `Stat.summary()` lines into the plan to report the variance.

Gate a metamorphic effect with two checks together:

1. A fixed minimum drop, such as `MIN_INTEGRITY_DROP = 0.15`, compared on the means.
2. `clears_noise(clean, perturbed, k=2.0)`. It passes when the clean mean minus the perturbed mean exceeds `k` times the clean runs' sample stdev.

`clears_noise` is a heuristic gate, not a significance test, and must never be the only check:

- With five runs the sample stdev has roughly 35% relative error.
- It compares a difference of means with the clean text's per-run stdev, not with a standard error.
  - With five runs on each text and equal spreads, the standard error of the difference is about 0.63 times the clean stdev, so the rule is conservative.
  - It stops being conservative once the perturbed stdev exceeds about twice the clean stdev.
  - The conservatism also assumes the clean stdev is well estimated, which it often is not with five runs.
- It ignores the perturbed text's spread, which is how the previous point can fail.
- When the clean runs are identical, any positive drop clears it.

A stricter rule, such as a floor on the stdev or a combined standard error, would change open question 5 and is Patrick's call.

Repeated runs must bypass any result cache. If a cache answers the repeats, every run is identical, the clean stdev is 0, and `clears_noise` passes any drop. The fixed minimum is then the only real gate. A replayed recording must hold one reply per run.

## The metamorphic gate

`tests/helpers/metamorphic.py` combines the checks for a clean and planted pair. `score_runs(fn)` scores a text `DEFAULT_RUNS` times and keeps every `Evaluation`. `planted_flaw_failures(clean, planted, *, kind, term, min_integrity_drop, max_force_change)` returns one message per failed check, and an empty list means it passes. The checks are:

1. **No false flag.** No clean run carries an annotation of `kind`, wherever it points.
2. **The flag is found.** Every planted run has an annotation of `kind` whose quote contains `term` as a whole word. This uses the same `contains_whole_word` as the term-tracking pass.
3. **Minimum drop.** The drop in mean integrity is at least the minimum (inclusive).
4. **Noise.** The drop clears `clears_noise` (strict).
5. **Force.** The mean force moves by at most the maximum (inclusive).

The messages carry the `Stat.summary()` lines, so a failure reports its variance.

The tolerances are open question 5. The per-run flag rule, every planted run and no clean run, is a night-shift interpretation that awaits Patrick. Anchoring on the term is necessary for detection, not sufficient. A mislabel of another move whose quote also covers the term still counts.

## Test hygiene

- The model client is a thin layer so tests can replay recorded responses and run offline.
- Live-model tests are marked and run in the nightly job with a key.
- Every score test states its tolerance and how it handles variance.
- `tests/test_e2e_metamorphic.py` is the first end-to-end test. It scores each fixture five times and applies the metamorphic gate. One run makes 10 `score_text` calls. It fails until the pipeline exists. That is intended.
