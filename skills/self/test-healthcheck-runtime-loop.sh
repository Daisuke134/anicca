#!/usr/bin/env bash
# test-healthcheck-runtime-loop.sh — proves the #7 H4 runtime/loop healthcheck classifies every
# real state correctly, BEFORE it ever acts. Mirrors test-healthcheck-lib.sh's pattern: source the
# REAL script and call its pure predicate (hrl_classify) directly, so this cannot drift from the
# actual logic and never spawns a real kickstart/self-fix for a synthetic case.
set -uo pipefail; P=0; F=0
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

chk() {
  local name="$1" want="$2" pid="$3" kind="$4" age="$5" stale_min="$6"
  local got; got="$(bash "$HERE/healthcheck-runtime-loop.sh" --classify "$pid" "$kind" "$age" "$stale_min")"
  [ "$got" = "$want" ] && { echo "  ok $name ($got)"; P=$((P+1)); } || { echo "  FAIL $name want=$want got=$got"; F=$((F+1)); }
}

# job vanished from launchctl entirely (unloaded / plist broken) -> DEAD_UNLOADED, either kind
chk "unloaded keepalive job" DEAD_UNLOADED "" keepalive 0 20
chk "unloaded interval job" DEAD_UNLOADED "" interval 0 90

# KeepAlive job present but no PID -> DEAD_NO_PID
chk "keepalive with no pid" DEAD_NO_PID "-" keepalive 3 20

# StartInterval job with no PID between runs -> NORMAL (not dead) -> falls through to freshness check
chk "interval with no pid, fresh artifact" OK "-" interval 5 90
chk "interval with no pid, stale artifact" STALE "-" interval 200 90

# job alive, artifact file doesn't exist yet -> MISSING_ARTIFACT (age -1 is the sentinel)
chk "artifact missing" MISSING_ARTIFACT 12345 keepalive -1 20

# job alive (real PID), artifact fresh -> OK
chk "keepalive alive + fresh" OK 12345 keepalive 1 20
chk "interval alive + fresh" OK 6789 interval 4 90

# job alive, artifact older than the limit -> STALE -> would escalate to self-fix
chk "keepalive alive + stale" STALE 12345 keepalive 25 20
chk "interval alive + stale" STALE 6789 interval 95 90

# boundary: age exactly == stale_min counts as STALE (>=), age one below does not
chk "boundary: age == limit is STALE" STALE 1 keepalive 20 20
chk "boundary: age == limit-1 is OK" OK 1 keepalive 19 20

echo "=== healthcheck-runtime-loop classify: $P passed $F failed ==="; [ "$F" = 0 ] && echo GREEN || exit 1
