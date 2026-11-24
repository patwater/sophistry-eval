# Plan: term-tracking pass (night 2026-11-24, task 1)

Source: `Specs/initial-build.md`, proposed answer 1 (build term tracking first) and answer 7 (annotation format with `start` and `end` offsets). There are no `ready` bugs in `TODOS.md`.

On 2026-11-21, task 2 planned this work (`night/runs/2026-11-21/term-tracking/plan.md`) but stopped after one review round. It did not commit tests or code. This plan starts from that one, keeps the round 1 revisions it accepted, and is reviewed again from scratch.

## Scope

In scope:

1. `Annotation` gains `start` and `end` character offsets into the original text (answer 7), plus a required `source`, the name of the pass that produced it.
   - **Why `source`.** It is an addition to answer 7. Once five passes write into one list, a reader (Burrow, or the e2e test) needs to tell which pass made a note, and two passes could produce the same `kind`. For example, both term tracking and the adversarial verifier can report an equivocation. `source` has no default, so no annotation is ever anonymous.
   - **What an offset counts.** `start` and `end` are Unicode code-point indices (Python string indices) into the exact string that was passed to the pass, with no normalisation of line endings, whitespace or quote marks. A consumer that counts UTF-16 units (JavaScript, so Burrow) or bytes must convert. A test with a non-BMP character pins this.
   - **Field order:** `kind, quote, start, end, note, source`.
   - **Validation.** `__post_init__` rejects an empty `kind` or `source`, `start < 0`, `end < start`, and `end - start != len(quote)`. The last rule catches offsets that drifted from the quote, but it cannot catch offsets that point at a different span of the same length. `text[start:end] == quote` can only be checked against the text, so each pass checks it when it anchors, and the tests assert it.
   - **Serialized form.** `ANNOTATION_FORMAT = 1`. `annotations_to_json(annotations) -> str` writes `{"format": 1, "annotations": [{"kind", "quote", "start", "end", "note", "source"}, ...]}` with fixed key names. `annotations_from_json` reads it back. It rejects any other format, a missing key, an unknown key (at the top level or in an annotation), and a value of the wrong type (`bool` and `float` do not count as `int`).
   - **Why a wrapper object, not a bare list.** This is a second departure from answer 7, which proposed a bare JSON list. The `format` field lets a reader such as Burrow detect a breaking change instead of misreading the data.
   - **Unknown keys are rejected, and any new field bumps `ANNOTATION_FORMAT`.** Strict reading suits a validation harness: a reader never silently drops a field it does not understand. The cost is that a later pass cannot add a field without a version bump, and that is deliberate. Tests pin this rule. A test pins the key names, so this contract sets the format, not Python field names. Both functions live in `types.py` beside `Annotation`.
   - **Existing code.** The only existing construction, in `tests/test_types.py`, is updated to the new fields.
2. A new package `sophistry_eval.passes`:
   - `passes/common.py` holds helpers that every later pass will need:
     - `PassOutputError(ValueError)` is raised when a model reply cannot be used. It is distinct from the client's `UnusableReplyError`, which covers transport-level failures such as truncation and refusal.
     - `parse_json_object(reply)` accepts either bare JSON or text containing exactly one fenced code block. It requires a top-level object.
     - `anchor_quote(text, quote)` returns `(start, end)`. It raises if the quote is empty, missing, or occurs more than once, overlapping occurrences included. An ambiguous quote is rejected rather than guessed, and the prompt tells the model to quote enough words to be unique. Matching is exact, with no whitespace or quote-mark normalisation in v0.1. If live runs show models normalising typography, that becomes a TODO with evidence.
   - `passes/term_tracking.py` holds the pass:
     - `SOURCE = "term_tracking"`, `SYSTEM_PROMPT`. (Planned as `PASS_NAME`. It was renamed during implementation because ruff's S105 reads "PASS" as a password. The new name is also more accurate, and renaming beats suppressing the rule.)
     - `track_terms(text, *, client, system_prompt=SYSTEM_PROMPT) -> TermReport`. The swappable prompt lets prompt variants be tried without editing code. It makes one `client.complete` call.
     - `TermReport` has `terms: tuple[TrackedTerm, ...]`, `equivocations: tuple[Equivocation, ...]` and `annotations: tuple[Annotation, ...]`.
     - `TrackedTerm(term, senses: tuple[str, ...])`.
     - `Equivocation(term, first_quote, first_start, first_end, first_sense, shifted_quote, shifted_start, shifted_end, shifted_sense, explanation)`.
     - All are frozen dataclasses.
     - The pass depends only on the `ModelClient` protocol, `types` and `passes.common`. No model name or essay is hard-coded.
3. Docs:
   - `Docs/overview.md`:
     - update the status;
     - say that each pass returns a typed report whose `annotations` use the shared format;
     - list the annotation fields and the JSON form under Output.
   - `Docs/rubrics.md` gets a short section on what term tracking checks, including how equivocation (a shift in what a term means) differs from a part-whole slide (a shift in the scope of a property).
   - `Docs/rubrics.md` also distinguishes a rate-versus-total slide. When one term carries the shift from per-task to overall, that is an equivocation, because the term's meaning changes. When two terms carry it and the author keeps them apart, as `clean.txt` does with efficiency and total use, there is no flaw. When a total is inferred from a rate without any term shifting, that is a non-sequitur. When two different words are treated as one concept, as with a near-synonym with a different sense, that is an equivocation carried by two words. The rubric states that the v0.1 same-word restriction limits what the pass can detect and is not part of the definition, so the rubric and `Docs/testing-strategy.md` agree.
   - The rubric section also covers figures: a figure later relied on as literal counts as an equivocation.
   - It names the two flaws in "must ... by the same amount" separately. "Must" is a modal slip, because a necessity claim rests on a per-flush cut that only makes a fall possible. "By the same amount" is an unsupported claim about magnitude, which is not modal.
   - "Immunizing move" (treating contrary evidence as error, so the claim cannot be tested) is added to the Named moves list, with a quoted span required as evidence like the other labels.
   - `Docs/testing-strategy.md` Layer 1 gets the same-word-only note (see Out of scope).
   - `tests/fixtures/equivocation/README.md` line 5 and the `tests/test_e2e_metamorphic.py` docstring are reworded. They named the flaw as an equivocation "between efficiency per task and total use", which names two terms. They will locate it correctly: the shifted use restates the definition as "efficiency means using less water", dropping "to accomplish the same task", and the argument then reads that shortened definition as less water overall. So the one term "efficiency" moves from per-task to overall. Neither file is protected.
   - `tests/fixtures/equivocation/README.md` also gets two notes, and the fixture text itself is unchanged, since the existing e2e test was written against it:
     - **The flaw is not pure.** Alongside the term shift, the planted text has a rate-to-total non-sequitur in the same sentence, a modal slip ("must"), an unsupported claim about magnitude ("by the same amount"), and a final immunizing clause that treats contrary evidence as measurement error. The rate-to-total step is not a part-whole slide: carrying a per-task property from devices to a community is valid.
     - **The control is equivocation-free, not flawless.** `clean.txt` draws a necessary condition ("only when paired with a cap or a price") from support that says "often", which is a modal slip, and it offers cap or price as the only remedies, which leans toward a false dilemma. So the e2e integrity gap measures a net difference.
     - **Difficulty differs too.** The planted text defends a stronger claim.
     - So the e2e test may credit an integrity drop to the planted text as a whole, but not to equivocation alone. It compares integrity and force, never sophistry.
     - A purer pair is logged in `TODOS.md`. It covers both texts: a control with no integrity flaws and a planted text whose only flaw is the equivocation.

Out of scope, logged in `TODOS.md`:

- **Wiring the pass into `score_text`.** Term tracking yields annotations, not the three scores, so `score_text` still needs a scoring step that the spec has not yet described. `tests/test_e2e_metamorphic.py` therefore still fails, as expected.
- **The input-hash result cache.** It is already in `TODOS.md`, whose entry says the key must come from `client.prompt_key` plus the model and call settings, so the cache and the recordings cannot use different hashing schemes. That entry will also note that only `annotations` serialize today. `TermReport` has no serialized form, so caching a whole pass's output needs a report serializer or a cache limited to annotations.
- **Live model calls and recordings.** None are made tonight. The pass is plumbing until there is a scorer that the e2e test can gate, and the first recorded run on the fixtures belongs with that task, using `measure_scores`. A live smoke run of `track_terms` on the two fixtures is logged as the next step.
- **Near-synonym equivocations** (see Validation). This conflicts with the documented design and is stated openly. `Docs/testing-strategy.md` Layer 1 and `Specs/initial-build.md` both describe the backbone metamorphic edit as swapping a key term for a near-synonym and say term tracking must flag it. The v0.1 pass can flag only shifts where the same word appears at both uses. Tonight:
  - `Docs/testing-strategy.md` Layer 1 gets a note saying so, and saying that near-synonym edits wait for a pass that links a near-synonym to its term explicitly;
  - the spec conflict is raised in `TODOS.md` for Patrick, since the spec is his.

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

`terms` lists the key terms the argument relies on, each with every sense in which the text uses it. Each term needs at least one sense, and any term named in an equivocation must be listed here (case-insensitively) with at least two senses. Sense strings are not matched between the two lists, because exact matching of free-text senses would be too brittle. `equivocations` lists only shifts the argument relies on. Both lists may be empty.

## The system prompt's definition of equivocation

The prompt defines an equivocation as one term used in two different senses, where an inference only goes through if the two senses are treated as one.

It tells the model not to flag three things:

- a distinction between two senses or two quantities that the author draws and then keeps them apart throughout. Stating a definition or distinction and then sliding across it is still an equivocation, and is the classic sophistic form;
- ordinary polysemy that carries no inference;
- figures of speech the reader is meant to read as figures, which are a matter of force, not integrity, unless the argument later relies on the figure read literally. A metaphor that slides into a literal premise is an equivocation.

It also tells the model that a shift in the scope of a property, from part to whole, is a part-whole slide, not an equivocation, unless the term's meaning also changes. The example comes from another domain ("every brick is light, so the wall is light").

The prompt test checks for the wording "keeps them apart" and "literal", not just "openly".

**The prompt never mentions fixture content.** A prompt tuned to the fixture would make the e2e test show less than it seems to. The first draft's part-whole example (device to community) was the planted text's own move, and it could have steered a model to label the planted flaw as part-whole rather than equivocation. A test checks that fixture words (efficiency, water, toilet, utility, flush, retrofit) are absent from `SYSTEM_PROMPT`.

Finally, it asks for verbatim quotes long enough to occur exactly once in the text, and tells the model to report only shifts where the term itself appears in both quotes. This matches the validation rule below, so a reply that follows the prompt cannot fail validation for that reason.

## Validation (strict, nothing is silently dropped)

Each equivocation must satisfy all of the following, or the pass raises `PassOutputError` naming the failed rule:

- every required field is present and is a non-empty string;
- both quotes anchor uniquely in the text;
- both quotes contain the term as a whole word, case-insensitively, so `use` does not match inside "Because" and `efficiency` does not match inside "inefficiency". A word boundary is "not preceded or followed by a word character", and the term is matched literally (escaped), so terms such as `C++` work;
- the two quotes do not overlap. Two overlapping quotes can share the one occurrence of the term, and that is one use, not the two an equivocation needs;
- the term is listed in `terms` with at least two senses;
- the two senses differ after normalising case and whitespace.

Each term must have a non-empty string `term` and a list of non-empty string `senses` with at least one entry. The top level must have both lists.

- **Why the term must appear in both quotes.** It is a soundness check against the model pointing at the wrong sentence. The cost is that an equivocation carried only by a pronoun or a near-synonym cannot be reported. That gap is logged in `TODOS.md` for a later pass that can link a near-synonym explicitly.
- **Why raise instead of skip.** A bad reply fails loudly instead of quietly lowering the equivocation count. The cost is that one bad reply fails a whole run, which fits a validation harness. The scoring task will decide whether a failed reply is retried or counted as a failed run, and report that rate.

## Annotations

Each equivocation becomes one annotation:

- `kind="equivocation"` and `source="term_tracking"`;
- anchored at the shifted use;
- a note that names the term, both senses, the first quote and the explanation.

Only equivocations become annotations in v0.1. Tracked terms stay in the report, so a later reader view can show them without changing the format.

## Testing plan

`tests/test_term_tracking.py` is written and fails at import (`No module named 'sophistry_eval.passes'`), as expected. It has about 55 test cases once parametrised, all offline, using a canned client:

- **`anchor_quote`:** correct offsets, code-point counting with a non-BMP character, no whitespace normalisation, a missing quote, an ambiguous quote (including overlapping occurrences), an empty quote.
- **`parse_json_object`:** bare JSON, one fenced block, rejection of two fenced blocks, and rejection of non-objects and non-JSON.
- **`Annotation`:**
  - validation of offsets, `kind`, `source`, and quote length against the offsets;
  - the JSON form with pinned key names;
  - a round trip;
  - rejection of another format, a missing key, an unknown key at both levels, and an offset typed as a string, a bool or a float.
- **`track_terms`:**
  - The system prompt and the text are sent, and a variant system prompt is honoured.
  - The system prompt carries the definition and the exclusions (open distinctions, part-whole, figures, exactly once, JSON). This only checks that those instructions are present, not that the model follows them.
  - The system prompt names no fixture content.
  - The planted equivocation anchors at the shifted use in `planted.txt`, with `text[start:end] == quote`, and the note names the term, both senses and the first use.
  - The report keeps both uses with correct offsets, and keeps the terms.
  - A reply with no equivocations (on `clean.txt`) gives no annotations.
  - The term matches regardless of case, and a fenced reply is accepted.
  - Each validation rule fails with a message naming it:
    - a missing quote, an ambiguous quote, and a term absent from a quote;
    - the term present only inside a longer word;
    - an identical span, and a span that contains the other;
    - the same sense after normalisation;
    - an empty explanation, a non-string term, and a missing field;
    - a term absent from `terms`, and a term listed with one sense.
  - A term with regex metacharacters (`C++`) matches literally.
  - One bad item fails the whole reply.
  - Nine malformed payloads are rejected.

These test plumbing only. Whether a model finds the planted equivocation and does not flag `clean.txt` is tested by the end-to-end metamorphic test once scoring exists.

**Variance:** no model is called tonight, so there is no variance to report. The e2e test will use `measure_scores` with `DEFAULT_RUNS`, per the existing TODO.

`tests/test_types.py` is updated for the new `Annotation` fields.

## Review history

### Round 1, both REVISE

- **Architect:**
  1. Define the offset unit and the base string. Accepted: code points into the exact input string, pinned by a non-BMP test and documented.
  2. Justify the wrapper object, and decide how unknown keys are treated. Accepted: they are rejected, any new field bumps the format, and tests pin it.
  3. Restore the cache-key note, and record that `TermReport` has no serializer. Accepted.
- **Logician:**
  1. The part-whole example was the fixture's own move. Accepted: it is replaced with a brick-and-wall example, and a test bans fixture words from the prompt.
  2. Overlapping quotes share one use of the term. Accepted: overlap is rejected and tested.
  3. Substring matching is too weak. Accepted: whole-word, literal matching, with tests.
  4. The two lists can disagree. Accepted: an equivocated term must be listed with at least two senses, and the canned payload is fixed.
  5. The README and the e2e docstring mislocate the flaw. Accepted: both reworded.
  6. The near-synonym conflict with Layer 1 and the spec. Accepted: noted in testing-strategy and raised for Patrick.
  7. Rubric additions (rate-versus-total, modal slip, immunizing move). Accepted.

### Round 2: architect APPROVE, logician REVISE

- **Architect:** approved, with notes for the implementation, all accepted:
  - the Output section of `Docs/overview.md` states the offset unit, the no-normalisation rule, unknown-key rejection and the version-bump rule;
  - the Pipeline section says every pass receives the identical original string;
  - `annotations_from_json -> tuple[Annotation, ...]`;
  - a TODO notes that the first use has no offsets of its own in the annotation, so linking both spans later needs a format bump.
- **Logician:** all accepted.
  1. "Part-whole slide" mislabelled the fixture's rate-to-total non-sequitur. Fixed in the README note.
  2. Split "must" (modal slip) from "by the same amount" (unsupported magnitude).
  3. `clean.txt` is equivocation-free, not flawless. Noted in the README, and the purer-pair TODO covers both texts.
  4. The open-distinction exclusion applies only when the author keeps the senses apart throughout. The prompt and the test use "keeps them apart".
  5. Figures are excluded unless later relied on literally. Added to the prompt, the test and the rubric.
  6. Near-synonym conflation is an equivocation by definition, and same-word is only a detection limit. Added to the rubric. "Immunizing move" is added to Named moves.

### Round 3: both APPROVE

Non-blocking notes, all folded into the implementation:

- **Architect:** the four round 2 items are in scope (overview Output and Pipeline sections, the `annotations_from_json` return type, and the TODO about first-use offsets).
- **Logician:**
  1. The README should not count the rate-to-total step twice. It is the inference the equivocation carries.
  2. The clean-case canned reply should list one sense. Fixed in the test.
  3. The e2e docstring should say the force tolerance also absorbs differences in craft, such as the clean text's concession.
  4. The rubric should say an equivocation that carries an inference is scored once, not again as a non-sequitur.

## Diff review history

### Round 1: architect REVISE, logician APPROVE

- **Architect:** `annotations_from_json` accepted `"format": 1.0`, because `1.0 == 1` in Python. This broke the plan's "float does not count as int" rule. Fixed test-first: the format test is parametrised over `2, 1.0, True, "1", None`, and the check now uses an exact type, like the per-field check. Recorded in `POSTMORTEMS.md`.
- **Logician** (non-blocking notes, all handled):
  1. Loose `match="term"` assertions now match the specific rule ("whole word", "not listed in 'terms'").
  2. Nothing orders the first and shifted uses, so the note now says "elsewhere" instead of "first", and the order question is logged in `TODOS.md`.
  3. The README now gives the right reason the rate-to-total step is not a separate flaw: the scoring rule.
  4. The prompt's grammar is fixed ("distinguishes and then keeps apart throughout"), and the test now pins "keeps apart". The plan's references to "keeps them apart" above describe the round 2 wording.
  5. The README's provenance line is kept as provenance.

### Round 2: both APPROVE

Cosmetic notes applied afterwards, with `make check` rerun clean:

- the "Built so far" list in the overview is one list again;
- the same-sense case matches "are the same", and the non-string term case matches "field 'term'";
- the one-sense message no longer prints a count.
