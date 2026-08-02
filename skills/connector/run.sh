#!/usr/bin/env bash
# Canonical bounded Connector pass. This script owns only local lifecycle state;
# the worker owns no global schedule or completion claim.
set -eu
umask 077

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$HERE/../.." && pwd -P)"
[ -f "$REPO_ROOT/apps/life-manager/lib/connector-events-pack.js" ] || {
  printf 'Connector native repository unavailable\n' >&2
  exit 2
}

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
# shellcheck source=/dev/null
source "$REPO_ROOT/apps/life-manager/scripts/lib/load-env-file.sh"
LM_CONNECTOR_ENV_FILE="${LM_CONNECTOR_ENV_FILE:-$HOME/.local/state/life-manager/.env}"
lm_load_env_file "$LM_CONNECTOR_ENV_FILE" || exit 2

STATE_DIR="${LM_CONNECTOR_STATE_DIR:-$HOME/.local/state/life-manager/connector-native}"
case "$STATE_DIR" in
  /*) ;;
  *) printf 'Connector native state directory unavailable\n' >&2; exit 2 ;;
esac
NODE_BIN="${NODE_BIN:-$(command -v node || true)}"
[ -n "$NODE_BIN" ] && [ -x "$NODE_BIN" ] || {
  printf 'Connector native node unavailable\n' >&2
  exit 2
}
LOCK_STALE_MS="${LM_CONNECTOR_LOCK_STALE_MS:-900000}"
OWNER_TOKEN="$($NODE_BIN -e 'process.stdout.write(require("node:crypto").randomBytes(32).toString("hex"))')"

release_lock() {
  "$NODE_BIN" "$HERE/lib/native-state.js" release "$STATE_DIR" "$OWNER_TOKEN" >/dev/null 2>&1 || true
}

LOCK_RESULT="$($NODE_BIN "$HERE/lib/native-state.js" acquire "$STATE_DIR" "$OWNER_TOKEN" "$$" "$LOCK_STALE_MS")" || {
  printf 'Connector native lock unavailable\n' >&2
  exit 2
}
case "$LOCK_RESULT" in
  '{"status":"acquired"}') ;;
  '{"status":"busy"}') exit 75 ;;
  *) printf 'Connector native lock unavailable\n' >&2; exit 2 ;;
esac
trap release_lock EXIT

"$NODE_BIN" "$HERE/lib/native-state.js" heartbeat "$STATE_DIR" "$OWNER_TOKEN" native_started >/dev/null || exit 2
if "$NODE_BIN" "$HERE/native-pass.js" \
  --repo-root "$REPO_ROOT" \
  --state-dir "$STATE_DIR" \
  --owner-token "$OWNER_TOKEN"; then
  "$NODE_BIN" "$HERE/lib/native-state.js" heartbeat "$STATE_DIR" "$OWNER_TOKEN" worker_finished >/dev/null || exit 2
  exit 0
else
  EXIT_CODE=$?
  "$NODE_BIN" "$HERE/lib/native-state.js" heartbeat "$STATE_DIR" "$OWNER_TOKEN" worker_failed >/dev/null 2>&1 || true
  exit "$EXIT_CODE"
fi
