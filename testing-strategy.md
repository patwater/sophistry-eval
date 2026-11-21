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

## Test hygiene

- The model client is a thin layer so tests can replay recorded responses and run offline.
- Live-model tests are marked and run in the nightly job with a key.
- Every score test states its tolerance and how it handles variance.
- `tests/test_e2e_metamorphic.py` is the first end-to-end test. It fails until the pipeline exists. That is intended.
