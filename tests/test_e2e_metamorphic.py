"""First end-to-end test with a known right answer, built from a controlled edit.

`planted.txt` equivocates between efficiency per task and total use. `clean.txt` does not.
The planted text also carries a part-whole slide, an unsupported "must", and a clause that
shields the claim from evidence, and it drops an evidence sentence and a concession. See
`fixtures/equivocation/README.md`.

Each text is scored `DEFAULT_RUNS` (5) times and judged by `planted_flaw_failures` in
`tests/helpers/metamorphic.py`. The pipeline must:

1. flag an equivocation on "efficiency" in every planted run, and no equivocation at all in any
   clean run;
2. give the planted text a mean integrity at least `MIN_INTEGRITY_DROP` lower, and a drop that
   exceeds twice the clean runs' stdev (open question 5). The drop is credited to the planted
   text as a whole, not to the equivocation alone;
3. leave mean force within `MAX_FORCE_CHANGE`. This is a loose check, because the pair is
   confounded on force.

The tolerances are open question 5 in `Specs/initial-build.md`. The per-run flag rule in point 1
is a night-shift interpretation that awaits Patrick's decision. Flags are matched by `kind`,
not by `source`. An equivocation on `clean.txt` from any pass is a false positive. The planted
flag is anchored on the term, which is necessary but not sufficient: a mislabel of the slide or
the "must" whose quote reaches back to "Because efficiency means..." would still count.

Cost: one run of this test makes 10 `score_text` calls (5 runs x 2 texts), and each fans out
over every pass. Every run must reach the model, not a result cache, or the noise gate is
empty. The client is the default one. Choosing a recorded or comparison-model client is in
`TODOS.md`.

This test fails until the pipeline is implemented. That is intended.
"""

from pathlib import Path

import pytest

from sophistry_eval.pipeline import score_text
from tests.helpers.metamorphic import planted_flaw_failures, score_runs

FIXTURES = Path(__file__).parent / "fixtures" / "equivocation"
MIN_INTEGRITY_DROP = 0.15
MAX_FORCE_CHANGE = 0.15


@pytest.mark.e2e
def test_planted_equivocation_is_detected_and_lowers_integrity_not_force() -> None:
    clean_text = (FIXTURES / "clean.txt").read_text()
    planted_text = (FIXTURES / "planted.txt").read_text()

    clean = score_runs(lambda: score_text(clean_text))
    planted = score_runs(lambda: score_text(planted_text))

    failures = planted_flaw_failures(
        clean,
        planted,
        kind="equivocation",
        term="efficiency",
        min_integrity_drop=MIN_INTEGRITY_DROP,
        max_force_change=MAX_FORCE_CHANGE,
    )
    assert failures == [], "\n".join(failures)
