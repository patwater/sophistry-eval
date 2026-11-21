"""First end-to-end test with a known right answer, built from a controlled edit.

`planted.txt` equivocates between efficiency per task and total use. `clean.txt` does not.
The pipeline must (1) flag an equivocation only in the planted text, (2) give the planted text
clearly lower integrity, and (3) leave force roughly flat, since the prose style is similar.

This test fails until the pipeline is implemented. That is intended. Tolerances are first guesses
and are open question 5 in Specs/initial-build.md. Model scores are noisy, so the night
shift should replace the single call with a repeat-and-average helper and report the variance.
"""

from pathlib import Path

import pytest

from sophistry_eval.pipeline import score_text

FIXTURES = Path(__file__).parent / "fixtures" / "equivocation"
MIN_INTEGRITY_DROP = 0.15
MAX_FORCE_CHANGE = 0.15


@pytest.mark.e2e
def test_planted_equivocation_is_detected_and_lowers_integrity_not_force() -> None:
    clean = score_text((FIXTURES / "clean.txt").read_text())
    planted = score_text((FIXTURES / "planted.txt").read_text())

    assert not any(a.kind == "equivocation" for a in clean.annotations)
    assert any(a.kind == "equivocation" for a in planted.annotations)
    assert planted.scores.integrity <= clean.scores.integrity - MIN_INTEGRITY_DROP
    assert abs(planted.scores.force - clean.scores.force) <= MAX_FORCE_CHANGE
