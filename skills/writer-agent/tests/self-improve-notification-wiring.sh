#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/self-improve-notify.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
SKILL="$TMP/skill"
mkdir -p "$SKILL/scripts" "$SKILL/state/learning/receipts" "$TMP/home/.openclaw/logs"
: >"$TMP/home/.openclaw/.env"

for helper in score-latest-run.sh topic-supply.sh; do
  printf '#!/usr/bin/env bash\nexit 0\n' >"$SKILL/scripts/$helper"
  chmod +x "$SKILL/scripts/$helper"
done

cat >"$SKILL/scripts/self_improve_control.py" <<'PY'
import json
import sys
from pathlib import Path

skill = Path(sys.argv[sys.argv.index("--skill-dir") + 1])
receipt = {
    "schema_version": 1,
    "observed_at": "2026-07-28T22:30:00+09:00",
    "status": "APPLIED",
    "new_metrics": 1,
    "metric_run_ids": ["daily-2026-07-27"],
    "experiment_id": "learning-2026-07-28",
    "source_commits": [],
}
path = skill / "state/learning/receipts/2026-07-28.json"
path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
print(json.dumps(receipt))
PY

cat >"$SKILL/scripts/self-improve-notify.py" <<'PY'
import json
import os
import sys
from pathlib import Path

receipt = Path(sys.argv[sys.argv.index("--receipt") + 1])
Path(os.environ["NOTIFY_MARKER"]).write_text(
    str(receipt) + "\n",
    encoding="utf-8",
)
print(json.dumps({"status": "sent", "message_id": "fixture-42"}))
PY

if ! NOTIFY_MARKER="$TMP/notified" \
  HOME="$TMP/home" \
  ARTICLE_SKILL_DIR="$SKILL" \
  bash "$ROOT/scripts/self-improve.sh" >"$TMP/stdout" 2>"$TMP/stderr"; then
  cat "$TMP/stdout" >&2
  cat "$TMP/stderr" >&2
  exit 1
fi

if [[ ! -f "$TMP/notified" ]]; then
  cat "$TMP/stdout" >&2
  cat "$TMP/stderr" >&2
  echo "notification marker missing" >&2
  exit 1
fi
ACTUAL_RECEIPT="$(realpath "$(cat "$TMP/notified")")"
EXPECTED_RECEIPT="$(realpath "$SKILL/state/learning/receipts/2026-07-28.json")"
if [[ "$ACTUAL_RECEIPT" != "$EXPECTED_RECEIPT" ]]; then
  printf 'receipt mismatch actual=%s expected=%s\n' \
    "$ACTUAL_RECEIPT" "$EXPECTED_RECEIPT" >&2
  exit 1
fi
if ! grep -q '"message_id": "fixture-42"' "$TMP/stdout"; then
  cat "$TMP/stdout" >&2
  echo "notification receipt missing from stdout" >&2
  exit 1
fi
echo "PASS: 22:30 wrapper durably notifies the controller receipt"
