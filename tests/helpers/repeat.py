"""Repeat-and-average helper for tests that depend on noisy model scores.

Use `measure` or `measure_scores` with `DEFAULT_RUNS`, report `Stat.summary()` in the plan, and
gate a metamorphic effect with both a fixed minimum drop and `clears_noise`.
"""

import statistics
from collections.abc import Callable
from dataclasses import dataclass

from sophistry_eval.types import Scores

DEFAULT_RUNS = 5
"""Runs per text, from open question 5 in Specs/initial-build.md."""

DEFAULT_K = 2.0
"""The drop must exceed this many clean-run stdevs (open question 5)."""


@dataclass(frozen=True)
class Stat:
    """The spread of one score over repeated runs. Needs at least 2 values."""

    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.values) < 2:
            msg = f"need at least 2 values to estimate spread, got {len(self.values)}"
            raise ValueError(msg)

    @property
    def runs(self) -> int:
        return len(self.values)

    @property
    def mean(self) -> float:
        return statistics.mean(self.values)

    @property
    def stdev(self) -> float:
        """Sample standard deviation (n - 1 in the denominator)."""
        return statistics.stdev(self.values)

    def summary(self) -> str:
        return f"mean {self.mean:.3f}, stdev {self.stdev:.3f}, runs {self.runs}"


@dataclass(frozen=True)
class ScoreStats:
    """One Stat per axis, plus sophistry averaged over each run's own product."""

    force: Stat
    integrity: Stat
    difficulty: Stat
    sophistry: Stat


def measure(fn: Callable[[], float], runs: int = DEFAULT_RUNS) -> Stat:
    """Call `fn` `runs` times and summarize the results."""
    if runs < 2:
        msg = f"need at least 2 runs to estimate spread, got {runs}"
        raise ValueError(msg)
    return Stat(values=tuple(fn() for _ in range(runs)))


def measure_scores(fn: Callable[[], Scores], runs: int = DEFAULT_RUNS) -> ScoreStats:
    """Call `fn` `runs` times and summarize each axis.

    Sophistry is the mean of the per-run products, not the product of the axis means. The two
    differ, and the per-run product is what a reader of any one run would have seen.
    """
    if runs < 2:
        msg = f"need at least 2 runs to estimate spread, got {runs}"
        raise ValueError(msg)
    results = [fn() for _ in range(runs)]
    return ScoreStats(
        force=Stat(values=tuple(s.force for s in results)),
        integrity=Stat(values=tuple(s.integrity for s in results)),
        difficulty=Stat(values=tuple(s.difficulty for s in results)),
        sophistry=Stat(values=tuple(s.sophistry for s in results)),
    )


def clears_noise(clean: Stat, perturbed: Stat, k: float = DEFAULT_K) -> bool:
    """True when the drop in means (clean minus perturbed) exceeds k clean-run stdevs.

    This is the rule from open question 5. It is a heuristic gate, not a significance test:

    - With 5 runs, the sample stdev has roughly 35% relative error.
    - It compares a difference of means with the clean text's per-run stdev. The standard error
      of that difference is sigma_c * sqrt(1/n_c + r**2/n_p), where r is the perturbed stdev over
      the clean stdev. With five runs on each text and equal spreads that is about 0.63 sigma_c,
      so the rule is conservative. With five runs each, it stops being conservative once the
      perturbed stdev exceeds about twice the clean stdev. That conservatism also assumes
      sigma_c is well estimated, which it often is not at n = 5.
    - It ignores the perturbed text's spread, which is how the previous point can fail.
    - When the clean runs are identical (stdev 0), any positive drop clears it.

    So it must never be the only check. Always pair it with a fixed minimum drop, such as
    MIN_INTEGRITY_DROP in tests/test_e2e_metamorphic.py.
    """
    drop = clean.mean - perturbed.mean
    return drop > k * clean.stdev
