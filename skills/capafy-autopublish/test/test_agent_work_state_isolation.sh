#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUB="$ROOT/vendor/capafy-publisher"

for id in 1037238583 7631594519; do
  got="$(cd "$PUB" && CAPAFY_PUBLISH_WORK_DIR="$PUB/.temp/agents/$id" python3 - <<'PY'
from packaging._shared.common.constants import DEVELOPER_WORK_DIR_PATH
print(DEVELOPER_WORK_DIR_PATH)
PY
)"
  [ "$got" = "$PUB/.temp/agents/$id" ] || { echo "FAIL $got"; exit 1; }
done

rg -q 'CAPAFY_PUBLISH_WORK_DIR=.*agents/\$ID' "$ROOT/scripts/publish_prepare.sh"
rg -q 'SHIP_OUT="\$(python3 packager.py publish-ship --agent-id "\$ID" 2>&1 || true)"' "$ROOT/scripts/publish_finish.sh"
rg -q 'CAPAFY_PUBLISH_WORK_DIR=.*agents/\$ID' "$ROOT/scripts/publish_finish.sh"
if rg -q 'CAPAFY_PUBLISH_WORK_DIR="\$\{CAPAFY_PUBLISH_WORK_DIR:-' \
  "$ROOT/scripts/publish_prepare.sh" "$ROOT/scripts/publish_finish.sh"; then
  echo "FAIL: publisher resume may inherit another agent's work-state" >&2
  exit 1
fi
echo PASS
