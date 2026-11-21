# sophistry-eval (router)

This file is a short router. It says what the project is and where everything else lives. It should stay under about 150 lines and should not duplicate the files it points to.

## What this project is

sophistry-eval is an AI evaluator that reads a piece of writing and scores it on three axes: persuasive force, conceptual integrity, and difficulty of the case. Sophistry strength is the product of the three, so it rewards writing that makes a hard, sound case land. Sophistry is used here in its craft sense (Protagoras, Gorgias), not as a slur. The idea started as a reply to Venkatesh Rao's post about soft Lean proofs for prose.

The owner is Patrick Atwater. He writes the specs during the day, and agents implement finished specs overnight. A longer description lives in `Docs/overview.md`.

## Current phase

v0.1 is about building a way to test and validate the approach, not about building a polished product. The first goals are a scoring harness, a term-tracking pass, and tests that show whether the scores behave sensibly. See `Specs/draft-initial-build.md` (ignored by the night loop until Patrick promotes it by renaming it).

## Stack

Python 3.12 or newer, managed with `uv`. The Claude API is the model backend. Strict typing with `mypy --strict`, linting and formatting with `ruff`, and tests with `pytest`. The one command that runs all of them is `make check`.

## Where to find things

- `AGENT_LOOP.md` is the night process. Follow it exactly during a night run.
- `REVIEW_PERSONAS.md` describes the reviewers, and `.claude/agents/` holds one subagent per reviewer plus the triage orchestrator.
- `Specs/` holds work. Files starting with `draft-` are ignored. See `Specs/README.md`.
- `Docs/` holds system knowledge. Start with `Docs/overview.md`, then `Docs/rubrics.md` and `Docs/testing-strategy.md`. The night shift setup notes are in `Docs/night-shift.md`.
- `TODOS.md` collects unrelated issues you notice, plus a section of questions for Patrick.
- `POSTMORTEMS.md` records each mistake with its cause and the process fix.
- `CHANGELOG.md` gets an entry for every change.
- `queue/proposals/` is where you put any proposed change to a protected file. `queue/approvals/` is where Patrick approves them.
- `night/runs/<date>/` holds the night's logs, plans and summary. `ledger/costs.csv` records spend.
- `corpus/` holds essays for testing. Only public domain text is committed. Other essays are stored as URLs in `corpus/urls.csv` and cached locally in `corpus/cache/`, which is gitignored.

## Protected paths

Never edit these. If a change to one of them seems necessary, write the proposal to `queue/proposals/` instead.

- `CLAUDE.md`, `AGENT_LOOP.md`, `REVIEW_PERSONAS.md`
- `.claude/agents/`
- `checks/` and `checks/protected_paths.txt`
- `runner/`
- `.github/`
- `Makefile`, `pyproject.toml`
- anything holding secrets (`.env*`, credentials, keys)

The authoritative list is `checks/protected_paths.txt`. A script checks every diff against it.

## Rules of thumb

- Fix the process before the bug. When you make a mistake, first update docs, specs, tests or validations so it cannot recur, then fix the code. Record it in `POSTMORTEMS.md`.
- Strictness helps you. Do not loosen a type check, lint rule or test to get a green result. Fix the cause.
- The worker never grades itself. Reviews run in a fresh context through the persona subagents.
- Do not commit copyrighted essay text. Store URLs and cache locally.
- Prefer small, well-tested changes with a detailed commit message and a CHANGELOG entry.
- Never print, log or commit secrets. The API key arrives as the environment variable `ANTHROPIC_API_KEY`.
