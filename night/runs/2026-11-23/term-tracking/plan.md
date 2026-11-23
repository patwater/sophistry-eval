# Plan: term-tracking pass (night 2026-11-23, task 1)

Source: `Specs/initial-build.md`, proposed answer 1 (build term tracking first) and answer 7 (annotation format with `start` and `end` offsets). There are no `ready` bugs in `TODOS.md`.

This continues `night/runs/2026-11-21/term-tracking/plan.md`. That task stopped after the first plan review (both personas said REVISE, and every point was accepted) and wrote no code. The plan below already includes those revisions, plus three small additions marked **new**.

## Scope

In scope:

1. `Annotation` gains `start` and `end` character offsets into the original text (answer 7), plus a required `source`, the name of the pass that produced it.
   - **Why `source`.** It goes beyond answer 7. Once five passes write into one list, a reader (Burrow, or the e2e test) needs to tell which pass made each note. The same `kind` could also come from two passes, for example equivocation from term tracking and from the adversarial verifier. `source` has no default, so no annotation is ever anonymous.
   - **Validation.** `__post_init__` rejects `start < 0`, `end < start`, and an empty `source`. **New:** it also rejects `end - start != len(quote)`. The annotation cannot see the text, but this length check catches offsets that disagree with their own quote.
   - **Field order:** `kind, quote, start, end, note, source`. The only existing construction, in `tests/test_types.py`, uses keywords and is updated.
   - **Offsets (round 2).** `start` and `end` count Unicode code points, which is Python `str` indexing and also what W3C `TextPositionSelector` uses. They are not UTF-16 units, so a JavaScript reader must convert them. They index the exact string passed to the pass, and that string must use `\n` newlines only. The caller normalizes. `track_terms` raises `ValueError` on any `\r` before it calls the model, so offsets can never silently drift against a CRLF file.
   - **Serialized form.** `ANNOTATION_FORMAT = 1`.
     - `text_sha256(text)` is the SHA-256 hex digest of the text's UTF-8 bytes.
     - `annotations_to_json(annotations, *, text) -> str` writes `{"format": 1, "text_sha256": "...", "annotations": [{"kind", "quote", "start", "end", "note", "source"}, ...]}` with those fixed key names. **(Round 2)** It refuses to write an annotation whose `text[start:end] != quote`.
     - `annotations_from_json(encoded, *, text)` reads it back. It rejects another format, a missing key, a value of the wrong type (`start` must be an int and not a bool, and strings must be strings), a `text_sha256` that does not match `text` **(round 2)**, and a quote that does not match its span.
     - A round-trip test pins the key names, so the format is fixed by this contract and not by Python field names. The text hash lets Burrow or the cache detect that annotations belong to a different text, instead of drawing them in the wrong place.
2. A new package, `sophistry_eval.passes`.
   - `passes/common.py` holds helpers that every later pass will need:
     - `PassOutputError(ValueError)`, raised when a model reply cannot be used.
     - `parse_json_object(reply)` accepts bare JSON or exactly one fenced code block, and requires a top-level object.
     - `anchor_quote(text, quote)` returns `(start, end)`. It raises when the quote is empty, missing, or occurs more than once. **New:** overlapping occurrences count, so `"aa"` in `"aaa"` is ambiguous. An ambiguous quote is rejected rather than guessed, and the prompt tells the model to quote enough words to be unique.
   - `passes/term_tracking.py` holds the pass:
     - `SOURCE_NAME = "term_tracking"` and `SYSTEM_PROMPT`. (This was `PASS_NAME` in review. It was renamed during implementation because ruff's S105 reads `PASS` as a password. The rename avoids a false positive without suppressing the rule.)
     - `track_terms(text, *, client, system_prompt=SYSTEM_PROMPT) -> TermReport`. A different prompt can be tried without editing code.
     - `TermReport(terms, equivocations, annotations)`, with each field a tuple.
     - `TrackedTerm(term, senses: tuple[str, ...])`.
     - `Equivocation(term, first_quote, first_start, first_end, first_sense, shifted_quote, shifted_start, shifted_end, shifted_sense, explanation)`.
   - The pass's only inputs are the text and a `ModelClient`. It reads no other pass's output, so it can be tested and re-run alone.
3. Docs:
   - `Docs/overview.md`:
     - update the status;
     - say that each pass returns a typed report whose `annotations` use the shared format;
     - list the annotation fields and the JSON form under Output.
   - `Docs/rubrics.md`: add a short section on what term tracking checks, including how equivocation (a shift in what a term means) differs from a part-whole slide (a shift in the scope of a property).
   - `Docs/overview.md` Output also states the offset unit, the newline rule and the text hash, so Burrow can implement against the doc alone.
   - `tests/fixtures/equivocation/README.md`: note four limits of the pair.
     - **The planted move is one step, not two flaws (round 2).** "Per flush" (each device, a rate) becomes "total use" (the utility, a total). That is a scope shift and a sense shift at once, and it is carried by the truncated restatement "efficiency means using less water", which drops "to accomplish the same task". Under the rubric it is an equivocation, the "meaning also changes" case. The planted text also has other integrity flaws: an unsupported "must ... by the same amount", and a final clause that shields the claim from evidence.
     - The pair also differs in difficulty, since the planted text defends a stronger claim.
     - **The control is not clean on integrity (round 2).** `clean.txt` has no equivocation. But "reduce total use only when paired with a cap or a price" claims a cap or price is necessary, on support ("often invites more units") that shows only possibility. That is a modal slip, and it is in tension with its own earlier "whether total use falls depends on whether people flush more...". The README's "its conclusion is scoped accordingly" is corrected.
     - **Force is not controlled (round 3).** `clean.txt` has a concession backed by evidence ("History shows..."), concrete mechanisms ("flush more, build more..."), a self-test ("If total use rises..."), and more length. `planted.txt` drops all of them and adds the framing word "simple". A correct scorer could therefore give the two texts different force. `MAX_FORCE_CHANGE` has to allow for that, and a failure of the force assertion may come from the fixture, not the scorer. Whether to qualify the e2e docstring's "the prose style is similar" is Patrick's call, and it goes in `TODOS.md`.
     - So the e2e test may credit an integrity drop to the planted text as a whole, but not to equivocation alone. It compares integrity and force, never sophistry.
     - A purer pair is logged in `TODOS.md`. Its requirements are a planted edit that changes only the term's sense, a control with no modal slip (a sufficient-condition or possibility claim, such as "they reduce total use when the number of tasks is held fixed"; corrected in the diff review), and (round 3) concessions, examples and length left unchanged, so force really is held fixed. The fixture text is unchanged tonight, because the existing e2e test was written against it.

Out of scope, logged in `TODOS.md`:

- **Wiring the pass into `score_text`.** Term tracking produces annotations, not the three scores, so `score_text` still needs a scoring step that the spec does not yet describe. `tests/test_e2e_metamorphic.py` therefore still fails, as expected.
- **The input-hash result cache.** It is already in `TODOS.md`. **(Round 2)** That entry gains a requirement: the cache key, and any stored report, must record the system prompt (via `client.prompt_key`), the model and the settings, so reports from different prompts are never mixed.
- **Live model calls and recordings.** The first recorded run on the fixtures belongs with the scoring task, using `measure_scores`.

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

`terms` lists the key terms the argument relies on, each with every sense in which the text uses it. `equivocations` lists only the shifts that the argument relies on.

## How the system prompt defines equivocation

The prompt defines an equivocation as one term used in two different senses, where an inference goes through only if the two senses are treated as one. It tells the model not to flag:

- a distinction the author draws openly between two senses or two quantities (`clean.txt` separates efficiency from total use);
- ordinary polysemy that carries no inference;
- figures of speech the reader is meant to read as figures, which are a matter of force, not integrity, **unless an inference later depends on reading the figure literally** (round 2). A shift between figurative and literal sense is an equivocation.

It also says the following:

- **Quotes.** Use verbatim quotes long enough to occur exactly once in the text, and report only shifts where the term itself appears in both quotes, as a whole word spelled exactly as given; leave out shifts carried by an inflected form (wording updated in diff review round 2). This matches the validation rule below, so a reply that follows the prompt cannot fail validation on that point.
- **Part-whole slides (reworded in round 2).** A part-whole slide (composition or division) carries the same property between parts and whole. A pure scope shift of that kind is not an equivocation. When the move also changes the property, as rate per task becoming a total, and a term carries it, the meaning also changes, and it is an equivocation that this pass must report. The prompt uses a generic worked example, not the fixture's own words, so the test is not taught its answer.

`Docs/rubrics.md` gets the same definitions: part-whole slide as composition or division, the rate-to-total case, and the figurative-to-literal condition. The rubric and the prompt then label cases the same way.

## Validation (strict, nothing is silently dropped)

Each equivocation must meet all of these, or the pass raises `PassOutputError`:

- every required field is a non-empty string;
- both quotes anchor uniquely in the text;
- both quotes contain the term, case-insensitively;
- the two quotes are different spans;
- the two senses differ after case and whitespace are normalized.

Each term must have a non-empty `term` and a non-empty list of non-empty sense strings. Both top-level keys must be lists.

Requiring the term in both quotes guards against the model pointing at the wrong sentence. The cost is that an equivocation carried only by a pronoun or a near-synonym cannot be reported. That case is logged in `TODOS.md` for a later pass that can link a near-synonym explicitly.

Raising on malformed output, rather than skipping the bad item, means a bad reply fails loudly instead of quietly lowering the equivocation count. The cost is that one bad reply fails a whole run, which is acceptable for a validation harness.

## Annotations

Each equivocation becomes one annotation, anchored at the shifted use, with `kind="equivocation"` and `source="term_tracking"`. The note names the term, both senses, the first quote and the explanation. Only equivocations become annotations in v0.1. Tracked terms stay in the report, so a later reader view can show them without changing the format.

## Testing plan

`tests/test_term_tracking.py` is written. It fails at import (`No module named 'sophistry_eval.passes'`), which is the expected reason. All of its tests run offline with a canned client:

- Newlines: a text containing `\r` is refused before any model call.
- `anchor_quote`: correct offsets, and rejection of a missing, ambiguous, overlapping-ambiguous or empty quote.
- `parse_json_object`: bare JSON, one fenced block, rejection of two fenced blocks, and rejection of non-objects.
- `Annotation`:
  - rejection of a negative start, `end < start`, an empty source, and a length that does not match the quote;
  - a JSON round trip that pins the key names, the format number and the text hash;
  - code-point offsets with an astral character;
  - refusal to write offsets that miss the text, and refusal to read against a different text;
  - rejection of another format, a missing key, and three wrong types.
- `track_terms`:
  - Prompts: the system prompt and the text are sent; a swapped system prompt is used; the system prompt names equivocation, inference, open distinctions, part-whole slides with the "meaning also changes" case, polysemy, figures with the literal-reading condition, and "exactly once".
  - The planted equivocation in `planted.txt` anchors exactly at the shifted use (`text[start:end] == quote`).
  - The note carries the term, both senses and the first quote.
  - The report keeps both uses, with offsets, and the terms.
  - No equivocations gives no annotations.
  - A fenced reply is accepted.
  - Validation: each rule above has a test, plus a missing field, a case-insensitive term match, and eight malformed payloads.

These test the plumbing only. Whether a model finds the planted equivocation, and leaves `clean.txt` unflagged, is tested by the end-to-end metamorphic test once scoring exists.

**Variance:** no model is called in this task, so there is no variance to report. The e2e test will use `measure_scores` with `DEFAULT_RUNS`, as the existing TODO says.

`tests/test_types.py` will be updated for the new `Annotation` fields.

## Review history

Night 2026-11-21, round 1, both REVISE. Every point was accepted and is folded in above (see the 2026-11-21 plan for the list).

Night 2026-11-23, round 1, both REVISE. Every point was accepted.

- Architect:
  1. state the offset unit (code points);
  2. define the text the offsets index and the newline rule;
  3. put a text hash in the JSON envelope;
  4. record the prompt, model and settings in the cache TODO.
- Logician:
  1. the control has a modal slip, so note it and require a clean control in the purer-pair TODO;
  2. the planted move is one step that is both a sense shift and a scope shift, so reword the part-whole rule so it cannot hide that;
  3. add the figurative-to-literal condition;
  4. make the prompt test check everything its name claims.

Night 2026-11-23, round 2:

- Architect: APPROVE. Two non-blocking notes, both taken:
  - a read-side test for a quote with correct length that points at the wrong span;
  - a decision on unknown keys. `annotations_from_json` rejects them, to match the strict style of the rest of the code. A new field means format 2, and this is stated in `Docs/overview.md`.
- Logician: REVISE, one point. The pair is not matched on force (concession, examples, self-test, length). Accepted as a documentation fix, with a fourth README limit and a purer-pair requirement, marked "round 3" above.

Night 2026-11-23, round 3: Logician APPROVE. One non-blocking note, taken in the README: length is not a source of force in itself; the extra length carries the devices. The plan is approved by both personas.

## Diff review history

Round 1, both REVISE. Every point was accepted.

- Architect:
  1. The format check accepted `true` and `1.0`. It now requires an int, with tests.
  2. The note used Python repr for the senses. Every part is now in plain double quotes, with an apostrophe test.
  3. A stale TODO said the e2e rewrite belongs with term tracking. It now points at the scoring task.
  - Also: the Pipeline wording in `Docs/overview.md` now says each pass returns a typed report, and a blank line that split the Status list is removed.
- Logician:
  1. The prompt's worked example ("a faster worker produces more in total") had a sound conclusion when hours are equal, so it was not an equivocation. It now reads "a plant whose productivity rose is said to have produced more, though it ran fewer hours". The rubric quotes the same example and contrasts it with the sound "same shift" case.
  2. The control wording proposed in TODOS ("unless the number of tasks is held fixed") was itself a necessary-condition claim. It is now a sufficient-condition or possibility claim. This was missed in plan review round 2.
  3. A fifth README limit: the control uses "efficiency" at both the device and the utility level, which is harmless but could be flagged. The purer-pair TODO now requires one level only.
  - Non-blocking notes, all taken:
    - limit 2 now says the planted text is the *harder* case;
    - "History shows..." is now called an appeal to precedent, not evidence;
    - the term check is now a whole-word match (`(?<!\w)term(?!\w)`), with a test that "art" does not match inside "part". A plural such as "efficiencies" therefore does not count as the term, which is the strict choice.

Round 2:

- Architect: APPROVE. One nit, fixed: TODOS said "three conditions" but listed four.
- Logician: REVISE, one point. The whole-word check from round 1 broke the plan's promise that a reply following the prompt cannot fail validation, because the prompt only said "contain the term". The prompt now says "as a whole word, spelled exactly as given", and says to leave out shifts carried by an inflected form. The prompt test asserts "whole word". The rubric and TODOS list inflected forms as a known gap.
  - Non-blocking notes, both taken: "same shift" became "same hours" to avoid a pun, and README limit 4 now names the opening "worth funding, but..." as the concession and "History shows..." as a supporting appeal to precedent.
