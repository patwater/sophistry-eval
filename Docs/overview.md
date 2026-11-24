# Overview

sophistry-eval reads a piece of writing and reports how well it makes its case. It scores three things separately and then combines them.

- **Persuasive force** is how strongly the prose pulls a reader toward its conclusion.
- **Conceptual integrity** is how well the terms, claims and inferences hold together.
- **Difficulty of the case** is how hard the position is to defend, so holding an unpopular or demanding thesis earns more credit than defending something everyone already believes.

Sophistry strength is force times integrity times difficulty, with difficulty acting as a multiplier that rewards holding a hard case rather than penalizing easy ones. Whether the combination should be a product or a minimum is an open question in `Specs/initial-build.md`.

## Why the word sophistry

The sophists taught the craft of speaking and arguing well. The long negative meaning owes much to Plato's campaign against them. Here, sophistry in the good sense means high force together with high integrity. A four-way map names the other cases. A dry proof has integrity without force. Demagoguery or eristic has force without integrity. Noise has neither.

## Pipeline

The pipeline is a sequence of independent passes. Each pass takes the text (and sometimes earlier annotations) and returns a typed report. The report's `annotations` use the shared format described under Output. Every pass must receive the identical original string, never a cleaned or reformatted copy, so that offsets from different passes line up.

1. Claim extraction builds a graph of claims, premises and links, with each link tagged as deductive, inductive, analogical or merely rhetorical.
2. Term tracking follows each key term across the piece and flags equivocation.
3. Modal audit flags necessity claims supported only by possibility and unargued slides from "can" to "should".
4. Presupposition load counts what the argument carries as given without stating it.
5. Adversarial verifier runs a prosecutor against a defender. Repairs count as evidence of robustness. The number and strength of objections also feed the difficulty estimate.

## Output

A margin-annotated version of the text and four scores: force, integrity, difficulty and sophistry strength. The annotation format is meant to be stable and readable by other tools, in particular the Burrow reader.

### Annotation format

An `Annotation` (in `sophistry_eval.types`) has six fields:

- `kind` names the finding, for example `equivocation`.
- `quote` is the exact span of the text the note points at.
- `start` and `end` are offsets such that `text[start:end] == quote`.
- `note` is the margin note itself.
- `source` names the pass that made the note, for example `term_tracking`. Two passes can report the same `kind`, so the reader needs to know which one spoke.

Rules a reader can rely on:

- **Offsets count Unicode code points**, which are Python string indices. A reader that counts UTF-16 code units (JavaScript, so Burrow) or bytes must convert.
- **Offsets point into the exact text the pass received**, with no normalisation of line endings, whitespace or quote marks.
- **Serialized form.** `annotations_to_json` writes the following, and `annotations_from_json` reads it back:

  ```json
  {"format": 1, "annotations": [{"kind": "...", "quote": "...", "start": 0, "end": 0, "note": "...", "source": "..."}]}
  ```

  `format` lets a reader detect a breaking change instead of misreading it. This is why the form is a wrapper object and not a bare list.
- **Strict reading.** Another format, a missing or unknown key, or a wrongly typed value is rejected. Any new or changed field therefore bumps `ANNOTATION_FORMAT`.

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
- The annotation format above, with `annotations_to_json` and `annotations_from_json`.
- `sophistry_eval.passes.common`, the helpers every pass needs:
  - `parse_json_object` reads a model reply;
  - `anchor_quote` turns a quote into offsets and rejects a missing or ambiguous quote;
  - `PassOutputError` is raised for an unusable reply.
- The term-tracking pass, `sophistry_eval.passes.term_tracking.track_terms`.
  - It makes one model call and returns a `TermReport` holding terms, equivocations and annotations.
  - Validation is strict: a malformed reply raises and is never partly used.
  - It reports only shifts where the same word appears at both uses. See `Docs/rubrics.md`.

No pass is wired into `pipeline.score_text` yet, because no scoring step exists. It still raises `NotImplementedError`.
