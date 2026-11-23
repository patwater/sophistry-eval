# Overview

sophistry-eval reads a piece of writing and reports how well it makes its case. It scores three things separately and then combines them.

- **Persuasive force** is how strongly the prose pulls a reader toward its conclusion.
- **Conceptual integrity** is how well the terms, claims and inferences hold together.
- **Difficulty of the case** is how hard the position is to defend, so holding an unpopular or demanding thesis earns more credit than defending something everyone already believes.

Sophistry strength is force times integrity times difficulty, with difficulty acting as a multiplier that rewards holding a hard case rather than penalizing easy ones. Whether the combination should be a product or a minimum is an open question in `Specs/initial-build.md`.

## Why the word sophistry

The sophists taught the craft of speaking and arguing well. The long negative meaning owes much to Plato's campaign against them. Here, sophistry in the good sense means high force together with high integrity. A four-way map names the other cases. A dry proof has integrity without force. Demagoguery or eristic has force without integrity. Noise has neither.

## Pipeline

The pipeline is a sequence of independent passes. Each pass takes the text (and sometimes earlier annotations) and returns a typed report that includes annotations in the shared format (see Output).

1. Claim extraction builds a graph of claims, premises and links, with each link tagged as deductive, inductive, analogical or merely rhetorical.
2. Term tracking follows each key term across the piece and flags equivocation.
3. Modal audit flags necessity claims supported only by possibility and unargued slides from "can" to "should".
4. Presupposition load counts what the argument carries as given without stating it.
5. Adversarial verifier runs a prosecutor against a defender. Repairs count as evidence of robustness. The number and strength of objections also feed the difficulty estimate.

## Output

A margin-annotated version of the text and four scores: force, integrity, difficulty and sophistry strength. The annotation format is meant to be stable and readable by other tools, in particular the Burrow reader.

Each pass returns a typed report, such as `TermReport`. Its `annotations` field uses the shared `Annotation` type from `sophistry_eval.types`, which has these fields:

- `kind`: what was found, for example `equivocation`.
- `quote`: the exact span of text the note points at.
- `start` and `end`: offsets of that span, with `text[start:end] == quote`.
- `note`: the explanation shown in the margin.
- `source`: the pass that produced the note, for example `term_tracking`. Two passes can report the same `kind`, so `source` tells them apart.

Offset rules, format 1:

- **Units.** Offsets count Unicode code points, which is Python `str` indexing and also what W3C `TextPositionSelector` uses. They are not UTF-16 units, so a JavaScript reader must convert them.
- **Which text.** Offsets index the exact string given to the pass. That string must use `\n` newlines only. The caller normalizes, and a pass refuses any text that contains `\r`.

Serialized form, format 1, from `annotations_to_json(annotations, text=...)`:

```json
{
  "format": 1,
  "text_sha256": "<SHA-256 hex of the text's UTF-8 bytes>",
  "annotations": [
    {"kind": "equivocation", "quote": "...", "start": 0, "end": 0, "note": "...", "source": "term_tracking"}
  ]
}
```

`annotations_from_json(encoded, text=...)` reads this back. It rejects the input when any of these hold:

- the format is not 1;
- `text_sha256` does not match the given text;
- a key is missing or has the wrong type;
- an annotation has an unknown key. Format 1 is closed, so a new field means format 2.
- a quote does not match its span.

The writer refuses to serialize an annotation that misses its span.

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
- The annotation format described under Output, with `text_sha256`, `annotations_to_json` and `annotations_from_json` in `sophistry_eval.types`.
- `sophistry_eval.passes.common`:
  - `parse_json_object` accepts a reply that is bare JSON or exactly one fenced block.
  - `anchor_quote` finds a quote's unique span. It raises when the quote is empty, missing or repeated.
  - Both raise `PassOutputError`.
- The term-tracking pass, `sophistry_eval.passes.term_tracking.track_terms(text, client=..., system_prompt=...)`. It returns a `TermReport` with the key terms and their senses, the equivocations with both uses anchored, and one annotation per equivocation at the shifted use. Malformed replies raise and are never silently dropped. See `Docs/rubrics.md` for what it checks.

No scoring step exists yet. `pipeline.score_text` still raises `NotImplementedError`, because term tracking yields annotations and not the three scores.
