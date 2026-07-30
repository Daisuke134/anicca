#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"
JOB_UID="$(id -u)"

for NAME in ai.anicca.job-search-daily ai.anicca.job-search-inbox ai.anicca.job-search-learning; do
  "$JOB_SEARCH_PLUTIL" -lint "$JOB_SEARCH_APP_ROOT/launchd/$NAME.plist" >/dev/null
  "$JOB_SEARCH_PLUTIL" -lint "$JOB_SEARCH_LAUNCH_AGENT_DIR/$NAME.plist" >/dev/null
  STATUS=$("$JOB_SEARCH_LAUNCHCTL" print "gui/$JOB_UID/$NAME" | awk '
    /^[[:space:]]*state =/ {state=$3}
    /^[[:space:]]*last exit code =/ {exit_code=$5}
    END {printf "state=%s last_exit=%s", state, exit_code}
  ')
  if [[ "$STATUS" != *"last_exit=0" ]]; then
    echo "$NAME unhealthy: $STATUS" >&2
    exit 1
  fi
  echo "$NAME $STATUS"
done

"$JOB_SEARCH_PYTHON" - "$JOB_SEARCH_STATE_ROOT" "$JOB_SEARCH_PROFILE" <<'PY'
import json
import sqlite3
import stat
import sys
import time
from pathlib import Path

root = Path(sys.argv[1])
profile = Path(sys.argv[2])
database = root / "ledger.sqlite3"
with sqlite3.connect(database) as connection:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise SystemExit(f"ledger integrity failed: {integrity}")
    counts = dict(
        connection.execute(
            "SELECT current_state, COUNT(*) FROM applications GROUP BY current_state"
        ).fetchall()
    )

prep_database = root / "interview-prep.sqlite3"
with sqlite3.connect(prep_database) as connection:
    prep_integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if prep_integrity != "ok":
        raise SystemExit(f"interview prep integrity failed: {prep_integrity}")
    prep_counts = {
        "registered": connection.execute(
            "SELECT COUNT(*) FROM interview_preps"
        ).fetchone()[0],
        "pending_generation": connection.execute(
            "SELECT COUNT(*) FROM interview_preps WHERE pack_json IS NULL"
        ).fetchone()[0],
        "deliveries": connection.execute(
            "SELECT COUNT(*) FROM prep_deliveries"
        ).fetchone()[0],
    }

private_paths = [root / "inbox-seen.json", prep_database, profile]
for path in private_paths:
    if not path.exists():
        raise SystemExit(f"private state missing: {path}")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise SystemExit(f"private state permissions too broad: {path} {mode:o}")

evidence_root = root / "evidence"
limits = {
    "daily-": 36 * 3600,
    "inbox-": 45 * 60,
    "learning-": 8 * 24 * 3600,
}
freshness = {}
now = time.time()
for prefix, maximum_age in limits.items():
    candidates = [
        candidate
        for candidate in sorted(evidence_root.glob(f"{prefix}*"))
        if (candidate / "summary.json").is_file()
    ]
    if not candidates:
        raise SystemExit(f"missing completed evidence for {prefix}")
    summary = candidates[-1] / "summary.json"
    value = json.loads(summary.read_text(encoding="utf-8"))
    age = now - summary.stat().st_mtime
    if age > maximum_age:
        raise SystemExit(f"stale evidence for {prefix}: {int(age)}s")
    freshness[prefix.rstrip("-")] = {
        "age_seconds": int(age),
        "status": value.get("status"),
    }

print(json.dumps({
    "ledger_integrity": integrity,
    "interview_prep_integrity": prep_integrity,
    "application_counts": counts,
    "interview_prep_counts": prep_counts,
    "freshness": freshness,
}, ensure_ascii=False, sort_keys=True))
PY
