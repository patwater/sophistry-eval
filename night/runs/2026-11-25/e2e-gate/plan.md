# Plan: apply open question 5's gate in the end-to-end test (night 2026-11-25, task 2)

Source: `Specs/initial-build.md`, proposed answer 5. It calls for the mean of five runs per text, integrity dropping by at least 0.15, force moving by at most 0.15, and an integrity drop larger than twice the clean runs' stdev. There are no `ready` bugs in `TODOS.md`. This also closes the backlog item "Rewrite `tests/test_e2e_metamorphic.py` to use `measure_scores` with `DEFAULT_RUNS` and to gate with both `MIN_INTEGRITY_DROP` and `clears_noise`". The e2e test's docstring asks for the same thing.

Why this task and not a live run: the other open term-tracking item is a recorded live run of `track_terms` on the fixtures. It needs the API key and live spend, and this session could not confirm a key was available. That item stays in `TODOS.md`. This task is offline and adds no spend.

## Problem

`tests/test_e2e_metamorphic.py` makes one `score_text` call per text and compares single scores. Answer 5 asks for means over five runs plus a noise gate. Today the gate exists only as separate pieces in `tests/helpers/repeat.py`, and nothing offline checks that the e2e test combines them correctly. When `score_text` is built, a mistake in the gate (a flipped sign, a missing check, a wrong inequality) would show up only as a live result that someone has to interpret. `AGENT_LOOP.md` forbids judging scores by reading outputs.

## Scope

1. `tests/helpers/repeat.py`: add `summarize_scores(results: Sequence[Scores]) -> ScoreStats`. `measure_scores` is refactored to call it, with the same behavior. Fewer than two results raise `ValueError` through `Stat`.
2. New `tests/helpers/metamorphic.py`:
   - `RunSet`, a frozen dataclass with `evaluations: tuple[Evaluation, ...]` and `stats: ScoreStats`. `RunSet.of(evaluations)` builds the stats with `summarize_scores`. The annotations of each run are kept, because the flag check is per run.
   - `score_runs(fn: Callable[[], Evaluation], runs: int = DEFAULT_RUNS) -> RunSet` calls the scorer `runs` times and rejects `runs < 2`.
   - `planted_flaw_failures(clean, planted, *, kind, term, min_integrity_drop, max_force_change, k=DEFAULT_K) -> list[str]` returns one message per failed check. An empty list means the gate passes. Every check runs, so one result shows every failure. The checks are:
     1. **No false flag.** No clean run has an annotation of `kind`, wherever it points. The message counts the offending runs: "n of N clean runs carry an 'equivocation' flag".
     2. **Flag found, on the right term.** Every planted run has at least one annotation of `kind` whose quote contains `term` as a whole word, ignoring case. It is the same whole-word rule the term-tracking pass applies. **(round 2)** The pass's private `_contains_word` moves to `passes/common.py` as the public `contains_whole_word(text, word)`. Both the pass and the gate call it, and a test checks that they share it. The message counts the misses: "n of N planted runs lack an 'equivocation' flag on 'efficiency'". **(round 1)**
     3. **Minimum drop.** `clean.integrity.mean - planted.integrity.mean >= min_integrity_drop`. This is inclusive, because answer 5 says "at least".
     4. **Noise.** `clears_noise(clean.integrity, planted.integrity, k)`. This is strict, as already pinned in `test_repeat_helper.py`.
     5. **Force flat.** `abs(planted.force.mean - clean.force.mean) <= max_force_change`. This is inclusive, because answer 5 says "at most".
   - The integrity messages include both `Stat.summary()` lines, so a failing live run reports its variance.
3. `tests/test_e2e_metamorphic.py`: score each fixture with `score_runs(lambda: score_text(text))` and assert `planted_flaw_failures(...) == []` with `kind="equivocation"`, `term="efficiency"`, `MIN_INTEGRITY_DROP = 0.15` and `MAX_FORCE_CHANGE = 0.15`. The failure messages become the assertion text. The test remains the expected `NotImplementedError` failure until `score_text` exists. The docstring is updated to describe the five runs, the gate and the per-run flag rule. The fixture caveats stay as they are: the pair is confounded, and force is a loose check.
4. `Docs/testing-strategy.md`: add a short "The metamorphic gate" paragraph naming the helper and the per-run rule, and update the line about `test_e2e_metamorphic.py`.
5. `TODOS.md`: remove the backlog item this closes. Add a question for Patrick about whether the flag rule should be "every run" or a majority.

Out of scope: building `score_text` or a scoring step, a live run, any change to the fixtures, and any change to `clears_noise` or the 2σ rule (that is Patrick's open question).

## Decisions

- **(round 1) Anchor the planted flag on the term.** `planted.txt` also has a part-whole slide, an unsupported "must" and a clause that shields the claim from evidence. A pass that labels one of those an equivocation has not detected the planted shift. So a planted run counts only when an `equivocation` annotation quotes "efficiency" as a whole word. The pass anchors its annotation at the shifted use, which contains the term.
  - **(round 2) Limit.** The anchor is necessary for detection, not sufficient. The part-whole slide (per flush to "the utility's total use") and the unsupported "must" share their sentence with the term: "Because efficiency means using less water, the utility's total use must therefore fall by the same amount." A mislabel whose quote reaches back to "Because efficiency means…" passes. Whether a mislabel is filtered out depends on how much text its quote covers, not on which move it names. A slide or "must" quote that covers only "the utility's total use must therefore fall by the same amount" lacks the term, so it is filtered out, and so is any mislabel of the shielding clause, "treat any rise in total use as a measurement error". The test uses that clause. The limit is stated in the test docstring, the e2e docstring and `Docs/testing-strategy.md`. A purer fixture pair is already in `TODOS.md`. On the clean side, any `equivocation` flag is a false positive, wherever it points.
- **(round 1) What is answer 5 and what is not.** Answer 5 fixes the tolerances on means: a minimum drop of 0.15, a maximum force change of 0.15, five runs and the 2σ gate. It says nothing about how flags are aggregated across runs. The every-run rule below is a night-shift interpretation awaiting Patrick, and the docstring and the Docs paragraph say so.
- **(round 1) Caching.** Repeated runs are useful only if each run reaches the model. If `score_text` or a client returned a cached result, all five runs would be identical. The clean stdev would then be 0, `clears_noise` would pass any drop, and the minimum drop would be the only real gate. No test can reject identical runs, because a deterministic model legitimately gives them; `test_zero_clean_spread_lets_any_positive_drop_clear` pins that case. So the `score_runs` docstring and `Docs/testing-strategy.md` say that repeated runs must bypass any result cache. A replayed recording must hold five replies per prompt, which `RecordedClient` supports.
- **(round 1) The client choice is deferred.** The e2e test calls `score_text(text)` with the default client, as it does today. Choosing the client, live or recorded and primary or comparison model, by a fixture or an environment variable is useful, but how depends on how `score_text` builds its default client, which does not exist yet. A TODO records this.
- **Per-run flag rule: every planted run must flag, and no clean run may.** **(round 2)** The single-call test cannot decide this, because with one run "every", "majority" and "any" agree. The reason is the reader's view: a majority rule would quietly accept a detector that misses the planted shift two times in five, or one that flags the clean text two times in five. A reader of any one run would see that miss or that false alarm. This is strict, and it may make the test flaky once it runs live. If so, that is a finding about the pass, and loosening the rule is Patrick's call. The question goes in `TODOS.md`.
- **Matching by `kind` only, not by `source`.** An equivocation flagged on `clean.txt` by any pass is a false positive. Requiring `source == "term_tracking"` for the planted flag would tie the e2e test to one pass's internals. The TODO from task 1 that asks this question is answered here and the reason is recorded in the docstring.
- **Where the code lives: in `tests/helpers/`, not `src/`.** The gate is a test policy, not a part of the product. It sits next to the repeat helper it builds on.
- **The force check has no noise gate.** Answer 5 asks only for a bound on the mean. With a confounded pair (see the fixture README), adding a second force condition would claim more than the fixtures support.
- **No sophistry check.** The fixture README says the test compares integrity and force, never sophistry.

## Tests (written first, failing on `ModuleNotFoundError: tests.helpers.metamorphic`)

`tests/test_metamorphic_helper.py`. All values are exact in binary floating point, so every boundary case is exact. The tests call the helper with `min_integrity_drop = max_force_change = 0.25` so the boundaries can be represented exactly. 0.15 is not exact.

- `summarize_scores` keeps each axis's values and the per-run sophistry product, and rejects a single result.
- `score_runs` calls the scorer once per run, keeps every evaluation, defaults to `DEFAULT_RUNS` (5), and rejects 0 or 1 runs.
- Pass: a clear effect with the flags in the right place gives `[]`.
- Boundary: a drop exactly at the minimum passes. The clean runs are identical, so the noise gate passes too.
- Each check fails on its own, with exactly one message:
  - one flagged clean run out of three, with "1 of 3" in the message;
  - one unflagged planted run out of three;
  - another `kind` neither satisfies the flag nor counts as a false positive;
  - **(round 1)** the right kind on a span without the term ("the whole community") does not count as the flag;
  - **(round 1)** whole-word, case-insensitive matching: "Efficiency," and "efficiency." count, "inefficiency" and "efficiencygain" do not;
  - a drop below the minimum that still clears the noise, because the clean runs are identical, which is the case `clears_noise` lets through;
  - a drop above the minimum that does not clear 2σ, with clean runs 0.5, 0.75, 1.0, stdev exactly 0.25 and a drop of 0.375 **(round 1: was 0.25, which sat on the minimum)**;
  - a force change of more than 0.25 in each direction.
- A force change of exactly the maximum passes in each direction.
- A rise in integrity fails both integrity checks, and the test asserts which two fired. **(round 1)**
- All five failures together give five messages, and the test asserts that each check fired once, in order. **(round 1)**
- Each integrity message, for the minimum and for the noise gate, carries both `Stat.summary()` lines. **(round 1)**
- Failure messages are asserted by their exact wording or by a phrase only that check uses. **(round 1)**
- **(round 2)**
  - The negative whole-word cases assert the exact flag-missing message.
  - The test that names `measure_scores` now compares it with `summarize_scores`.
  - The wrong-span test uses the shielding clause from `planted.txt`, not a phrase from `clean.txt`.
  - A test checks that the gate and the pass share one matcher.

The e2e test itself still fails with `NotImplementedError` from `score_text`. That is the expected failure named in `AGENT_LOOP.md` step 0.

## Variance

No model calls are made, so there is no variance to report. The helper puts the variance into the e2e failure output once live runs exist.

**(round 1) Cost once `score_text` exists:** each live run of the e2e test makes 10 `score_text` calls (5 runs × 2 texts), not 2. Each call fans out over every pass in the pipeline. The spend shows up through `ClaudeClient.usage` and, once that is converted into dollars (a backlog item), in `ledger/costs.csv`. Whoever builds `score_text` should plan for the 5× multiplier. This goes in the e2e docstring.

## Review history

- Round 1:
  - The Architect asked for revisions: the cache defeating the noise gate, the client being hard-wired, and the cost being understated.
  - The Logician asked for revisions:
    - anchor the flag on the term;
    - label the every-run rule as an interpretation;
    - a test that sat on the minimum;
    - count-only assertions;
    - a half-tested message;
    - message wording.
  - All of these are folded in above, marked **(round 1)**.

- Round 2:
  - The Architect approved. Its non-blocking suggestion to share the matcher is adopted.
  - The Logician asked for revisions:
    - the anchor's limit;
    - exact assertions for the negative whole-word cases;
    - a shared matcher;
    - the every-run reasoning;
    - a test name.
  - All are folded in, marked **(round 2)**.
  - Also following the Logician, `tests/fixtures/equivocation/README.md` is corrected. The planted slide runs from per-flush use to "the utility's total use", and "the whole community" appears only in `clean.txt`. This is a factual fix to a description. The fixture texts are unchanged.

- Round 3: both approved. The Logician's non-blocking points are applied in the implementation:
  - the shared-matcher test also checks the pass's side;
  - the import order is fixed;
  - the limit is worded by quote coverage, not by move.

## Diff review

- Round 1: both personas approved. Their non-blocking notes were applied:
  - `TODOS.md`'s cache item now asks for a bypass for repeated runs (Architect);
  - `contains_whole_word` is no longer in the gate's `__all__`, and the identity test reads the module namespace (Architect);
  - a test docstring now words the anchor's limit by quote coverage (Logician).

## Deviation from the plan

- The shared-matcher test reads `vars(term_tracking)["contains_whole_word"]` rather than the attribute, because `mypy --strict` rejects access to a name the module does not re-export. Adding `__all__` to the pass only for a test would widen its public surface.

## Risks

- The "every run" rule may be too strict for a noisy model. That is mitigated by recording it as Patrick's question rather than choosing a softer rule silently.
- `RunSet.of` with fewer than two evaluations raises through `Stat`. That is the intended behavior and it is tested.
