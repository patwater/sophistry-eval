"""The gate a metamorphic test applies to a clean text and a text with a planted flaw.

The tolerances come from open question 5 in `Specs/initial-build.md`: the mean of five runs
per text, integrity dropping by at least a fixed minimum, force moving by at most a fixed
maximum, and an integrity drop larger than `k` clean-run stdevs.

How flags are counted across runs is not part of answer 5. It is a night-shift interpretation
that awaits Patrick's decision (see `TODOS.md`): every planted run must flag the planted term,
and no clean run may carry the flag kind anywhere. A reader of any single run would see a miss
or a false alarm, so a majority rule would hide one.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sophistry_eval.passes.common import contains_whole_word
from sophistry_eval.types import Evaluation
from tests.helpers.repeat import DEFAULT_K, DEFAULT_RUNS, ScoreStats, clears_noise, summarize_scores


@dataclass(frozen=True)
class RunSet:
    """Every evaluation of one text over repeated runs, and the spread of their scores."""

    evaluations: tuple[Evaluation, ...]
    stats: ScoreStats

    @classmethod
    def of(cls, evaluations: Sequence[Evaluation]) -> "RunSet":
        """Build a RunSet. Fewer than two evaluations raise `ValueError`."""
        kept = tuple(evaluations)
        return cls(evaluations=kept, stats=summarize_scores([e.scores for e in kept]))


def score_runs(fn: Callable[[], Evaluation], runs: int = DEFAULT_RUNS) -> RunSet:
    """Call the scorer `runs` times and keep every evaluation.

    Each run must reach the model. If a result cache answers the repeats, every run is
    identical, the clean stdev is 0, `clears_noise` passes any drop, and the fixed minimum is
    left as the only real gate. A replayed recording must hold one reply per run.
    """
    if runs < 2:
        msg = f"need at least 2 runs to estimate spread, got {runs}"
        raise ValueError(msg)
    return RunSet.of([fn() for _ in range(runs)])


def planted_flaw_failures(
    clean: RunSet,
    planted: RunSet,
    *,
    kind: str,
    term: str,
    min_integrity_drop: float,
    max_force_change: float,
    k: float = DEFAULT_K,
) -> list[str]:
    """Return one message per failed check. An empty list means the gate passes.

    Every check runs, so one result shows every failure:

    1. No clean run has an annotation of `kind`, wherever it points.
    2. Every planted run has an annotation of `kind` whose quote contains `term` as a whole
       word. This is necessary for detection, not sufficient. A mislabel of another move whose
       quote also covers the term still counts.
    3. The integrity drop in means is at least `min_integrity_drop` (inclusive).
    4. The integrity drop clears the noise: `clears_noise(clean, planted, k)`, strict.
    5. The force means differ by at most `max_force_change` (inclusive).
    """
    failures: list[str] = []

    false_flags = sum(any(a.kind == kind for a in e.annotations) for e in clean.evaluations)
    if false_flags:
        failures.append(
            f"{false_flags} of {len(clean.evaluations)} clean runs carry an {kind!r} flag"
        )

    misses = sum(
        not any(a.kind == kind and contains_whole_word(a.quote, term) for a in e.annotations)
        for e in planted.evaluations
    )
    if misses:
        failures.append(
            f"{misses} of {len(planted.evaluations)} planted runs lack an {kind!r} flag on {term!r}"
        )

    clean_i, planted_i = clean.stats.integrity, planted.stats.integrity
    spread = f"clean integrity {clean_i.summary()}; planted integrity {planted_i.summary()}"
    drop = clean_i.mean - planted_i.mean
    if not drop >= min_integrity_drop:
        failures.append(
            f"integrity drop {drop:.3f} is below the minimum {min_integrity_drop:.3f} ({spread})"
        )
    if not clears_noise(clean_i, planted_i, k):
        failures.append(
            f"integrity drop {drop:.3f} does not clear the noise: it must exceed "
            f"{k:g} x clean stdev = {k * clean_i.stdev:.3f} ({spread})"
        )

    force_change = planted.stats.force.mean - clean.stats.force.mean
    if not abs(force_change) <= max_force_change:
        failures.append(
            f"force moved by {force_change:+.3f}, more than {max_force_change:.3f} "
            f"(clean force {clean.stats.force.summary()}; "
            f"planted force {planted.stats.force.summary()})"
        )

    return failures
