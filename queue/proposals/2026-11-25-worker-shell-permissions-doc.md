# Proposal: document the worker's shell permissions and how to check the API key

Cause label: doc gap. Night 2026-11-25, task 2.

## What happened

Task 2 wanted to do the recorded live run of `track_terms` (a `TODOS.md` backlog item). It first tried to confirm the API key with this compound command:

    [ -n "$ANTHROPIC_API_KEY" ] && echo key-set || echo key-missing; ls ...; cat ...; cat ...

The runner uses `--permission-mode dontAsk` with the allowlist in `runner/night_shift.sh`. That allowlist covers `make`, `uv`, `python3`, `ls`, `mkdir` and some `git` subcommands, but not `[`, `cat` or `echo`, so the whole command was denied. A second compound command, `make check 2>&1 | tail -5; make protected; echo protected-exit=$?`, was denied for the same reason. The worker could not tell whether the key was set, treated that as a missing credential, and switched to an offline task. The switch was sensible, but the live run is still not done, and nothing in `Docs/` would have told the agent that:

- the key is almost certainly present, because the runner needs `ANTHROPIC_API_KEY` to start the worker at all;
- compound shell commands are denied unless every part is on the allowlist;
- there is an allowed way to check for the key without printing it.

A second gap: `Docs/` does not say whether a night task may spend money on live model calls. Those calls go through `ClaudeClient`, not through the worker session, so they are neither recorded in `ledger/costs.csv` nor counted against `NIGHT_SPEND_CAP_USD`.

## Change

`Docs/night-shift.md` is not protected, but the triage agent may not edit docs, so this is a proposal. Add a section after "How a night works":

> ## Worker shell permissions
>
> The worker runs with `--permission-mode dontAsk` and the allowlist in `runner/night_shift.sh`: `make`, `uv`, `python3`, `ls`, `mkdir`, and `git status`, `diff`, `log`, `add`, `commit` and `stash`. Any other command is denied without a prompt. That includes `cat`, `echo`, `test` or `[`, `tail` and `head`, and any compound command (`;`, `&&`, `|`) with a part that is not on the list. Run one allowed command per call and use the Read, Grep and Glob tools to look at files.
>
> To check for the API key without printing it, run:
>
>     uv run python -c "import os; print('set' if os.environ.get('ANTHROPIC_API_KEY') else 'missing')"
>
> The runner cannot start a worker without credentials, so a denied check does not mean the key is missing. Do not treat a permission denial as a missing credential.
>
> ## Live model spend during a task
>
> (Patrick to decide.) Live calls made by project code through `ClaudeClient` are not included in the worker's `total_cost_usd`, so they are not in `ledger/costs.csv` and do not count against the nightly cap. Until `ClaudeClient.usage` is converted into dollars in the ledger, a task may make live calls only if [Patrick's rule, for example: at most N calls or about $X per task, logged in the task's plan and summary].

Also add one line to the working notes in `AGENT_LOOP.md` (protected, so Patrick makes this change):

> - A permission denial is not a missing credential. See "Worker shell permissions" in `Docs/night-shift.md` before you stop or switch tasks over a credential.

## Why this comes before the code fix

Without this, the next night will probably hit the same denial and defer the live run again. That run is the only thing that will show whether the term-tracking prompt works at all.
