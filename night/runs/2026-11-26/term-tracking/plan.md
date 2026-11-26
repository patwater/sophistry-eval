# Plan: term-tracking pass (night 2026-11-26, task 1)

Source: `Specs/initial-build.md`, proposed answer 1 (build term tracking first) and answer 7 (annotation format with `start` and `end` offsets). There are no `ready` bugs in `TODOS.md`.

This continues the plan drafted on 2026-11-21 (`night/runs/2026-11-21/term-tracking/plan.md`). That plan went through one review round, where both personas asked for revisions and all of them were accepted. It was then cut off by the cost cap before a second round. The accepted revisions are carried over below, and a few details are tightened (noted as **new**).

## Scope

In scope:

1. `Annotation` in `sophistry_eval/types.py`:
   - It gains `start` and `end` character offsets into the original text (answer 7), plus a required `source`, the name of the pass that produced it.
   - `source` is an addition to answer 7. Once five passes write into one list, a reader (Burrow, or the e2e test) must be able to tell which pass made a note, and the same `kind` could come from two passes, for example equivocation from term tracking and from the adversarial verifier. It has no default, so no annotation is ever anonymous.
   - Field order is `kind, quote, start, end, note, source`.
   - `__post_init__` rejects:
     - `start < 0` or `end < start`;
     - `end - start != len(quote)` (**new**: the span must be the quote's length, so offsets and quote cannot disagree);
     - an empty `kind` or `source`.
   - The JSON form:
     - `ANNOTATION_FORMAT = 1`.
     - `annotations_to_json(annotations) -> str` writes `{"format": 1, "annotations": [{"kind", "quote", "start", "end", "note", "source"}, ...]}` with those fixed key names.
     - `annotations_from_json` reads it back. It rejects another format, a missing key, an unknown key, or a wrong type (**new**). `start` and `end` must be ints, and `bool` does not count as an int. `kind`, `quote`, `note` and `source` must be strings. Unknown keys are rejected, so any added field is a format bump to 2, never a silent extension.
     - **Offsets** (**new**) are counted in Unicode code points into the text exactly as the pass received it, as Python string indices. Callers read files as UTF-8 with no newline translation and no normalisation (the tests use `read_bytes().decode("utf-8")`). A JavaScript reader such as Burrow, which indexes by UTF-16 code units, must convert them. This goes in the Output section of `Docs/overview.md`, with a test that pins code points against bytes and UTF-16 units.
     - A round-trip test pins the key names, so the format is set by this contract and not by Python field names.
     - Format 1 has one span per annotation. A note that relates two spans carries the second only in its prose. Linking two spans, which equivocation, motte-and-bailey and the adversarial verifier will all want, needs format 2. This is logged in `TODOS.md`.
   - The only existing construction, in `tests/test_types.py`, uses keywords and is updated.
2. A new package `sophistry_eval.passes`:
   - `passes/common.py` holds helpers that every later pass will need:
     - `PassOutputError(ValueError)`, raised when a model reply cannot be used.
     - `parse_json_object(reply)` accepts bare JSON or exactly one fenced code block (with or without a `json` tag), and requires a top-level object. Two fenced blocks are rejected rather than guessed between.
     - `anchor_quote(text, quote)` returns `(start, end)`. It raises if the quote is empty or whitespace, missing, or occurs more than once. Overlapping occurrences count (**new**). An ambiguous quote is rejected rather than guessed, and the prompt tells the model to quote enough words to be unique. Matching is exact: no whitespace or case normalisation, so offsets are always true offsets into the original text.
   - `passes/term_tracking.py` holds the pass:
     - `PASS_NAME = "term_tracking"` and `SYSTEM_PROMPT`.
     - `track_terms(text, *, client, system_prompt=SYSTEM_PROMPT) -> TermReport`. The prompt can be swapped so that variants can be tried without editing code. The pass makes exactly one model call.
     - `TermReport` has `terms: tuple[TrackedTerm, ...]`, `equivocations: tuple[Equivocation, ...]` and `annotations: tuple[Annotation, ...]`.
     - `TrackedTerm(term, senses: tuple[str, ...])`.
     - `Equivocation(term, first_quote, first_start, first_end, first_sense, shifted_quote, shifted_start, shifted_end, shifted_sense, explanation)`, with both uses stored as start and end offsets, like annotations.
     - The pass depends only on the `ModelClient` protocol, so a `RecordedClient` can drive it offline and any model can be plugged in.
3. Docs:
   - In `Docs/overview.md`:
     - Update the status.
     - Under Pipeline, add one line (**new**): term tracking takes the text only and does not depend on claim extraction, and the numbering is not a dependency order.
     - Say that each pass returns a typed report whose `annotations` use the shared format.
     - Under Output, list the annotation fields, the JSON form, the unknown-key rule, the offset unit and text convention, and the one-span limit.
   - In `Docs/rubrics.md`, add a short section on what term tracking checks. It covers how equivocation (one term, two senses, an inference that needs them to be one) differs from a part-whole slide (a property moved from parts to the whole), using a neutral textbook example: "each brick is light, so the wall is light" (**new**: not the fixture's own case).
   - Rewrite the flaw description in `tests/fixtures/equivocation/README.md` (**new**: reworded, not just added to):
     - The planted flaw is an equivocation on "efficiency". It is carried by the shortened restatement "efficiency means using less water", which drops "to accomplish the same task". The two senses are less water per task and less water in total. "Per task" and "total use" are two quantities, and the equivocation is the term "efficiency" being made to stand for both.
     - The planted flaw is not pure. It also rests on an unstated premise that the number of tasks stays fixed (a rebound or Jevons case, which is presupposition load in the rubric). It has an unsupported "must ... by the same amount", and a final clause that shields the claim from evidence.
     - The control is not fully clean either. "They reduce total use only when paired with a cap or a price" claims a necessity on support ("often invites more units") that establishes only a possibility, which is a modal slip by the rubric's definition. And only `clean.txt` has a well-timed concession and an appeal to evidence, which the rubric counts as force, so "force roughly flat" is an assumption the e2e test must test, not take for granted.
     - The pair also differs in difficulty, since the planted text defends a stronger claim.
     - So the e2e test may credit an integrity drop to the planted text as a whole, but not to equivocation alone. It compares integrity and force, never sophistry.
     - The fixture texts are unchanged, since the existing e2e test was written against them. Whether to soften the control's "only when" (for example to "may not reduce total use unless") is a question for Patrick in `TODOS.md`, and a purer pair is in the backlog.

Out of scope, logged in `TODOS.md`:

- Wiring the pass into `score_text`. Term tracking yields annotations, not the three scores. `score_text` still needs a scoring step that the spec has not yet described, so `tests/test_e2e_metamorphic.py` still fails, as expected.
- The input-hash result cache. It is already in `TODOS.md`, and its key must come from `client.prompt_key` plus the model and settings.
- Live model calls and recordings. The first recorded run on the fixtures belongs with the scoring task, using `measure_scores`. Tonight's budget is better spent on a plumbing change that can be fully tested offline.
- Equivocations carried by a pronoun or near-synonym, which the validation rule below cannot express.

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

- `terms` lists the key terms the argument relies on, each with every sense in which the text uses it, and at least one sense.
- `equivocations` lists only shifts that the argument relies on. An empty list is a valid answer and the expected one for most sound texts.
- Unknown extra keys are ignored. Missing `terms` or `equivocations` raises.

The user prompt wraps the text in `<text>` tags and passes it verbatim.

## The system prompt's definition of equivocation

The prompt defines an equivocation as one term used in two different senses, where an inference only goes through if the senses are treated as one. It tells the model not to flag:

- a distinction the author draws openly between two senses or two quantities (`clean.txt` separates efficiency from total use);
- ordinary polysemy that carries no inference;
- figures of speech the reader is meant to read as figures, which are a matter of force, not integrity.

It also:

- asks for verbatim quotes long enough to occur exactly once in the text;
- tells the model to report only shifts where the term itself appears in both quotes. This matches the validation rule below, so a reply that follows the prompt cannot fail validation for that reason.
- says that moving a property from parts to the whole ("each brick is light, so the wall is light") is a part-whole slide, not an equivocation, unless the term's meaning also changes. Term tracking does not report part-whole slides; that belongs to a later pass.
- asks for JSON only.

**New:** the prompt's examples must not come from the test fixtures, since citing the fixture's own case as "not an equivocation" would steer the model on the very test meant to measure it. A test checks that the prompt does not mention the fixture's vocabulary (water, device, community, toilet, efficiency).

## Validation (strict, nothing is silently dropped)

Each tracked term must have a non-empty `term` and a non-empty list of non-empty sense strings.

Each equivocation must satisfy all of the following, or the pass raises `PassOutputError`:

- every required field is a non-empty string;
- both quotes anchor uniquely in the text;
- both quotes contain the term, case-insensitively (`casefold`);
- the two anchored spans do not overlap (**new**: stricter than "different spans", since overlapping quotes cannot be two separate uses);
- the two senses differ after normalising case and whitespace.

Requiring the term in both quotes is a soundness check against the model pointing at the wrong sentence. Its cost is that an equivocation carried only by a pronoun or a near-synonym cannot be reported. That case is logged in `TODOS.md` for a later pass that can link a near-synonym explicitly. The equivocation's term is not required to appear in `terms`, since that would fail a whole run over a bookkeeping slip that does not affect the finding.

Raising on malformed output, rather than skipping the bad item, means a bad reply fails loudly instead of quietly lowering the equivocation count. The cost is that one bad reply fails a whole run. That fits a validation harness.

## Annotations

Each equivocation becomes one annotation with `kind="equivocation"` and `source="term_tracking"`, anchored at the shifted use. The note names the term, both senses, the first quote and the explanation. Only equivocations become annotations in v0.1. Tracked terms stay in the report, so a later reader view can show them without the format changing.

## Testing plan

`tests/test_term_tracking.py` is written and fails at import, as expected. It has about 50 test cases (counting parametrized ones), all offline, with a canned client:

- `anchor_quote`: correct offsets, a missing quote, an ambiguous quote (a phrase that really occurs twice in `planted.txt`), an empty or whitespace quote, and overlapping occurrences.
- `parse_json_object`: bare JSON, a fenced block with and without a tag, two fenced blocks, and four non-objects.
- `Annotation`:
  - rejection of bad offsets, a length mismatch, and an empty `kind` or `source`;
  - the JSON round trip with fixed key names;
  - rejection of another format, a missing key, an unknown key, and seven wrong types, including `start: true`, a float `end`, and non-string `kind`, `note` and `source`;
  - offsets count code points, checked on a string with a two-byte character and an astral one.
- `track_terms`:
  - the prompt carries the text and the system prompt, and the system prompt can be swapped;
  - the system prompt mentions equivocation, inference, distinction, polysemy, figure, part-whole, verbatim and JSON (a smoke check that the definition and all three exclusions are present, not a test of their quality);
  - the system prompt does not use the fixture's vocabulary;
  - the planted equivocation anchors exactly at the shifted use in `planted.txt`, with `text[start:end] == quote`, and the note carries the term, both senses, the first quote and the explanation;
  - the report keeps both uses and the terms;
  - no equivocations gives no annotations;
  - the term match ignores case, and a fenced reply is accepted;
  - each validation rule above, a missing field, and nine malformed payloads. The term-in-both-quotes rule is tested on each quote separately (a term found only in the first quote, and one found only in the shifted quote), so checking just one quote would fail.

These test plumbing only. Whether a model finds the planted equivocation, and does not flag `clean.txt`, is tested by the end-to-end metamorphic test once scoring exists. **Variance:** there are no model calls in this task, so there is no variance to report. The e2e test will use `measure_scores` with `DEFAULT_RUNS` per the existing TODO.

`tests/test_types.py` is updated for the new `Annotation` fields.

## Review history

Round 1 (2026-11-21), both REVISE:

- Architect: justify and require `source`; define the JSON form with a version and a round-trip test; store end offsets; allow the system prompt to be swapped; mention the cache; update the overview's pipeline and output sections. All accepted.
- Logician:
  - The near-synonym clause in the prompt contradicted the validation rule, so it is removed.
  - The fixture flaw is not pure, and the pair is confounded on difficulty. Both are documented in the README, with a purer pair added to TODOS.
  - Equivocation versus part-whole slide goes in the prompt and in the rubrics.
  - All accepted.

Round 2 (2026-11-26), both REVISE, all accepted:

- Architect:
  1. Fix the type-rule wording: `start` and `end` are ints.
  2. State the offset unit and the text convention, and read fixtures without newline translation.
  3. Decide on unknown keys. They are now rejected.
  4. Test the `bool` rule and other types.
  5. Add the Pipeline line on independence.
  6. Say that format 1 has one span, and log format 2 in TODOS.
- Logician:
  1. Remove the fixture's own case from the prompt's part-whole example and use bricks and a wall. A test now guards this.
  2. Reword the README's flaw description, since per task and total use are two quantities, not two senses. Describe the second flaw as the fixed-task-count presupposition.
  3. Document the control's modal slip and the force confound in the README. Softening the control text is Patrick's call.
  4. Add polysemy and figures to the exclusion test.
  5. Test each quote for the term separately.
  6. Test the type rules.
  7. Check the first quote and the explanation in the note.
