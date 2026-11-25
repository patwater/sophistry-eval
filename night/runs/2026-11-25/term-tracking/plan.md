# Plan: term-tracking pass (night 2026-11-25, task 1)

Source: `Specs/initial-build.md`, proposed answer 1 (build term tracking first) and answer 7 (annotation format with `start` and `end` offsets). There are no `ready` bugs in `TODOS.md`.

History: this plan was first written on 2026-11-21 (task 2) and went through one review round, in which both personas asked for changes. That run then stopped at its spend cap before a second round, and nothing was implemented. The round-1 fixes are already folded in below, and the earlier record is in `night/runs/2026-11-21/term-tracking/plan.md`. Tonight's additions are marked **(new)**.

## Scope

In scope:

1. `Annotation` gains `start` and `end` character offsets into the original text (answer 7), plus a required `source`, the name of the pass that produced it.
   - Why `source` is added to answer 7: once five passes write into one list, a reader (Burrow, or the e2e test) needs to tell which pass made a note. The same `kind` could also come from two passes, for example equivocation from term tracking and from the adversarial verifier. `source` has no default, so no annotation is ever anonymous.
   - `__post_init__` rejects:
     - `start < 0` and `end < start`;
     - an empty `kind` or `source`;
     - **(new)** `end - start != len(quote)`. This is a cheap invariant that catches offsets computed against the wrong string. It cannot check `text[start:end] == quote`, since an annotation does not hold the text. The pass guarantees that, and the tests check it.
   - Field order: `kind, quote, start, end, note, source`. The only existing construction, in `tests/test_types.py`, uses keywords and is updated.
   - **(round 2) Offset unit.** `start` and `end` count Unicode code points (Python `str` indices) into the exact string the pass was given, with no newline or Unicode normalisation. A JavaScript reader such as Burrow, which counts UTF-16 units, must convert. A test with a non-BMP character before the quote pins this down.
   - Serialized form: `ANNOTATION_FORMAT = 1`. `annotations_to_json(annotations, *, text) -> str` writes `{"format": 1, "text_sha256": "<hex>", "annotations": [{"kind", "quote", "start", "end", "note", "source"}, ...]}` with those fixed key names.
     - **(round 2)** `text_sha256` is the SHA-256 of the UTF-8 encoding of the text the offsets index into. It is in format 1 from the start, so a reader can tell whether a saved file matches the text it has. It also lines up with the planned input-hash cache.
     - `annotations_from_json(data, *, text=None)` reads it back. It rejects other formats, a missing or non-string hash, missing keys, and wrong types (**new**: `bool` is not accepted as an int). When `text` is given, it also rejects a hash mismatch.
     - A round-trip test pins the key names, so the format is set by this contract and not by Python field names.
2. A new package `sophistry_eval.passes`:
   - `passes/common.py` holds helpers that every later pass will need:
     - `PassOutputError(ValueError)`, raised when a model reply cannot be used.
     - `parse_json_object(reply)` accepts bare JSON or exactly one fenced code block, and requires a top-level object.
     - `anchor_quote(text, quote)` returns `(start, end)`. It raises if the quote is empty, missing, or appears more than once, **(new)** counting overlapping occurrences. An ambiguous quote is rejected rather than guessed, and the prompt tells the model to quote enough words to be unique.
   - `passes/term_tracking.py` holds the pass:
     - `PASS_NAME = "term_tracking"` and `SYSTEM_PROMPT`.
     - `track_terms(text, *, client, system_prompt=SYSTEM_PROMPT) -> TermReport`. The prompt can be swapped without editing code.
     - `TermReport` has `terms: tuple[TrackedTerm, ...]`, `equivocations: tuple[Equivocation, ...]` and `annotations: tuple[Annotation, ...]`.
     - `TrackedTerm(term, senses: tuple[str, ...])`, with at least one non-empty sense.
     - `Equivocation(term, first_quote, first_start, first_end, first_sense, shifted_quote, shifted_start, shifted_end, shifted_sense, explanation)`. Both uses are stored as start and end offsets, like annotations.
     - All are frozen dataclasses. The pass reads only its input text, so it can be cached by input hash later.
3. Docs:
   - `Docs/overview.md`:
     - Update the status.
     - Say that each pass returns a typed report whose `annotations` use the shared format.
     - List the annotation fields and the JSON form under Output.
   - `Docs/rubrics.md`: add a short section on what term tracking checks. It covers how equivocation (a shift in what a term means) differs from a part-whole slide (a shift in the scope of a property).
   - `tests/fixtures/equivocation/README.md`, note two things:
     - The planted flaw is not pure. Alongside the term shift there is a part-whole slide, an unsupported "must ... by the same amount", and a final clause that shields the claim from evidence.
     - The pair also differs in difficulty, since the planted text defends a stronger claim.
     - **(round 2)** The pair also differs in force. `planted.txt` drops the evidence sentence ("History shows...") and the scoped concession, and `Docs/rubrics.md` counts both as force. So "force stays roughly flat" is a loose check on a confounded pair, not a clean control.

     So the e2e test may credit an integrity drop to the planted text as a whole, but not to equivocation alone. It compares integrity and force, never sophistry. A purer pair is logged in `TODOS.md`: one controlled term shift with evidence and concessions kept matched. The fixture text is unchanged, since the existing e2e test was written against it.
   - **(round 2)** The docstring of `tests/test_e2e_metamorphic.py` is updated to match the README. The assertions are unchanged.

Out of scope, logged in `TODOS.md`:

- Wiring the pass into `score_text`.
  - Term tracking yields annotations, not the three scores, so `score_text` still needs a scoring step that the spec has not yet described.
  - So `tests/test_e2e_metamorphic.py` still fails, as expected.
  - The e2e test's `clean` assertion (no `equivocation` annotation) will need to filter by `source` or accept the stated limit.
- The input-hash result cache. It is already in `TODOS.md`, and its key must come from `client.prompt_key` plus the model and settings.
- Live model calls and recordings. The first recorded run on the fixtures belongs with the scoring task, using `measure_scores`. No live call is made tonight. That keeps the night's spend on building and reviewing, and an unvalidated prompt is cheaper to tune once the scoring step can consume it.

## The model contract

The model is asked for one JSON object:

```json
{
  "terms": [{"term": "efficiency", "senses": ["less water per task"]}],
  "equivocations": [{
    "term": "efficiency",
    "first_quote": "...", "first_sense": "...",
    "shifted_quote": "...", "shifted_sense": "...",
    "explanation": "..."
  }]
}
```

`terms` lists the key terms the argument relies on, each with every sense in which the text uses it. `equivocations` lists only shifts that the argument relies on.

## The system prompt's definition of equivocation

The prompt defines an equivocation as one term used in two different senses, where an inference only goes through if the senses are treated as one. It tells the model not to flag:

- a distinction the author draws openly between two senses or two quantities (`clean.txt` separates efficiency from total use);
- ordinary polysemy that carries no inference;
- **(round 2)** figures of speech on which no inference depends. Their craft is a matter of force, not integrity. A figure that is later read literally to carry an inference is still checked.

It asks for verbatim quotes long enough to occur exactly once in the text, and tells the model to report only shifts where the term itself appears in both quotes. This matches the validation rule below, so a reply that follows the prompt cannot fail validation for that reason. It also tells the model that a shift in the scope of a property (from a part to the whole, such as from a device to a community) is a part-whole slide, not an equivocation, unless the term's meaning also changes.

## Validation (strict, nothing is silently dropped)

The payload must have a `terms` list and an `equivocations` list. Each term needs a non-empty `term` and a non-empty list of non-empty string `senses`.

Each equivocation must satisfy all of the following, or the pass raises `PassOutputError`:

- every required field is a non-empty string;
- both quotes anchor uniquely in the text;
- both quotes contain the term as a whole word or phrase, case-insensitively, so "inefficiency" does not count as "efficiency" **(round 2)**;
- the two spans do not overlap, so one occurrence of the term cannot be reported as two uses **(round 2; it was "different spans")**;
- the two senses differ after normalising case and whitespace.

Requiring the term in both quotes is a soundness check against the model pointing at the wrong sentence. Its cost is that an equivocation carried only by a pronoun or a near-synonym cannot be reported. That case is logged in `TODOS.md` for a later pass that can link a near-synonym explicitly.

Raising on malformed output, rather than skipping the bad item, means a bad reply fails loudly instead of quietly lowering the equivocation count. The cost is that one bad reply fails a whole run. That fits a validation harness.

## Annotations

Each equivocation becomes one annotation with `kind="equivocation"` and `source="term_tracking"`, anchored at the shifted use. The note names the term, both senses, the first quote and the explanation. Only equivocations become annotations in v0.1. Tracked terms stay in the report, so a later reader view can show them without the format changing.

## Testing plan

`tests/test_term_tracking.py` is written and fails at import (`No module named 'sophistry_eval.passes'`), as expected. All of it is offline and uses a canned client that records its prompts. It covers:

- `anchor_quote`: correct offsets, a missing quote, an ambiguous quote, overlapping repeats, and an empty quote.
- `parse_json_object`: bare JSON, one fenced block, two fenced blocks rejected, and non-objects and non-JSON rejected.
- `Annotation`:
  - validation of `start`, `end`, `kind`, `source` and the quote length;
  - the JSON round trip with fixed key names;
  - rejection of another format, a missing key, and a wrong type.
- `track_terms`, the prompt:
  - the prompt carries the text;
  - the system prompt is the module's constant and can be swapped;
  - the system prompt names equivocation, open distinctions, part-whole slides, figures, and "exactly once".
- `track_terms`, the report:
  - The planted equivocation anchors exactly at the shifted use in `planted.txt`, with `text[start:end] == quote`.
  - The report keeps both uses and the terms.
  - No equivocations gives no annotations, run on `clean.txt`.
  - A fenced reply is accepted.
- `track_terms`, validation:
  - each validation rule above;
  - a missing field;
  - a case-insensitive term match;
  - six malformed payloads.

`tests/test_types.py` is updated for the new `Annotation` fields.

These tests check plumbing only. Whether a model finds the planted equivocation, and does not flag `clean.txt`, is tested by the end-to-end metamorphic test once scoring exists. **Variance:** there are no model calls tonight, so there is no variance to report. The e2e test will use `measure_scores` with `DEFAULT_RUNS` per the existing TODO.

**(round 2) Tests added:**

- the non-BMP offset case;
- the `text_sha256` field, both a missing hash and a mismatched text;
- `bool` rejected as `start` or `end`;
- overlapping quotes that share one occurrence of the term;
- a whole-word miss ("funding" for the term "fund");
- the reworded figures clause.

## Deviations in implementation

- `PASS_NAME` is renamed `SOURCE`. Ruff's `S105` flags any constant whose name contains "pass" as a possible hardcoded password. That is a false positive, but per `CLAUDE.md` the rule is not suppressed. `SOURCE` also names what the constant is: the `source` value on this pass's annotations.
- Parameters that take unparsed JSON are typed `object` rather than `Any` (ruff `ANN401`), and are narrowed with `isinstance`.
- `track_terms` builds its user prompt with a public `build_prompt(text)`, which wraps the text in `<text>` tags. That way a later recording or cache can rebuild the same prompt key.

## Review history

Diff review, round 1 (2026-11-25): both APPROVE. The logician's optional point is taken up: the two whole-word test cases now match "whole word" rather than "term", which also appears in other error messages.

Plan round 3 (2026-11-25): both APPROVE. Two optional notes are taken up in implementation:

- The architect suggested that the overview's Output section state the offset unit and `text_sha256`.
- The logician suggested that the README note say the dropped "History shows..." sentence is evidence, so it bears on integrity as well as force.

Round 2 (2026-11-25), both REVISE, all accepted and folded in above:

- Architect asked for:
  - the offset unit to be defined;
  - `text_sha256` in the envelope;
  - a test for `bool` as an int.
- Logician asked for:
  - overlap, not identity, as the span rule;
  - a whole-word term match;
  - a narrower figures exclusion;
  - the force confound to be documented;
  - the e2e docstring to match the README.

Round 1 (2026-11-21), both REVISE:

- Architect asked for these changes, all accepted:
  - justify and require `source`;
  - define the JSON form with a version and a round-trip test;
  - store end offsets;
  - allow the system prompt to be swapped;
  - mention the cache;
  - update the overview's pipeline and output sections.
- Logician asked for these changes, all accepted:
  - The near-synonym clause in the prompt contradicted the validation rule, so it is removed.
  - The fixture flaw is not pure, and the pair is confounded on difficulty. Both are documented in the README, with a purer pair added to TODOS.
  - Equivocation versus part-whole slide goes in the prompt and in the rubrics.
