# Rubrics (v0, to be refined by testing)

Scores run from 0 to 1. These are working definitions that the Logician and Rhetorician persona checks. They will change as testing shows what works.

## Persuasive force

How strongly the prose moves a reader toward its conclusion. Rhetorical craft counts here: rhythm, framing, figures of speech, structure, vivid example, and well-timed concession. High force is not a flaw. A beautifully written weak argument has high force and low integrity.

## Conceptual integrity

How well the piece holds together as reasoning. Reduced by equivocation (a term shifting sense across uses), modal slips (claims of necessity resting on support for possibility only, or "can" turning into "should" without argument), heavy unstated presuppositions, non-sequiturs, and failures that the adversarial verifier cannot repair. Not reduced by plain style, brevity or disagreeable conclusions.

## Difficulty of the case

How hard the position is to defend. Raised by strong available objections, widespread prior skepticism, and dependence on overturning a common assumption. Not raised by obscurity, length or jargon. Difficulty multiplies the product of force and integrity, so a hard case argued with force and integrity scores higher than an easy one.

## Term tracking (what the pass checks)

The term-tracking pass lists the key terms an argument relies on, with every sense in which the text uses each one. It flags an **equivocation** when one term is used in two different senses and an inference goes through only if the two senses are treated as one.

It does not flag:

- A distinction the author draws openly between two senses or two quantities. Keeping them apart is good practice.
- Ordinary polysemy that carries no inference.
- A figure of speech meant to be read as a figure. That is force, not a flaw. The exception is when a later inference depends on reading the figure literally. Then the shift between the figurative and the literal sense is an equivocation.

**Equivocation versus part-whole slide.**

- A part-whole slide (composition or division) carries the *same* property between parts and whole. An example is "each brick is light, so the wall is light". A pure scope shift of that kind is a part-whole slide, not an equivocation.
- When the move also changes the property itself, and a term carries it, the term's meaning also changes, and it is an equivocation. An example is a rate per task becoming a total. The system prompt uses the same example: "productivity" defined as output per hour, then treated as total output, so that a plant whose productivity rose is said to have produced more, though it ran fewer hours. Note that the conclusion must depend on the shift. "A faster worker produces more in the same hours" holds the count fixed and is sound.
- The planted fixture in `tests/fixtures/equivocation/` is this second kind. "Efficiency" per flush becomes total use.

The pass reports an equivocation only when the term itself appears in both quoted uses, as a whole word spelled as given. A shift carried by a pronoun, a near-synonym or an inflected form (plural, adjective) is out of scope for now, even though inflected forms of one word are the same term for equivocation purposes.

## Combination

sophistry strength = force x integrity x difficulty

The alternative of using the minimum of force and integrity, and whether difficulty multiplies or enters separately, are open questions.

## Named moves

The adversarial pass may label moves using standard names: equivocation, motte-and-bailey, begging the question, false dilemma, part-whole slide, and appeal to authority or popularity. Labels need a quoted span from the text as evidence.
