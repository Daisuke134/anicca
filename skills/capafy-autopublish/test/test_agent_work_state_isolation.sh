#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUB="$ROOT/vendor/capafy-publisher"
STATE_HOME="$(mktemp -d)"
cleanup(){ rm -rf "$STATE_HOME"; }
trap cleanup EXIT
OPERATOR_HOME_TOKEN='$HOME'
OPENCLAW_PATH_SUFFIX='/.openclaw'

for script in "$ROOT/scripts/publish_prepare.sh" "$ROOT/scripts/publish_finish.sh"; do
  rg -q '^CAPAFY_PUBLISHER_STATE_HOME="\$\{CAPAFY_PUBLISHER_STATE_HOME:-\$LIFE_MANAGER_STATE_HOME/runtime/capafy-publisher\}"$' "$script"
  rg -q '^export CAPAFY_PUBLISHER_STATE_HOME$' "$script"
done
if rg -qF "${OPERATOR_HOME_TOKEN}${OPENCLAW_PATH_SUFFIX}" "$ROOT/scripts/publish_prepare.sh" "$ROOT/scripts/publish_finish.sh"; then
  echo "FAIL: publisher entrypoints read operator OpenClaw state" >&2
  exit 1
fi

for id in 1037238583 7631594519; do
  got="$(cd "$PUB" && LIFE_MANAGER_STATE_HOME="$STATE_HOME" CAPAFY_PUBLISH_WORK_DIR="$STATE_HOME/runtime/capafy-publisher/work/agents/$id" python3 - <<'PY'
from packaging._shared.common.constants import DEVELOPER_WORK_DIR_PATH
print(DEVELOPER_WORK_DIR_PATH)
PY
)"
  [ "$got" = "$STATE_HOME/runtime/capafy-publisher/work/agents/$id" ] || { echo "FAIL $got"; exit 1; }
done

rg -q 'CAPAFY_PUBLISH_WORK_DIR="\$CAPAFY_PUBLISHER_STATE_HOME/work/agents/\$ID"' "$ROOT/scripts/publish_prepare.sh"
rg -q 'BOOTSTRAP_ROOT="\$CAPAFY_PUBLISHER_STATE_HOME/work/bootstrap"' "$ROOT/scripts/publish_prepare.sh"
rg -q 'mkdir -p "\$BOOTSTRAP_ROOT"' "$ROOT/scripts/publish_prepare.sh"
rg -q 'BOOTSTRAP_WORK_DIR="\$\(mktemp -d "\$BOOTSTRAP_ROOT/capafy\.XXXXXX"\)"' "$ROOT/scripts/publish_prepare.sh"
rg -q 'mv "\$BOOTSTRAP_WORK_DIR" "\$AGENT_WORK_DIR"' "$ROOT/scripts/publish_prepare.sh"
rg -q 'export CAPAFY_PUBLISH_WORK_DIR="\$AGENT_WORK_DIR"' "$ROOT/scripts/publish_prepare.sh"
rg -q 'echo "CONFIG_PATH=\$CFG_ONE"' "$ROOT/scripts/publish_prepare.sh"
rg -q 'SHIP_OUT=.*publish-ship.*--agent-id' "$ROOT/scripts/publish_finish.sh"
rg -q 'CAPAFY_PUBLISH_WORK_DIR="\$CAPAFY_PUBLISHER_STATE_HOME/work/agents/\$ID"' "$ROOT/scripts/publish_finish.sh"
rg -q 'CFG_ONE="\$CAPAFY_PUBLISHER_STATE_HOME/cfg_one\.json"' "$ROOT/scripts/publish_prepare.sh"
rg -q 'build_config\.py.*"\$CFG_ONE"' "$ROOT/scripts/publish_prepare.sh"
rg -q 'python3 - "\$CFG_ONE"' "$ROOT/scripts/publish_prepare.sh"
rg -q 'CAPAFY_PUBLISH_WORK_DIR/staging' "$ROOT/scripts/publish_finish.sh"
rg -q 'DSF="\$CAPAFY_PUBLISH_WORK_DIR/dsf\.json"' "$ROOT/scripts/publish_finish.sh"
rg -q -U 'if \[ -e "\$CAPAFY_PUBLISH_WORK_DIR/staging" \]; then\n\s+chmod -R u\+w "\$CAPAFY_PUBLISH_WORK_DIR/staging" 2>/dev/null \|\| true\n\s+rm -rf "\$CAPAFY_PUBLISH_WORK_DIR/staging" 2>/dev/null \\\n\s+\|\| die .*\n\s+fi' "$ROOT/scripts/publish_finish.sh"
rg -q 'chmod -R u\+w "\$WS/skills/\$SKILL_NAME"' "$ROOT/scripts/publish_prepare.sh"
if rg -qF '.temp/cfg_one.json' "$ROOT/CP1_AGENTIC.md"; then
  echo "FAIL: CP1 instructions use a release-local config path" >&2
  exit 1
fi
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
