# TODOS

Unrelated issues the agent notices go here. Bugs marked `ready` are picked up first by the night loop.

## Ready

(none yet)

## Backlog

- Replace the synthetic equivocation fixtures with controlled edits of a public domain essay once `corpus/public_domain/` has one.
- Add a recorded-response model client for offline tests.
- Add a repeat-and-average helper in `tests/helpers` for noisy scores.

## NEEDS INPUT FROM PATRICK

- Create the empty GitHub repo `patwater/sophistry-eval` and push this branch. The workspace GitHub token was invalid when the kit was built.
- Add `ANTHROPIC_API_KEY` as a GitHub Actions secret, and set the repository variable `NIGHT_SPEND_CAP_USD` (suggested `10`). The runner refuses to run if the cap is unset.
- Finish `Specs/draft-initial-build.md` and rename it to promote it. See its open questions.
- Trigger the first night by hand with `workflow_dispatch` and read the triage report before trusting the schedule.
