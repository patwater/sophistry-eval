#!/usr/bin/env python3
"""Print `session_id,cost_usd,num_turns` from one `claude -p --output-format json` result file.

Field names follow the Claude Code headless docs (session_id, total_cost_usd, num_turns). Missing
numeric fields count as 0. Exits 1 when the file is not valid JSON, so the runner can stop
because the cost of that invocation is unknown.
"""

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write("usage: parse_usage.py RESULT.json\n")
        return 2
    try:
        data = json.loads(Path(sys.argv[1]).read_text())
    except (OSError, json.JSONDecodeError) as error:
        sys.stderr.write(f"cannot parse {sys.argv[1]}: {error}\n")
        return 1
    if not isinstance(data, dict):
        sys.stderr.write("result is not a JSON object\n")
        return 1
    session = str(data.get("session_id") or "unknown")
    cost = float(data.get("total_cost_usd") or 0)
    turns = int(data.get("num_turns") or 0)
    sys.stdout.write(f"{session},{cost:.4f},{turns}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
