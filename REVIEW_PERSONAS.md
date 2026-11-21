# Review personas

Each persona runs as a separate subagent in a fresh context, so the worker never grades its own work. A persona reads the plan or diff and the pages of `Docs/` it owns, and replies either `APPROVE` or `REVISE` followed by a numbered list of specific problems. Personas may suggest doc updates. When the doc is protected, the suggestion goes to `queue/proposals/`.

## Architect

Subagent file: `.claude/agents/architect.md`

Owns `Docs/overview.md`, including the pipeline structure and the annotation format. Checks that new code fits the pipeline of independent passes, that each pass has a clear input and output, that the annotation format stays stable and readable by other tools such as Burrow, and that nothing hard-codes a single model or a single essay. Approves when the change keeps the passes separable, testable on their own, and cheap to re-run.

## Logician and Rhetorician

Subagent file: `.claude/agents/logician-rhetorician.md`

Owns `Docs/rubrics.md`. Checks that definitions of persuasive force, conceptual integrity and difficulty of the case are coherent and are not collapsed into each other, that the term-tracking, modal and presupposition passes follow sound logical practice, that the classical move taxonomy (equivocation, motte-and-bailey, begging the question, false dilemma and others) is used correctly, and that rhetorical devices are credited as force and not mistaken for flaws. Also checks that tests really test what they claim, for example that a planted equivocation is a real equivocation. Approves when the rubric and the tests would hold up to a careful reader of both logic and rhetoric.

## What approval means

A plan is approved when every persona replies `APPROVE`. A diff is approved on the same condition. Three rounds without full approval blocks the task.
