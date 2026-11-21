#!/usr/bin/env bash
# A stand-in for `claude -p` used only to dry-run the runner offline. It prints JSON in the shape the
# runner expects and makes small, predictable edits. It does not call any model.
#
# STUB_SLEEP=N           sleep N seconds first, to test the lock.
# STUB_TOUCH_PROTECTED=1 edit CLAUDE.md, to test the protected-paths gate.
# STUB_TRIAGE_ESCAPE=1   make the triage stub edit a file outside its boundary.
set -euo pipefail

PROMPT=""
while [ $# -gt 0 ]; do
  case "$1" in
    -p) PROMPT="$2"; shift 2 ;;
    *) shift ;;
  esac
done

DATE="${NIGHT_DATE:?}"
RUN_DIR="night/runs/$DATE"
mkdir -p "$RUN_DIR" queue/proposals
[ -n "${STUB_SLEEP:-}" ] && sleep "$STUB_SLEEP"

if [[ "$PROMPT" == *night-triage* ]]; then
  cat > "$RUN_DIR/triage.md" <<EOF
# Night shift triage for $DATE (stub)

## Needs your decision
1. Nothing. This is a dry run with a stub agent.

## What shipped
A no-op task.
EOF
  echo "stub proposal" > "queue/proposals/$DATE-stub.md"
  [ "${STUB_TRIAGE_ESCAPE:-0}" = "1" ] && echo "escaped" >> Docs/overview.md
  echo '{"session_id":"stub-triage","total_cost_usd":0.05,"num_turns":2,"result":"ok"}'
  exit 0
fi

mkdir -p "$RUN_DIR/noop"
echo "stub plan" > "$RUN_DIR/noop/plan.md"
echo "no-op task done" >> "$RUN_DIR/summary.md"
[ "${STUB_TOUCH_PROTECTED:-0}" = "1" ] && echo "tampered" >> CLAUDE.md
git add -A "$RUN_DIR" CLAUDE.md 2>/dev/null || true
git commit -q -m "stub task" 2>/dev/null || true
echo '{"session_id":"stub-task","total_cost_usd":4.00,"num_turns":3,"result":"ok"}'
