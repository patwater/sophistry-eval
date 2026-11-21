"""Tests for the repeat-and-average helper that noisy score tests use."""

import itertools
import statistics

import pytest

from sophistry_eval.types import Scores
from tests.helpers.repeat import (
    DEFAULT_RUNS,
    ScoreStats,
    Stat,
    clears_noise,
    measure,
    measure_scores,
)


def test_measure_reports_mean_sample_stdev_and_the_raw_values() -> None:
    values = iter([0.2, 0.4, 0.6])
    stat = measure(lambda: next(values), runs=3)
    assert stat.values == (0.2, 0.4, 0.6)
    assert stat.mean == pytest.approx(0.4)
    assert stat.stdev == pytest.approx(statistics.stdev([0.2, 0.4, 0.6]))
    assert stat.runs == 3


def test_measure_calls_the_function_once_per_run() -> None:
    calls = itertools.count()
    measure(lambda: float(next(calls)), runs=5)
    assert next(calls) == 5


@pytest.mark.parametrize("runs", [0, 1])
def test_measure_needs_at_least_two_runs_to_estimate_spread(runs: int) -> None:
    with pytest.raises(ValueError, match="at least 2"):
        measure(lambda: 0.5, runs=runs)


@pytest.mark.parametrize("runs", [0, 1])
def test_measure_scores_needs_at_least_two_runs(runs: int) -> None:
    with pytest.raises(ValueError, match="at least 2"):
        measure_scores(lambda: Scores(force=0.5, integrity=0.5, difficulty=0.5), runs=runs)


def test_constant_scores_have_zero_spread() -> None:
    assert measure(lambda: 0.7, runs=4).stdev == 0.0


def test_measure_scores_summarizes_each_axis_separately() -> None:
    runs = iter(
        [
            Scores(force=0.8, integrity=0.5, difficulty=0.5),
            Scores(force=0.6, integrity=0.7, difficulty=0.5),
        ]
    )
    stats = measure_scores(lambda: next(runs), runs=2)
    assert isinstance(stats, ScoreStats)
    assert stats.force.mean == pytest.approx(0.7)
    assert stats.integrity.mean == pytest.approx(0.6)
    assert stats.difficulty.stdev == 0.0


def test_sophistry_is_averaged_per_run_not_recomputed_from_axis_means() -> None:
    """The mean of products is not the product of means. Each run's product is what a reader
    would have seen, so that is what gets averaged."""
    runs = iter(
        [
            Scores(force=1.0, integrity=0.0, difficulty=1.0),
            Scores(force=0.0, integrity=1.0, difficulty=1.0),
        ]
    )
    stats = measure_scores(lambda: next(runs), runs=2)
    assert stats.sophistry.mean == 0.0
    assert stats.force.mean * stats.integrity.mean * stats.difficulty.mean == pytest.approx(0.25)


def test_default_runs_follow_answer_5() -> None:
    """Open question 5 in Specs/initial-build.md: the mean of five runs per text."""
    assert DEFAULT_RUNS == 5


def test_a_drop_clears_the_noise_only_when_larger_than_k_clean_stdevs() -> None:
    """Open question 5: the drop in means must exceed twice the clean runs' stdev.
    All values are exact in binary floating point and within the 0 to 1 score range."""
    clean = Stat(values=(0.5, 0.75, 1.0))  # mean 0.75, stdev exactly 0.25
    assert clean.stdev == 0.25
    assert clears_noise(clean=clean, perturbed=Stat(values=(0.0, 0.0)))  # drop 0.75 > 0.5
    assert not clears_noise(clean=clean, perturbed=Stat(values=(0.5, 0.5)))  # drop 0.25 < 0.5
    assert clears_noise(clean=clean, perturbed=Stat(values=(0.5, 0.5)), k=0.5)  # 0.25 > 0.125


def test_a_drop_exactly_equal_to_k_stdevs_does_not_clear() -> None:
    clean = Stat(values=(0.5, 0.75, 1.0))  # mean 0.75, stdev 0.25
    perturbed = Stat(values=(0.25, 0.25))  # drop exactly 0.5 == 2 * 0.25
    assert not clears_noise(clean=clean, perturbed=perturbed)


def test_a_rise_never_clears_the_noise() -> None:
    """Sign convention: the drop is clean mean minus perturbed mean. A higher perturbed mean
    is not a drop, however large."""
    clean = Stat(values=(0.5, 0.5))
    assert not clears_noise(clean=clean, perturbed=Stat(values=(0.9, 0.9)))


def test_zero_clean_spread_lets_any_positive_drop_clear() -> None:
    """Pinned on purpose: with identical clean runs, 0.001 clears the noise. That is why
    clears_noise is never the only check and always goes with a fixed minimum drop."""
    clean = Stat(values=(0.8, 0.8, 0.8))
    assert clears_noise(clean=clean, perturbed=Stat(values=(0.799, 0.799)))


def test_stat_rejects_fewer_than_two_values() -> None:
    with pytest.raises(ValueError, match="at least 2"):
        Stat(values=(0.5,))


def test_stat_summary_line_reports_mean_stdev_and_runs() -> None:
    """Plans must report variance, so the helper gives a line that can be pasted into one."""
    line = Stat(values=(0.70, 0.80, 0.90)).summary()
    assert line == "mean 0.800, stdev 0.100, runs 3"
