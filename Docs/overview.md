# Overview

sophistry-eval reads a piece of writing and reports how well it makes its case. It scores three things separately and then combines them.

- **Persuasive force** is how strongly the prose pulls a reader toward its conclusion.
- **Conceptual integrity** is how well the terms, claims and inferences hold together.
- **Difficulty of the case** is how hard the position is to defend, so holding an unpopular or demanding thesis earns more credit than defending something everyone already believes.

Sophistry strength is force times integrity times difficulty, with difficulty acting as a multiplier that rewards holding a hard case rather than penalizing easy ones. Whether the combination should be a product or a minimum is an open question in `Specs/draft-initial-build.md`.

## Why the word sophistry

The sophists taught the craft of speaking and arguing well. The long negative meaning owes much to Plato's campaign against them. Here, sophistry in the good sense means high force together with high integrity. A four-way map names the other cases. A dry proof has integrity without force. Demagoguery or eristic has force without integrity. Noise has neither.

## Pipeline

The pipeline is a sequence of independent passes. Each pass takes the text (and sometimes earlier annotations) and produces annotations.

1. Claim extraction builds a graph of claims, premises and links, with each link tagged as deductive, inductive, analogical or merely rhetorical.
2. Term tracking follows each key term across the piece and flags equivocation.
3. Modal audit flags necessity claims supported only by possibility and unargued slides from "can" to "should".
4. Presupposition load counts what the argument carries as given without stating it.
5. Adversarial verifier runs a prosecutor against a defender. Repairs count as evidence of robustness. The number and strength of objections also feed the difficulty estimate.

## Output

A margin-annotated version of the text and four scores: force, integrity, difficulty and sophistry strength. The annotation format is meant to be stable and readable by other tools, in particular the Burrow reader.

## Design principles

- Passes are separable and testable on their own.
- Model calls go through one thin client layer, so tests can use recorded responses and cost can be counted.
- Results are cached by input hash so passes are cheap to re-run.
- Scores from a model are noisy, so every test that depends on them states how it handles variance.

## Status

v0.1 is a harness and test strategy first. See `Docs/testing-strategy.md`. Only `types.combine` is implemented so far, and `pipeline.score_text` raises `NotImplementedError`.
