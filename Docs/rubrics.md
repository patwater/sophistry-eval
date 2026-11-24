# Rubrics (v0, to be refined by testing)

Scores run from 0 to 1. These are working definitions that the Logician and Rhetorician persona checks. They will change as testing shows what works.

## Persuasive force

How strongly the prose moves a reader toward its conclusion. Rhetorical craft counts here: rhythm, framing, figures of speech, structure, vivid example, and well-timed concession. High force is not a flaw. A beautifully written weak argument has high force and low integrity.

## Conceptual integrity

How well the piece holds together as reasoning. Reduced by equivocation (a term shifting sense across uses), modal slips (claims of necessity resting on support for possibility only, or "can" turning into "should" without argument), heavy unstated presuppositions, non-sequiturs, and failures that the adversarial verifier cannot repair. Not reduced by plain style, brevity or disagreeable conclusions.

## Difficulty of the case

How hard the position is to defend. Raised by strong available objections, widespread prior skepticism, and dependence on overturning a common assumption. Not raised by obscurity, length or jargon. Difficulty multiplies the product of force and integrity, so a hard case argued with force and integrity scores higher than an easy one.

## Combination

sophistry strength = force x integrity x difficulty

The alternative of using the minimum of force and integrity, and whether difficulty multiplies or enters separately, are open questions.

## Term tracking: what counts as equivocation

An equivocation is one term used in two different senses, where an inference only goes through if the senses are treated as one. It lowers integrity.

These are equivocations:

- **A stated definition the argument slides across.** The author states a definition or distinction and then slides across it. This is the classic sophistic form, and stating the distinction openly does not excuse it.
- **A figure read literally.** A figure of speech is a matter of force, but the argument later relies on it as a literal premise.
- **A near-synonym conflation.** Two different words are treated as one concept when their senses differ. This is an equivocation carried by two words.

These are not equivocations:

- **A distinction kept apart.** The author draws a distinction between two senses or quantities and keeps them apart throughout.
- **Polysemy that carries no inference.**
- **A figure meant as a figure.** This is credited as force.
- **A part-whole slide.** This shifts the scope of a property, not the meaning of a term ("every brick is light, so the wall is light"). It is a separate flaw unless the term's meaning also changes.

Rate against total is a common case. A per-unit quantity such as water per task differs from a total such as water used overall:

- When one term carries the shift from rate to total, it is an equivocation, because the term's meaning changes.
- When two terms carry the two quantities and the author keeps them apart, there is no flaw.
- When a total is inferred from a rate and no term shifts, it is a non-sequitur.

When an equivocation carries an inference, the flaw is scored once, as the equivocation. It is not counted again as a non-sequitur.

v0.1's pass reports only shifts where the same word appears at both uses, because it checks that the term occurs in both quotes. That is a limit on what the pass can detect, not part of the definition. Near-synonym conflations wait for a pass that links a near-synonym to its term explicitly.

Other flaws that often travel with an equivocation are kept separate:

- A modal slip, where "must" rests on support that only makes something possible.
- An unsupported claim about magnitude, such as "by the same amount". This is not modal.
- An immunizing move (see Named moves).

## Named moves

The adversarial pass may label moves using standard names:

- equivocation;
- motte-and-bailey;
- begging the question;
- false dilemma;
- part-whole slide;
- appeal to authority or popularity;
- immunizing move, which treats contrary evidence as error so that the claim cannot be tested.

Labels need a quoted span from the text as evidence.
