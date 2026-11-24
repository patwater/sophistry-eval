# TODOS

Unrelated issues the agent notices go here. Bugs marked `ready` are picked up first by the night loop.

## Ready

(none yet)

## Backlog

- Replace the synthetic equivocation fixtures with controlled edits of a public domain essay once `corpus/public_domain/` has one.
- Build the input-hash result cache from `Docs/overview.md`.
  - Its key must come from `client.prompt_key` plus the model and call settings, so it cannot drift from the recording key.
  - A recording is not a cache: it is strict and fails on a miss.
  - Only `annotations` serialize today. `TermReport` has no serialized form, so caching a whole pass's output needs a report serializer or a cache limited to annotations.
- An equivocation annotation carries only the shifted use's offsets. The first use appears only as text in `note`, so Burrow cannot highlight both spans. `TermReport.equivocations` keeps both offsets. Linking two spans in one annotation needs a format bump (`ANNOTATION_FORMAT = 2`).
- Wire term tracking into `score_text` once a scoring step for force, integrity and difficulty is specified. Then run `track_terms` live on both equivocation fixtures, record the replies under `tests/fixtures/recordings/`, and report how often it flags the planted text and stays quiet on the clean one.
- Decide what the scoring task does when a pass raises `PassOutputError`: retry, or count the run as failed. Report the rate either way.
- Build a purer equivocation pair. The control should have no integrity flaws (today's `clean.txt` has a modal slip and leans toward a false dilemma). The planted text's only flaw should be the equivocation (today's adds a modal slip, an unsupported magnitude and an immunizing move), and both texts should defend claims of similar difficulty.
- Near-synonym equivocations: v0.1 term tracking requires the term to appear in both quotes, so it cannot report a shift carried by a near-synonym or a pronoun. A later pass needs to link a near-synonym to its term explicitly.
- Term tracking does not check that `first_quote` comes before `shifted_quote` in the text, since a loose use can come before a definition. The annotation note therefore says "elsewhere" rather than "first". If the order turns out to matter to readers, either check it or rename the fields.
- If live runs show models normalising whitespace or quote marks in their quotes, `anchor_quote` will reject them. Decide then, with evidence, whether to add a normalising fallback.
- The rubric additions and the fixture README (2026-11-24) suggest that the adversarial verifier's prompt should not count an equivocation's inference a second time as a non-sequitur. Carry this into that pass's spec.
- `RecordingClient` re-reads the file before every write, which is safe for several recorders in one process but not for separate processes writing at the same moment. Add a file lock if parallel recording is ever needed.
- Rewrite `tests/test_e2e_metamorphic.py` to use `measure_scores` with `DEFAULT_RUNS` and to gate with both `MIN_INTEGRITY_DROP` and `clears_noise`. This was tied to the term-tracking task, but it needs a scoring step, so it now belongs with the scoring task.
- Turn the token counts in `ClaudeClient.usage` into dollars for `ledger/costs.csv` once the first pass makes live calls.

## NEEDS INPUT FROM PATRICK

- Review the proposed answers to the open questions in `Specs/initial-build.md`. The spec is promoted, so the night loop will use them as written unless he edits them first.
- Pick or swap the twelve Substack and Medium articles in `corpus/urls.csv`. They are a convenience sample from web searches and nobody has read them.
- Trigger the first night by hand with `workflow_dispatch` and read the triage report before trusting the schedule.
- Apply the proposal in `queue/proposals/2026-11-21-claude-md-spec-reference.md` (CLAUDE.md still describes the spec as a draft).
- Should there be a `live` pytest marker for tests that call the real API? `pyproject.toml` registers only `e2e` and is protected. A tiny live smoke test of `ClaudeClient` would confirm the model ids and the key in CI.
- Open question 5's 2σ rule is a heuristic, as written up in `Docs/testing-strategy.md`. With five runs it lets any positive drop through when the clean runs are identical, and it ignores the perturbed text's spread. The fixed 0.15 minimum covers this for now. Do you want a σ floor or a combined standard error instead?
- The spec's first acceptance test, like `Docs/testing-strategy.md` Layer 1, has the term-tracking pass flag a key term swapped for a near-synonym. The v0.1 pass can only flag a shift where the same word appears at both uses (see `Docs/rubrics.md`), so it cannot flag that swap. Should the spec's metamorphic edit become "reuse the same term in a shifted sense" for now, or do you want near-synonym linking sooner?
- Is a scoring step for force, integrity and difficulty the next spec? Term tracking exists but yields annotations, not scores, so `score_text` and the end-to-end test are blocked on it.
- The installed SDK (anthropic 2.12.0) has no temperature parameter, so run-to-run spread is whatever the API gives. If you expected to control sampling for the stability checks, say how.
