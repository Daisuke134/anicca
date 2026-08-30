#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUB="$ROOT/vendor/capafy-publisher"

for id in 1037238583 7631594519; do
  state="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$(mktemp -d)")/state"
  got="$(cd "$PUB" && LIFE_MANAGER_STATE_HOME="$state" CAPAFY_PUBLISH_WORK_DIR="$state/runtime/capafy-publisher/work/agents/$id" python3 - <<'PY'
from packaging._shared.common.constants import DEVELOPER_WORK_DIR_PATH
print(DEVELOPER_WORK_DIR_PATH)
PY
)"
  [ "$got" = "$state/runtime/capafy-publisher/work/agents/$id" ] || { echo "FAIL $got"; exit 1; }
done

rg -q 'CAPAFY_PUBLISH_WORK_DIR=.*agents/\$ID' "$ROOT/scripts/publish_prepare.sh"
rg -q 'SHIP_OUT=.*publish-ship.*--agent-id' "$ROOT/scripts/publish_finish.sh"
rg -q 'CAPAFY_PUBLISH_WORK_DIR=.*agents/\$ID' "$ROOT/scripts/publish_finish.sh"
if rg -qF '$PUB/.temp' "$ROOT/scripts/publish_prepare.sh" "$ROOT/scripts/publish_finish.sh" \
  || rg -q 'open\(.*\.temp' "$ROOT/scripts/publish_prepare.sh" "$ROOT/scripts/publish_finish.sh"; then
  echo "FAIL: publisher entrypoints write mutable files inside the release" >&2
  exit 1
fi
if rg -q 'CAPAFY_PUBLISH_WORK_DIR="\$\{CAPAFY_PUBLISH_WORK_DIR:-' \
  "$ROOT/scripts/publish_prepare.sh" "$ROOT/scripts/publish_finish.sh"; then
  echo "FAIL: publisher resume may inherit another agent's work-state" >&2
  exit 1
fi
echo PASS
