# TODOS

Unrelated issues the agent notices go here. Bugs marked `ready` are picked up first by the night loop.

## Ready

(none yet)

## Backlog

- Replace the synthetic equivocation fixtures with controlled edits of a public domain essay once `corpus/public_domain/` has one. The new pair must meet four conditions, from the limits in `tests/fixtures/equivocation/README.md`:
  1. The planted edit changes only the term's sense, with no extra modal or evidence-shielding flaws.
  2. The control has no modal slip. It should make a sufficient-condition or possibility claim instead of the current necessary-condition claim ("only when paired with a cap"), for example "they reduce total use when the number of tasks is held fixed" or "they may not reduce total use if the number of tasks grows".
  3. Concessions, examples and length stay unchanged, so force really is held fixed.
  4. The control uses the term at only one level (device or utility, not both), so a model has no innocent scope move to flag.
- Build the input-hash result cache from `Docs/overview.md`.
  - Its key must come from `client.prompt_key` (which covers the system prompt and the prompt) plus the model and call settings, so it cannot drift from the recording key.
  - Any stored report must also record the system-prompt hash, the model and the settings, so reports from different prompts (`track_terms(..., system_prompt=...)`) are never mixed.
  - A recording is not a cache: it is strict and fails on a miss.
- Add a scoring step that turns pass reports into force, integrity and difficulty, then wire term tracking into `pipeline.score_text`. The spec does not yet say how annotations become scores. This unblocks `tests/test_e2e_metamorphic.py`.
- Term tracking cannot report an equivocation carried only by a pronoun, a near-synonym or an inflected form ("efficiencies", "efficient"), because each quote must contain the term as a whole word. Inflected forms are really the same term, so this is a known gap. A later change could let the model name the surface form it quotes, and link near-synonyms explicitly.
- `RecordingClient` re-reads the file before every write, which is safe for several recorders in one process but not for separate processes writing at the same moment. Add a file lock if parallel recording is ever needed.
- Rewrite `tests/test_e2e_metamorphic.py` to use `measure_scores` with `DEFAULT_RUNS` and to gate with both `MIN_INTEGRITY_DROP` and `clears_noise`. This belongs with the scoring-step task above, together with the first recorded run on the fixtures.
- Turn the token counts in `ClaudeClient.usage` into dollars for `ledger/costs.csv` once the first pass makes live calls.

## NEEDS INPUT FROM PATRICK

- Review the proposed answers to the open questions in `Specs/initial-build.md`. The spec is promoted, so the night loop will use them as written unless he edits them first.
- Pick or swap the twelve Substack and Medium articles in `corpus/urls.csv`. They are a convenience sample from web searches and nobody has read them.
- Trigger the first night by hand with `workflow_dispatch` and read the triage report before trusting the schedule.
- Apply the proposal in `queue/proposals/2026-11-21-claude-md-spec-reference.md` (CLAUDE.md still describes the spec as a draft).
- Should there be a `live` pytest marker for tests that call the real API? `pyproject.toml` registers only `e2e` and is protected. A tiny live smoke test of `ClaudeClient` would confirm the model ids and the key in CI.
- Open question 5's 2σ rule is a heuristic, as written up in `Docs/testing-strategy.md`. With five runs it lets any positive drop through when the clean runs are identical, and it ignores the perturbed text's spread. The fixed 0.15 minimum covers this for now. Do you want a σ floor or a combined standard error instead?
- The e2e test's docstring says the fixture pair's "prose style is similar", but the two texts differ in concession, concrete examples and self-test, so force is not controlled (see limit 4 in `tests/fixtures/equivocation/README.md`). Should the docstring be qualified, `MAX_FORCE_CHANGE` loosened, or the fixtures replaced first?
- Wording, from the logician's final review: the term-tracking prompt, `Docs/rubrics.md` and the inflected-form TODO call an adjective ("efficient") an inflected form, but it is a derived word. The suggestion is "an inflected or derived form (a plural, or a related word such as an adjective)", with the rubric's "same term" sentence limited to inflections. Behaviour is the same either way. Changing the prompt invalidates any recordings, so it was left as approved.
- How should the term-tracking annotations feed the integrity score? For example: a fixed penalty per equivocation, a model-rated severity, or a separate integrity rating that sees the annotations. The spec is silent, and this blocks wiring `score_text`.
- The installed SDK (anthropic 2.12.0) has no temperature parameter, so run-to-run spread is whatever the API gives. If you expected to control sampling for the stability checks, say how.
