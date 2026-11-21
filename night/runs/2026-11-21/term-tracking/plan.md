# Plan: term-tracking pass (night 2026-11-21, task 2)

Source: `Specs/initial-build.md`, proposed answer 1 (build term tracking first) and answer 7 (annotation format with `start` and `end` offsets). There are no `ready` bugs in `TODOS.md`.

## Scope

In scope:

1. `Annotation` gains `start` and `end` character offsets into the original text (answer 7), plus a required `source`, the name of the pass that produced it. `source` is an addition to answer 7: once five passes write into one list, a reader (Burrow, or the e2e test) needs to tell which pass made a note, and the same `kind` could come from two passes, for example equivocation from term tracking and from the adversarial verifier. It has no default, so no annotation is ever anonymous. `__post_init__` rejects `start < 0`, `end < start`, and an empty `source`. Field order: `kind, quote, start, end, note, source`. The only existing construction, in `tests/test_types.py`, uses keywords and is updated.
   - Serialized form: `ANNOTATION_FORMAT = 1`. `annotations_to_json(annotations) -> str` writes `{"format": 1, "annotations": [{"kind", "quote", "start", "end", "note", "source"}, ...]}` with those fixed key names. `annotations_from_json` reads it back, rejecting other formats or missing keys. A round-trip test pins the key names, so the format is set by this contract and not by Python field names.
2. A new package `sophistry_eval.passes`:
   - `passes/common.py` holds helpers that every later pass will need:
     - `PassOutputError(ValueError)`, raised when a model reply cannot be used.
     - `parse_json_object(reply)` accepts bare JSON or exactly one fenced code block, and requires a top-level object.
     - `anchor_quote(text, quote)` returns `(start, end)`. It raises if the quote is empty, missing, or appears more than once. An ambiguous quote is rejected rather than guessed, and the prompt tells the model to quote enough words to be unique.
   - `passes/term_tracking.py` holds the pass:
     - `PASS_NAME = "term_tracking"`, `SYSTEM_PROMPT`.
     - `track_terms(text, *, client) -> TermReport`.
     - `TermReport` has `terms: tuple[TrackedTerm, ...]`, `equivocations: tuple[Equivocation, ...]` and `annotations: tuple[Annotation, ...]`.
     - `TrackedTerm(term, senses)`.
     - `Equivocation(term, first_quote, first_start, first_end, first_sense, shifted_quote, shifted_start, shifted_end, shifted_sense, explanation)`, with both uses stored as start and end offsets like annotations.
     - `track_terms` takes `system_prompt: str = SYSTEM_PROMPT`, so prompt variants can be tried without editing code.
3. Docs:
   - In `Docs/overview.md`, update the status, say that each pass returns a typed report whose `annotations` use the shared format, and list the annotation fields and the JSON form under Output.
   - In `Docs/rubrics.md`, add a short section on what term tracking checks, including how equivocation (a shift in what a term means) differs from a part-whole slide (a shift in the scope of a property).
   - In `tests/fixtures/equivocation/README.md`, note two things. First, the planted flaw is not pure: alongside the term shift there is a part-whole slide, an unsupported "must ... by the same amount", and a final clause that shields the claim from evidence. Second, the pair also differs in difficulty, since the planted text defends a stronger claim. So the e2e test may credit an integrity drop to the planted text as a whole, but not to equivocation alone. It compares integrity and force, never sophistry. A purer pair is logged in `TODOS.md`. The fixture text is unchanged, since the existing e2e test was written against it.

Out of scope, logged in `TODOS.md`:

- Wiring the pass into `score_text`. Term tracking yields annotations, not the three scores, so `score_text` still needs a scoring step that the spec has not yet described. `tests/test_e2e_metamorphic.py` therefore still fails, as expected.
- The input-hash result cache. It is already in `TODOS.md`, and its key must come from `client.prompt_key` plus the model and settings.
- Live model calls and recordings. No live call is made tonight because the remaining budget is small (about $5). The first recorded run on the fixtures belongs with the scoring task, using `measure_scores`.

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
- figures of speech the reader is meant to read as figures, which are a matter of force, not integrity.

It asks for verbatim quotes long enough to occur exactly once in the text, and tells the model to report only shifts where the term itself appears in both quotes. This matches the validation rule below, so a reply that follows the prompt cannot fail validation for that reason. It also tells the model that a shift in the scope of a property (from a part to the whole, such as from a device to a community) is a part-whole slide, not an equivocation, unless the term's meaning also changes.

## Validation (strict, nothing is silently dropped)

Each equivocation must satisfy all of the following, or the pass raises `PassOutputError`:

- every required field is a non-empty string;
- both quotes anchor uniquely in the text;
- both quotes contain the term, case-insensitively;
- the two quotes are different spans;
- the two senses differ after normalising case and whitespace.

Requiring the term in both quotes is a soundness check against the model pointing at the wrong sentence. Its cost is that an equivocation carried only by a pronoun or a near-synonym cannot be reported. That case is logged in `TODOS.md` for a later pass that can link a near-synonym explicitly.

Raising on malformed output, rather than skipping the bad item, means a bad reply fails loudly instead of quietly lowering the equivocation count. The cost is that one bad reply fails a whole run. That fits a validation harness.

## Annotations

Each equivocation becomes one annotation with `kind="equivocation"`, `source="term_tracking"`, anchored at the shifted use. The note names the term, both senses, the first quote and the explanation. Only equivocations become annotations in v0.1. Tracked terms stay in the report, so a later reader view can show them without the format changing.

## Testing plan

`tests/test_term_tracking.py` is written and fails at import, as expected. It has about 30 tests, all offline, using a canned client:

- `anchor_quote`: correct offsets, a missing quote, an ambiguous quote, and an empty quote;
- `parse_json_object`: bare JSON, a fenced block, and non-object rejection;
- `Annotation` validation of offsets and `source`, and the JSON round trip with fixed key names and format rejection;
- `track_terms`:
  - the prompt carries the text;
  - the system prompt defines equivocation and mentions open distinctions;
  - the planted equivocation anchors exactly at the shifted use in `planted.txt`, with `text[start:end] == quote`;
  - the report keeps both uses and the terms;
  - no equivocations gives no annotations;
  - each validation rule above, and five malformed payloads.

These test plumbing only. Whether a model finds the planted equivocation, and does not flag `clean.txt`, is tested by the end-to-end metamorphic test once scoring exists. **Variance:** there are no model calls tonight, so there is no variance to report. The e2e test will use `measure_scores` with `DEFAULT_RUNS` per the existing TODO.

The existing `test_types.py` will be updated for the new `Annotation` fields.

## Review history

Round 1, both REVISE:

- Architect: justify and require `source`; define the JSON form with a version and a round-trip test; store end offsets; allow the system prompt to be swapped; mention the cache; update the overview's pipeline and output sections. All accepted.
- Logician:
  - The near-synonym clause in the prompt contradicted the validation rule, so it is removed.
  - The fixture flaw is not pure, and the pair is confounded on difficulty. Both are documented in the README, with a purer pair added to TODOS.
  - Equivocation versus part-whole slide goes in the prompt and in the rubrics.
  - All accepted.
