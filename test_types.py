import pytest

from sophistry_eval.types import Annotation, Evaluation, Scores, combine


def test_combine_is_the_product_of_the_three_axes() -> None:
    assert combine(0.5, 0.8, 0.5) == pytest.approx(0.2)


def test_hard_cases_score_higher_than_easy_ones_with_equal_force_and_integrity() -> None:
    assert combine(0.8, 0.8, 0.9) > combine(0.8, 0.8, 0.3)


def test_either_axis_at_zero_gives_zero() -> None:
    assert combine(0.0, 0.9, 0.9) == 0.0
    assert combine(0.9, 0.0, 0.9) == 0.0


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_out_of_range_inputs_are_rejected(bad: float) -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        combine(bad, 0.5, 0.5)


def test_scores_expose_sophistry_and_evaluation_holds_annotations() -> None:
    scores = Scores(force=0.5, integrity=0.5, difficulty=1.0)
    note = Annotation(kind="equivocation", quote="efficiency", note="sense shifts")
    evaluation = Evaluation(scores=scores, annotations=(note,))
    assert evaluation.scores.sophistry == pytest.approx(0.25)
    assert evaluation.annotations[0].kind == "equivocation"
