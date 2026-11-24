"""First end-to-end test with a known right answer, built from a controlled edit.

In `planted.txt` the term "efficiency" shifts from less water per task to less water overall,
and the conclusion depends on that shift. `clean.txt` keeps the one per-task sense throughout.
The pipeline must (1) flag an equivocation only in the planted text, (2) give the planted text
clearly lower integrity, and (3) leave force roughly flat. The prose style is similar, and the
force tolerance is a first guess that must also absorb differences in craft, such as the clean
text's concession and scoped conclusion. The planted text has other flaws besides the
equivocation (see the fixture README), so the integrity gap is a net difference.

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
