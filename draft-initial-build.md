# Draft: v0.1 build of the sophistry strength evaluator

This is a draft built from Patrick's words in the conversation that started the project. It records what he said and lists what he still has to decide. It is not a finished spec, and the night loop ignores it until he renames it to `initial-build.md`.

## Goal

In Patrick's words, the starting point was a reply to Venkatesh Rao's blyg post wondering about soft Lean proofs for prose, "to signal a certain level of coherence and conceptual integrity":

> Something like modal logic? You know it wouldnt be that hard to have an ai verifier go through and check for coherence, going beyond logic. On a secant, I'd propose a sophistry based approach and will add this to my list of fafo AI experiments.

The idea is "a sophistry strength evaluator that looks at the conceptual and semantic integrity of a piece of writing." Sophistry is meant in the craft sense. In Patrick's words: "something with high force and high integrity should get high sophistry approach because I think that the negative connotation was so frustrated part of the 2000 year propaganda campaign of the platonists."

He later asked to include the third axis, difficulty of the case, as part of the score. Sophistry strength is force times integrity times difficulty, with difficulty acting as a multiplier that rewards holding a hard case.

For v0.1 he said: "I am thinking that I need to test and validate to improve the approach." So v0.1 is about building a way to test the approach, with a new repo for that testing.

## Users

Patrick first, as an experimenter. Later, readers of blygs in the Burrow reader, where margin annotations could show inline while reading.

## Behavior (from the conversation, to be confirmed)

The pipeline has five passes, each producing annotations and not just a verdict:

1. Claim extraction into a graph of claims, premises and inferential links, with each link tagged as deductive, inductive, analogical or merely rhetorical.
2. Term tracking, which follows each key term across the piece and flags equivocation.
3. Modal audit, which checks necessity claims supported only by possibility, and "can" sliding into "should".
4. Presupposition load, which counts what the argument smuggles in as given.
5. Adversarial verifier, where a prosecutor tries to break each link and a defender repairs it. Repairs count as evidence of robustness. This pass can also name classical moves such as motte-and-bailey, begging the question and false dilemma.

The output is a margin-annotated version of the text plus the scores for force, integrity, difficulty and sophistry strength.

## Acceptance tests (from the conversation, to be confirmed)

Real essays have no known right answer, so Patrick agreed to a layered approach:

1. Metamorphic tests on real essays. Make controlled edits to a real essay (swap a key term for a near-synonym with a different sense partway through, delete a premise, turn a "may" into a "must"). Integrity must drop in the right pass, and force must stay roughly flat.
2. Rank-order checks on a corpus of famous real essays plus random essays from Substack and the public internet, compared with Patrick's hand ratings of roughly 20 pieces for force, integrity and difficulty.
3. Stability checks. Run each essay several times and measure score variance, and check that scores do not swing with essay length or paragraph order.

Public domain essays are committed. Other essays are stored as URLs and cached locally. Candidate calibration pieces mentioned: Gorgias's Encomium of Helen, Swift's A Modest Proposal, Federalist 10, and Orwell's essay on politics and the English language.

## Out of scope for v0.1 (proposed, Patrick to confirm)

The Burrow integration itself, any web service, and a polished user interface.

## Open questions for Patrick

1. Which pass should the first night shift build? The suggestion from the conversation was term tracking, because it is the most tractable and the most revealing.
2. Should the final score be a product or a minimum of force and integrity, and should difficulty multiply that result or enter separately?
3. How should difficulty of the case be measured, and who sets the baseline for what counts as a common assumption?
4. Which model or models should the first runs use, and is it acceptable to compare two for stability?
5. What is the tolerance for the metamorphic test, meaning how far must integrity drop for a planted flaw to count as detected?
6. Which 20 or so essays form the hand-rated set, and when can Patrick rate them?
7. What annotation format should the output use so that Burrow can read it later?
8. Should force be scored by a model alone, or should it include measurable features such as rhetorical device counts?
