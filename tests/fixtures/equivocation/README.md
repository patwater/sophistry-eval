# Equivocation fixture pair

`clean.txt` keeps one sense of "efficiency" throughout: using less water per task. It keeps that separate from total use. Its conclusion is narrower, but see the limits below.

`planted.txt` defines efficiency the same way in its first paragraph. It then reasons as if efficiency meant using less water overall, and concludes that no cap or price is needed. The planted flaw is an equivocation between efficiency per task and total use. Both texts are original, written for this project.

The Logician and Rhetorician persona should confirm that the planted flaw is a real equivocation and that `clean.txt` has no equivocation. Once a public domain essay is in `corpus/public_domain/`, add a pair made by a controlled edit of a real essay.

## Known limits of this pair

Reviewed on night 2026-11-23. The fixture text is unchanged, because the existing e2e test was written against it. A purer pair is logged in `TODOS.md`.

1. **The planted move is one step, not two flaws.** "Per flush" (each device, a rate) becomes "total use" (the utility, a total). That is a scope shift and a sense shift at once. It is carried by the truncated restatement "efficiency means using less water", which drops "to accomplish the same task". Under `Docs/rubrics.md` it is an equivocation, the case where a part-whole move also changes the property. The planted text also has other integrity flaws: an unsupported "must ... by the same amount", and a final clause ("treat any rise in total use as a measurement error") that shields the claim from evidence.
2. **Difficulty differs.** The planted text defends a stronger claim, and strong objections to it are readily available, so under the rubric it is the *harder* case.
3. **The control is not clean on integrity.** `clean.txt` has no equivocation. But "reduce total use only when paired with a cap or a price" claims that a cap or price is necessary, and its support ("often invites more units") shows only possibility. That is a modal slip. It is also in tension with the text's own earlier sentence, that whether total use falls "depends on whether people flush more, build more, or put the saved water to new uses".
4. **Force is not controlled.** `clean.txt` has an opening concession ("worth funding, but..."), a supporting appeal to precedent ("History shows...", asserted without evidence), concrete mechanisms ("flush more, build more..."), and a self-test ("If total use rises..."). Its extra length is what carries these devices. Length is not a source of force in itself. `planted.txt` drops all of these and adds the framing word "simple". A correct scorer could give the two texts different force, so a failure of the `MAX_FORCE_CHANGE` assertion may come from the fixture rather than the scorer.
5. **The control uses "efficiency" at two levels.** `clean.txt` calls efficiency "a property of a device". It then uses the word at the utility level: "publish total use alongside efficiency each year" and "If total use rises while efficiency improves". This is the same rate moved from one device to the whole fleet, and no inference depends on conflating the two. So it is a scope move or ordinary polysemy, and the control is still free of equivocation. But a model might flag it, and then the e2e assertion that `clean.txt` has no equivocation would fail because of the fixture, not the scorer.

So the e2e test may credit an integrity drop to the planted text as a whole, but not to equivocation alone. It compares integrity and force, never sophistry.
