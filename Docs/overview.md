# Overview

sophistry-eval reads a piece of writing and reports how well it makes its case. It scores three things separately and then combines them.

- **Persuasive force** is how strongly the prose pulls a reader toward its conclusion.
- **Conceptual integrity** is how well the terms, claims and inferences hold together.
- **Difficulty of the case** is how hard the position is to defend, so holding an unpopular or demanding thesis earns more credit than defending something everyone already believes.

Sophistry strength is force times integrity times difficulty, with difficulty acting as a multiplier that rewards holding a hard case rather than penalizing easy ones. Whether the combination should be a product or a minimum is an open question in `Specs/initial-build.md`.

## Why the word sophistry

The sophists taught the craft of speaking and arguing well. The long negative meaning owes much to Plato's campaign against them. Here, sophistry in the good sense means high force together with high integrity. A four-way map names the other cases. A dry proof has integrity without force. Demagoguery or eristic has force without integrity. Noise has neither.

## Pipeline

The pipeline is a sequence of independent passes. Each pass takes the text (and sometimes earlier annotations) and a `ModelClient`, and returns a typed report whose `annotations` use the shared format below. Passes live in `sophistry_eval.passes`, and shared helpers (`PassOutputError`, `parse_json_object`, `anchor_quote`) are in `passes/common.py`. Each pass takes its system prompt as a parameter with a default, so prompt variants can be tried without editing code.

1. Claim extraction builds a graph of claims, premises and links, with each link tagged as deductive, inductive, analogical or merely rhetorical.
2. Term tracking follows each key term across the piece and flags equivocation.
3. Modal audit flags necessity claims supported only by possibility and unargued slides from "can" to "should".
4. Presupposition load counts what the argument carries as given without stating it.
5. Adversarial verifier runs a prosecutor against a defender. Repairs count as evidence of robustness. The number and strength of objections also feed the difficulty estimate.

## Output

A margin-annotated version of the text and four scores: force, integrity, difficulty and sophistry strength. The annotation format is meant to be stable and readable by other tools, in particular the Burrow reader.

### Annotation format (version 1)

An `Annotation` (`sophistry_eval.types`) has these fields:

- `kind`: the move, such as `equivocation`.
- `quote`: the exact span the note points at.
- `start`, `end`: offsets into the text, so `text[start:end] == quote`. They count Unicode code points (Python `str` indices) into the exact string the pass was given, with no newline or Unicode normalisation. A reader that counts UTF-16 units, as JavaScript does, must convert.
- `note`: the explanation for a reader.
- `source`: the pass that made the note, such as `term_tracking`. Two passes can report the same `kind`.

`annotations_to_json(annotations, text=...)` writes:

```json
{"format": 1, "text_sha256": "<hex>", "annotations": [
  {"kind": "...", "quote": "...", "start": 0, "end": 0, "note": "...", "source": "..."}
]}
```

`text_sha256` is the SHA-256 of the UTF-8 text the offsets index into. `annotations_from_json(data, text=...)` refuses a hash mismatch, so offsets never land in the wrong text. Any change to these keys is a new format version.

## Design principles

- Passes are separable and testable on their own.
- Model calls go through one thin client layer, so tests can use recorded responses and cost can be counted. Recorded replies are keyed by a hash of the system prompt and prompt (`client.prompt_key`), and the recording file pins the model and call settings. A recording is a strict test fixture, not a cache.
- Results are cached by input hash so passes are cheap to re-run.
- Scores from a model are noisy, so every test that depends on them states how it handles variance.

## Status

v0.1 is a harness and test strategy first. See `Docs/testing-strategy.md`.

Built so far:

- `types.combine`.
- The client layer in `sophistry_eval.client`:
  - `ClaudeClient` defaults to `claude-sonnet-5-5`, with `claude-haiku-5-5` as the comparison model. It counts tokens in `usage`. It raises on a missing key, and on a reply that is truncated, refused, otherwise incomplete, or empty (`UnusableReplyError`).
  - `RecordingClient` and `RecordedClient` record replies and replay them offline.

- The annotation format above, with JSON round-tripping.
- The term-tracking pass, `passes.term_tracking.track_terms`. It returns a `TermReport` with the key terms, the equivocations (both uses anchored), and one annotation per equivocation, anchored at the shifted use. It is tested offline only. No live run has checked it against the fixtures yet.

`pipeline.score_text` still raises `NotImplementedError`, because nothing yet turns annotations into the three scores.
