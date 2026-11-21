#!/usr/bin/env bash
# Night shift runner. Runs headless Claude Code on finished specs, then runs the triage step.
#
# Environment:
#   NIGHT_SPEND_CAP_USD   required. The nightly cap for worker tasks. The run refuses to start without it.
#   NIGHT_MAX_TASKS       tasks to attempt (default 2).
#   NIGHT_MAX_TURNS       turn limit per task (default 80).
#   NIGHT_BASE_BRANCH     branch to start from and diff against (default main).
#   NIGHT_DATE            run date, YYYY-MM-DD (default today, UTC).
#   NIGHT_CLAUDE_BIN      claude executable (default claude). Tests point this at a stub.
#   NIGHT_DRY_RUN         set to 1 to skip push, PR and issue steps.
#
# Exit codes: 0 done or paused or lock held, 1 usage or config error, 3 protected path touched.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CLAUDE_BIN="${NIGHT_CLAUDE_BIN:-claude}"
DATE="${NIGHT_DATE:-$(date -u +%F)}"
MAX_TASKS="${NIGHT_MAX_TASKS:-2}"
MAX_TURNS="${NIGHT_MAX_TURNS:-80}"
BASE="${NIGHT_BASE_BRANCH:-main}"
DRY="${NIGHT_DRY_RUN:-0}"
export NIGHT_DATE="$DATE"

# Worker tools. Shell access is limited to the commands the loop needs. Pushing is the runner's job.
ALLOWED="Read,Edit,Write,Glob,Grep,Bash(make *),Bash(uv *),Bash(python3 *),Bash(ls *),Bash(mkdir *),Bash(git status *),Bash(git diff *),Bash(git log *),Bash(git add *),Bash(git commit *),Bash(git stash *)"

# 0. Stop early on PAUSE or a missing spend cap.
if [ -e PAUSE ]; then
  echo "PAUSE file present. Not running."
  exit 0
fi
if [ -z "${NIGHT_SPEND_CAP_USD:-}" ]; then
  echo "NIGHT_SPEND_CAP_USD is not set. Refusing to run." >&2
  exit 1
fi
if ! [[ "$NIGHT_SPEND_CAP_USD" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
  echo "NIGHT_SPEND_CAP_USD must be a number, got '$NIGHT_SPEND_CAP_USD'." >&2
  exit 1
fi

# Lock so two runs never overlap.
exec 9>"$ROOT/.night.lock"
if ! flock -n 9; then
  echo "Another night run holds the lock. Exiting."
  exit 0
fi

# One branch per night. Reuse it if it already exists so tasks stack as commits.
BRANCH="night/$DATE"
if git rev-parse --verify --quiet "$BRANCH" >/dev/null; then
  git checkout -q "$BRANCH"
else
  git checkout -q -B "$BRANCH" "$BASE"
fi

RUN_DIR="night/runs/$DATE"
mkdir -p "$RUN_DIR"
LEDGER="ledger/costs.csv"
[ -e "$LEDGER" ] || echo "date,task,session_id,cost_usd,num_turns" > "$LEDGER"

spent_today() {
  awk -F, -v d="$DATE" 'NR>1 && $1==d && $2 !~ /^triage/ {s+=$4} END {printf "%.4f", s+0}' "$LEDGER"
}

record_cost() { # label, result file
  local line
  if ! line="$(python3 runner/parse_usage.py "$2")"; then
    echo "Could not read usage from $2. Stopping because the cost is unknown." >&2
    return 1
  fi
  echo "$DATE,$1,$line" >> "$LEDGER"
}

PUSH_OK=1
STOP_REASON="task cap reached"

for i in $(seq 1 "$MAX_TASKS"); do
  REMAINING="$(awk -v cap="$NIGHT_SPEND_CAP_USD" -v s="$(spent_today)" 'BEGIN {printf "%.4f", cap - s}')"
  if awk -v r="$REMAINING" 'BEGIN {exit !(r <= 0)}'; then
    STOP_REASON="spend cap reached"
    break
  fi
  [ -e PAUSE ] && { STOP_REASON="PAUSE appeared"; break; }

  PROMPT="Follow AGENT_LOOP.md for exactly one task. This is task $i of $MAX_TASKS tonight. Today is $DATE. Put plans and the summary under $RUN_DIR/. Stop after one task."
  echo "Starting task $i with $REMAINING USD remaining."
  set +e
  "$CLAUDE_BIN" -p "$PROMPT" \
    --output-format json \
    --max-turns "$MAX_TURNS" \
    --max-budget-usd "$REMAINING" \
    --permission-mode dontAsk \
    --allowedTools "$ALLOWED" \
    > "$RUN_DIR/task-$i.json" 2> "$RUN_DIR/task-$i.stderr.log"
  STATUS=$?
  set -e
  echo "Task $i exited with status $STATUS."

  if ! record_cost "task-$i" "$RUN_DIR/task-$i.json"; then
    STOP_REASON="unreadable invocation output"
    break
  fi

  set +e
  make check > "$RUN_DIR/task-$i-check.txt" 2>&1
  echo "make check exit status after task $i: $?" >> "$RUN_DIR/task-$i-check.txt"
  set -e

  if ! python3 checks/check_protected_paths.py --base "$BASE" > "$RUN_DIR/task-$i-protected.txt" 2>&1; then
    echo "Protected paths touched after task $i. Will not push."
    PUSH_OK=0
    STOP_REASON="protected path touched"
    break
  fi
done

echo "Worker loop finished: $STOP_REASON."
echo "$STOP_REASON" > "$RUN_DIR/stop-reason.txt"

# Commit the night's logs and ledger so triage sees a clean tree.
git add "$RUN_DIR" "$LEDGER" 2>/dev/null || true
git commit -q -m "night $DATE: run logs and cost ledger" 2>/dev/null || true

# Triage runs in a fresh context even when the worker stopped early.
bash runner/triage.sh "$DATE" || echo "Triage step reported a problem. See $RUN_DIR."

# Final gate before anything leaves the machine.
if ! python3 checks/check_protected_paths.py --base "$BASE"; then
  PUSH_OK=0
fi

if [ "$PUSH_OK" = "1" ] && [ "$DRY" != "1" ]; then
  git push -u origin "$BRANCH"
  bash runner/report.sh "$DATE" "$BRANCH" "$BASE"
elif [ "$PUSH_OK" = "0" ]; then
  echo "Refusing to push because a protected path was touched." >&2
  exit 3
else
  echo "Dry run: not pushing."
fi
