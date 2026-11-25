"""Tests for the metamorphic gate that the end-to-end test applies (open question 5).

All score values are exact in binary floating point, so every boundary case sits exactly on the
boundary it claims to test.
"""

import itertools

import pytest

from sophistry_eval.passes import term_tracking
from sophistry_eval.passes.common import contains_whole_word
from sophistry_eval.types import Annotation, Evaluation, Scores
from tests.helpers import metamorphic as gate
from tests.helpers.metamorphic import RunSet, planted_flaw_failures, score_runs
from tests.helpers.repeat import DEFAULT_RUNS, measure_scores, summarize_scores

KIND = "equivocation"
TERM = "efficiency"


def _flag(kind: str = KIND, quote: str = "more efficiency") -> Annotation:
    return Annotation(kind=kind, quote=quote, start=0, end=len(quote), note="n", source="test")


def _ev(integrity: float, force: float = 0.5, *, kinds: tuple[str, ...] = ()) -> Evaluation:
    return Evaluation(
        scores=Scores(force=force, integrity=integrity, difficulty=0.5),
        annotations=tuple(_flag(k) for k in kinds),
    )


def _runs(*evaluations: Evaluation) -> RunSet:
    return RunSet.of(evaluations)


def _clean(integrity: tuple[float, ...] = (0.75, 0.75), force: float = 0.5) -> RunSet:
    return _runs(*(_ev(i, force) for i in integrity))


def _planted(integrity: tuple[float, ...] = (0.25, 0.25), force: float = 0.5) -> RunSet:
    return _runs(*(_ev(i, force, kinds=(KIND,)) for i in integrity))


def _failures(clean: RunSet, planted: RunSet, min_drop: float = 0.25) -> list[str]:
    return planted_flaw_failures(
        clean,
        planted,
        kind=KIND,
        term=TERM,
        min_integrity_drop=min_drop,
        max_force_change=0.25,
    )


# --- summarize_scores and score_runs -------------------------------------------------------


def test_summarize_scores_matches_measure_scores_axis_by_axis() -> None:
    results = [
        Scores(force=0.75, integrity=0.5, difficulty=0.25),
        Scores(force=0.25, integrity=1.0, difficulty=0.75),
    ]
    stats = summarize_scores(results)
    replay = iter(results)
    assert measure_scores(lambda: next(replay), runs=2) == stats
    assert stats.force.values == (0.75, 0.25)
    assert stats.integrity.values == (0.5, 1.0)
    assert stats.difficulty.values == (0.25, 0.75)
    assert stats.sophistry.values == (0.75 * 0.5 * 0.25, 0.25 * 1.0 * 0.75)


def test_summarize_scores_needs_at_least_two_runs() -> None:
    with pytest.raises(ValueError, match="at least 2"):
        summarize_scores([Scores(force=0.5, integrity=0.5, difficulty=0.5)])


def test_score_runs_calls_the_scorer_once_per_run_and_keeps_every_evaluation() -> None:
    calls = itertools.count()

    def scorer() -> Evaluation:
        return _ev(integrity=float(next(calls)) / 8)

    runs = score_runs(scorer, runs=4)
    assert next(calls) == 4
    assert len(runs.evaluations) == 4
    assert runs.stats.integrity.values == (0.0, 0.125, 0.25, 0.375)


def test_score_runs_defaults_to_five_runs() -> None:
    calls = itertools.count()

    def scorer() -> Evaluation:
        next(calls)
        return _ev(integrity=0.5)

    score_runs(scorer)
    assert next(calls) == DEFAULT_RUNS == 5


@pytest.mark.parametrize("runs", [0, 1])
def test_score_runs_needs_at_least_two_runs(runs: int) -> None:
    with pytest.raises(ValueError, match="at least 2"):
        score_runs(lambda: _ev(0.5), runs=runs)


# --- planted_flaw_failures: the passing case ------------------------------------------------


def test_a_clear_effect_with_flags_in_the_right_place_passes() -> None:
    assert _failures(_clean(), _planted()) == []


def test_a_drop_exactly_at_the_minimum_passes() -> None:
    """Answer 5 says integrity drops by at least the minimum, so the boundary is inclusive.
    Clean runs are identical, so the noise gate passes for any positive drop."""
    assert _failures(_clean((0.75, 0.75)), _planted((0.5, 0.5))) == []


# --- planted_flaw_failures: each check fails on its own ------------------------------------


def test_a_flag_in_any_clean_run_fails() -> None:
    clean = _runs(_ev(0.75), _ev(0.75, kinds=(KIND,)), _ev(0.75))
    failures = _failures(clean, _planted())
    assert failures == ["1 of 3 clean runs carry an 'equivocation' flag"]


def test_a_planted_run_without_the_flag_fails() -> None:
    planted = _runs(_ev(0.25, kinds=(KIND,)), _ev(0.25), _ev(0.25, kinds=(KIND,)))
    failures = _failures(_clean(), planted)
    assert failures == ["1 of 3 planted runs lack an 'equivocation' flag on 'efficiency'"]


def test_other_annotation_kinds_neither_count_as_the_flag_nor_as_a_false_positive() -> None:
    clean = _runs(_ev(0.75, kinds=("modal_slide",)), _ev(0.75, kinds=("modal_slide",)))
    planted = _runs(_ev(0.25, kinds=("modal_slide",)), _ev(0.25, kinds=(KIND,)))
    failures = _failures(clean, planted)
    assert failures == ["1 of 2 planted runs lack an 'equivocation' flag on 'efficiency'"]


def test_the_right_kind_on_a_span_without_the_term_does_not_count_as_the_flag() -> None:
    """planted.txt also has a clause that shields the claim from evidence. A pass that labels
    that clause an equivocation has not found the planted shift on "efficiency".

    The anchor is necessary for detection, not sufficient. The part-whole slide and the
    unsupported "must" share a sentence with the term, so a mislabel quoting that sentence
    would still count. A quote that also covers the term cannot tell those moves apart."""
    planted = _runs(
        _ev(0.25, kinds=(KIND,)),
        Evaluation(
            scores=Scores(force=0.5, integrity=0.25, difficulty=0.5),
            annotations=(_flag(quote="treat any rise in total use as a measurement error"),),
        ),
    )
    failures = _failures(_clean(), planted)
    assert failures == ["1 of 2 planted runs lack an 'equivocation' flag on 'efficiency'"]


@pytest.mark.parametrize(
    ("quote", "counts"),
    [
        ("Efficiency, as defined", True),
        ("the efficiency.", True),
        ("inefficiency", False),
        ("efficiencygain", False),
    ],
)
def test_the_term_must_appear_as_a_whole_word_ignoring_case(quote: str, counts: bool) -> None:
    flagged = Evaluation(
        scores=Scores(force=0.5, integrity=0.25, difficulty=0.5),
        annotations=(_flag(quote=quote),),
    )
    failures = _failures(_clean(), _runs(flagged, flagged))
    expected = [] if counts else ["2 of 2 planted runs lack an 'equivocation' flag on 'efficiency'"]
    assert failures == expected


def test_the_gate_uses_the_same_whole_word_rule_as_the_term_tracking_pass() -> None:
    """The gate and the pass share one matcher, so the two rules cannot drift apart."""
    assert vars(gate)["contains_whole_word"] is contains_whole_word
    assert vars(term_tracking)["contains_whole_word"] is contains_whole_word
    assert not hasattr(term_tracking, "_contains_word")


def test_a_drop_below_the_minimum_fails_even_when_it_clears_the_noise() -> None:
    """Identical clean runs let any positive drop clear the noise gate, so the fixed
    minimum is what catches a small drop. Drop 0.125 < 0.25."""
    failures = _failures(_clean((0.75, 0.75)), _planted((0.625, 0.625)))
    assert len(failures) == 1
    assert "below the minimum" in failures[0]


def test_a_drop_above_the_minimum_fails_when_it_does_not_clear_the_noise() -> None:
    """Clean runs 0.5, 0.75, 1.0 have mean 0.75 and stdev exactly 0.25. A drop of 0.375 is
    above the 0.25 minimum but below 2 x 0.25 = 0.5."""
    failures = _failures(_clean((0.5, 0.75, 1.0)), _planted((0.375, 0.375)))
    assert len(failures) == 1
    assert "does not clear the noise" in failures[0]


def test_a_rise_in_integrity_fails_both_integrity_checks() -> None:
    failures = _failures(_clean((0.25, 0.25)), _planted((0.75, 0.75)))
    assert len(failures) == 2
    assert "below the minimum" in failures[0]
    assert "does not clear the noise" in failures[1]


@pytest.mark.parametrize("planted_force", [0.25, 0.75])
def test_a_force_change_at_the_maximum_passes_in_either_direction(planted_force: float) -> None:
    assert _failures(_clean(force=0.5), _planted(force=planted_force)) == []


@pytest.mark.parametrize("planted_force", [0.125, 0.875])
def test_a_force_change_beyond_the_maximum_fails_in_either_direction(
    planted_force: float,
) -> None:
    failures = _failures(_clean(force=0.5), _planted(force=planted_force))
    assert len(failures) == 1
    assert "force moved" in failures[0]


def test_every_failure_is_reported_not_only_the_first() -> None:
    clean = _runs(_ev(0.25, 0.5, kinds=(KIND,)), _ev(0.25, 0.5))
    planted = _runs(_ev(0.75, 1.0), _ev(0.75, 1.0))
    failures = _failures(clean, planted)
    assert len(failures) == 5
    for i, phrase in enumerate(
        [
            "clean runs carry",
            "planted runs lack",
            "below the minimum",
            "does not clear the noise",
            "force moved",
        ]
    ):
        assert phrase in failures[i]


@pytest.mark.parametrize(
    ("clean_integrity", "planted_integrity", "clean_line", "planted_line"),
    [
        # Fails the minimum only.
        ((0.75, 0.75), (0.625, 0.625), "mean 0.750, stdev 0.000, runs 2", "mean 0.625"),
        # Fails the noise gate only.
        ((0.5, 0.75, 1.0), (0.375, 0.375), "mean 0.750, stdev 0.250, runs 3", "mean 0.375"),
    ],
)
def test_integrity_failure_messages_report_the_spread_of_both_texts(
    clean_integrity: tuple[float, ...],
    planted_integrity: tuple[float, ...],
    clean_line: str,
    planted_line: str,
) -> None:
    """Plans must report variance, so each integrity message carries both Stat summaries."""
    failures = _failures(_clean(clean_integrity), _planted(planted_integrity))
    assert len(failures) == 1
    assert clean_line in failures[0]
    assert f"{planted_line}, stdev 0.000, runs 2" in failures[0]
