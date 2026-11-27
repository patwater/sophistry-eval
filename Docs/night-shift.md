# Night shift setup

This repo is set up for the night shift workflow described at jamon.dev/night-shift. Patrick works the day shift on specs. Agents implement finished specs overnight. A separate triage agent reads the night's logs before he wakes up and writes the morning report.

## What Patrick still has to do

1. Create the empty GitHub repo `patwater/sophistry-eval` and push the `night-shift-setup` branch. The GitHub token in the workspace that built this kit was invalid, so nothing has been pushed yet.
2. In the repo settings, allow GitHub Actions to create pull requests (Settings, Actions, General, Workflow permissions).
3. Add the secret `ANTHROPIC_API_KEY` under Settings, Secrets and variables, Actions.
4. Set the repository variable `NIGHT_SPEND_CAP_USD`. The suggested value is `10`. The runner refuses to run when it is unset. Optionally set `NIGHT_MAX_TASKS` (default 2).
5. Promote a spec by renaming it from `draft-<name>.md` to `<name>.md`. Nothing runs overnight until a spec is promoted. `Specs/initial-build.md` was promoted on 2026-11-21, with proposed answers to its open questions that Patrick can revise.
6. Trigger the first night by hand (Actions, night-shift, Run workflow) and read the triage report. The workflow has no schedule trigger and runs only when started by hand. To run nightly again, add the `schedule` block described in the comment at the top of `.github/workflows/night-shift.yml`.
7. Review and merge the setup pull request.

## Pausing and resuming

A file named `PAUSE` in the repo root makes the runner exit before doing any work, whether the run was manual or scheduled. `.gitignore` lists `PAUSE`, so a plain `git add` skips it and a pause would never reach CI. Use `git add -f PAUSE` to pause, and `git rm PAUSE` to resume. The pause only takes effect once it is on `main`, because that is the branch the workflow checks out.

## How a night works

`runner/night_shift.sh` does the following.

1. Exits if a `PAUSE` file exists or if `NIGHT_SPEND_CAP_USD` is unset.
2. Takes a lock so two runs never overlap.
3. Works on one branch per night, `night/<date>`, branched from `main`, and reuses it if it exists.
4. Runs each task as its own headless Claude Code invocation, up to `NIGHT_MAX_TASKS` tasks, each limited by `--max-turns` and by the remaining budget through `--max-budget-usd`. Each invocation follows `AGENT_LOOP.md`.
5. Saves each invocation's full JSON output under `night/runs/<date>/`, runs `make check` after each task and saves the result, and records session id, cost and turns in `ledger/costs.csv`. It stops when the nightly cap is reached or when an invocation's usage cannot be read.
6. Runs `checks/check_protected_paths.py` after each task and again before pushing. If a protected path was touched, it refuses to push and exits with status 3.
7. Runs the triage step (`runner/triage.sh`), which invokes the `night-triage` subagent in a fresh context. The runner reverts anything the triage agent writes outside `night/runs/<date>/triage.md` and new files in `queue/proposals/`.
8. Pushes the branch, opens or updates the pull request with `triage.md` as its description, and files a GitHub issue with the same report (`runner/report.sh`).

Full JSON transcripts are gitignored and uploaded as a CI artifact named `night-runs`. Summaries, triage reports, plans and the ledger stay in the repo.

Setting `NIGHT_DRY_RUN=1` skips the push, pull request and issue steps. `NIGHT_CLAUDE_BIN` points the runner at another executable, which is how the stub in `runner/dry_run/` is used for offline tests.

## Reading the morning report

The triage report leads with what needs Patrick's decision, then what shipped, what failed and why with one cause label per failure, and what the night cost. Proposals for fixing the process are written to `queue/proposals/`. Patrick moves a proposal he accepts into `queue/approvals/`, and the change to the protected file is made by him or in a day session. The agent never edits protected files.

## Protected paths

Listed in `checks/protected_paths.txt`: `CLAUDE.md`, `AGENT_LOOP.md`, `REVIEW_PERSONAS.md`, `.claude/agents/`, `checks/`, `runner/`, `.github/`, `Makefile`, `pyproject.toml`, `queue/approvals/`, and files that hold secrets.

## Not built yet

- The automatic single re-run of a task after an environment failure. For now, re-run the workflow by hand.
- The pipeline itself. `pipeline.score_text` raises `NotImplementedError`, and the first night shift builds it from the promoted spec.
- Live-model tests. The recorded-response clients and the repeat-and-average helper exist (see `Docs/testing-strategy.md`), but no test calls a live model yet, and `pyproject.toml` has no `live` marker.

## Sources used for CLI and CI details

These were checked against the current documentation when the kit was built.

- Claude Code run programmatically (headless): https://code.claude.com/docs/en/headless. Used for `claude -p`, `--output-format json`, `--allowedTools`, `--permission-mode`, the `dontAsk` mode, the `session_id` and `total_cost_usd` fields, `ANTHROPIC_API_KEY` for CI, and the exit status behavior.
- Claude Code CLI reference: https://code.claude.com/docs/en/cli-reference. Used for `--max-turns` and `--max-budget-usd` (print mode only), `--allowedTools` and `--disallowedTools`, `--agents`, and `--bare`. The runner does not use `--bare` because it skips CLAUDE.md and subagents, which this workflow needs.
- The npm package name `@anthropic-ai/claude-code` was confirmed to exist in the npm registry.
- The `gh` flags `pr create --base --head --title --body-file`, `pr edit --body-file`, `issue create --title --body-file` and `pr list --head --json --jq` were checked against the installed `gh` help.

## Not verified

- The exact JSON field name for turns. The runner reads `num_turns` and treats a missing value as 0.
- Whether the subagent tool is allowed under `dontAsk` with the current `--allowedTools` list. If personas fail to run in the first real night, add the subagent tool to the list in `runner/night_shift.sh` through a proposal.
- The `actions/checkout@v4`, `actions/setup-node@v4` and `actions/upload-artifact@v4` versions, which were not checked against the marketplace.
- A real `claude` invocation. The dry run used a stub, so the headless flags have not been exercised against the live CLI.
