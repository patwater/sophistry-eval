#!/usr/bin/env bash
# Posts the morning report: the PR description and a GitHub issue. Needs the gh CLI and GH_TOKEN.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DATE="${1:?usage: report.sh DATE BRANCH BASE}"
BRANCH="${2:?usage: report.sh DATE BRANCH BASE}"
BASE="${3:-main}"
REPORT="night/runs/$DATE/triage.md"
[ -s "$REPORT" ] || { echo "No report at $REPORT" >&2; exit 1; }

PR_NUMBER="$(gh pr list --head "$BRANCH" --json number --jq '.[0].number // empty')"
if [ -z "$PR_NUMBER" ]; then
  gh pr create --base "$BASE" --head "$BRANCH" --title "Night shift $DATE" --body-file "$REPORT"
else
  gh pr edit "$PR_NUMBER" --body-file "$REPORT"
fi

gh issue create --title "Night shift report $DATE" --body-file "$REPORT"
