#!/usr/bin/env bash
# Morning triage. Runs the night-triage subagent in a fresh context, then enforces what it may write.
# It may write only night/runs/<date>/triage.md and new files in queue/proposals/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DATE="${1:?usage: triage.sh YYYY-MM-DD}"
CLAUDE_BIN="${NIGHT_CLAUDE_BIN:-claude}"
TRIAGE_CAP="${NIGHT_TRIAGE_CAP_USD:-1}"
RUN_DIR="night/runs/$DATE"
mkdir -p "$RUN_DIR"

PROMPT="Use the night-triage subagent to triage the night run in $RUN_DIR (date $DATE). Follow its instructions exactly."

set +e
"$CLAUDE_BIN" -p "$PROMPT" \
  --output-format json \
  --max-turns 40 \
  --max-budget-usd "$TRIAGE_CAP" \
  --permission-mode dontAsk \
  --allowedTools "Read,Grep,Glob,Write" \
  > "$RUN_DIR/triage-invocation.json" 2> "$RUN_DIR/triage-invocation.stderr.log"
STATUS=$?
set -e

# Triage spend is recorded in the ledger under a triage label and does not count toward the worker cap.
if line="$(python3 runner/parse_usage.py "$RUN_DIR/triage-invocation.json")"; then
  echo "$DATE,triage,$line" >> ledger/costs.csv
fi

# Enforce the write boundary. Anything else the triage agent changed is reverted.
ALLOWED_RE="^(${RUN_DIR}/triage\.md|queue/proposals/[^/]+\.md)$"
VIOLATED=0
while IFS= read -r entry; do
  [ -z "$entry" ] && continue
  code="${entry:0:2}"
  path="${entry:3}"
  if [[ "$path" =~ $ALLOWED_RE ]]; then
    continue
  fi
  # Ledger and the triage invocation logs are the runner's own writes.
  if [ "$path" = "ledger/costs.csv" ] || [[ "$path" == "$RUN_DIR/triage-invocation"* ]]; then
    continue
  fi
  echo "Triage wrote outside its boundary: $path. Reverting." >&2
  VIOLATED=1
  if [ "$code" = "??" ]; then
    rm -rf -- "$path"
  else
    git checkout -- "$path"
  fi
done < <(git status --porcelain --untracked-files=all)

if [ ! -s "$RUN_DIR/triage.md" ]; then
  cat > "$RUN_DIR/triage.md" <<EOF
# Night shift triage for $DATE

The triage agent did not produce a report (exit status $STATUS). Read \`$RUN_DIR/summary.md\`, \`$RUN_DIR/stop-reason.txt\` and the check outputs in the same folder, and \`ledger/costs.csv\` for the spend.
EOF
fi
if [ "$VIOLATED" = "1" ]; then
  printf '\nNote: the triage agent tried to write outside its boundary and those changes were reverted.\n' >> "$RUN_DIR/triage.md"
fi

git add "$RUN_DIR/triage.md" queue/proposals ledger/costs.csv 2>/dev/null || true
git commit -q -m "night $DATE: triage report and proposals" 2>/dev/null || true
