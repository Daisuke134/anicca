#!/usr/bin/env bash
set -uo pipefail

P=0
F=0
ok(){ echo "  ok $1"; P=$((P+1)); }
fail(){ echo "  FAIL $1"; F=$((F+1)); }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HELPER="$ROOT/earn/capafy-marketing/account_state.sh"
DAILY="$ROOT/earn/capafy-marketing/capafy-ig-marketing-daily.sh"
WARM="$ROOT/earn/capafy-marketing/warm_jitter.sh"
GOAL="$ROOT/earn/capafy-marketing/capafy-goal-monitor.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ ! -f "$HELPER" ]; then
  fail "account state helper exists"
  echo "=== test_capafy_ig_account_state: $P passed $F failed ==="
  exit 1
fi
# shellcheck source=/dev/null
. "$HELPER"

printf '[]\n' > "$TMP/accounts.json"
[ -z "$(resolve_capafy_ig_handle "$TMP/accounts.json")" ] \
  && ok "empty state returns no active account" \
  || fail "empty state must return no active account"

cat > "$TMP/accounts.json" <<'JSON'
[
  {"handle":"old_poisoned","status":"poisoned_manual_backup","session_owner":"browser"},
  {"handle":"older_ready","status":"ready","session_owner":"instagrapi"},
  {"handle":"new_warming","status":"warming","session_owner":"instagrapi"}
]
JSON
[ "$(resolve_capafy_ig_handle "$TMP/accounts.json")" = "new_warming" ] \
  && ok "latest usable ready/warming account wins" \
  || fail "resolver did not return latest usable account"

cat > "$TMP/accounts.json" <<'JSON'
[
  {"handle":"flagged_ready","status":"ready","poisoned_at":"2026-07-19T00:00Z"},
  {"handle":"blocked","status":"blocked"}
]
JSON
[ -z "$(resolve_capafy_ig_handle "$TMP/accounts.json")" ] \
  && ok "poisoned or blocked accounts are rejected" \
  || fail "resolver returned a poisoned or blocked account"

MARKER="$TMP/cooked"
[ "$(capafy_ig_provision_reason "" "$MARKER")" = "no-active-account" ] \
  && ok "empty handle enters PROVISION" \
  || fail "empty handle did not enter PROVISION"
[ -z "$(capafy_ig_provision_reason "fresh_warming" "$MARKER")" ] \
  && ok "usable handle skips PROVISION" \
  || fail "usable handle unexpectedly enters PROVISION"
touch "$MARKER"
[ "$(capafy_ig_provision_reason "fresh_warming" "$MARKER")" = "cooked-marker" ] \
  && ok "cooked marker forces PROVISION" \
  || fail "cooked marker did not force PROVISION"

mkdir -p "$TMP/home-empty" "$TMP/home-active"
printf '[]\n' > "$TMP/empty.json"
EMPTY_PROBE="$(HOME="$TMP/home-empty" CAPAFY_IG_ACCOUNTS_FILE="$TMP/empty.json" CAPAFY_IG_PROBE_ONLY=1 bash "$DAILY")"
[ "$EMPTY_PROBE" = "active_handle=none provision_needed=yes reason=no-active-account" ] \
  && ok "daily dry probe enters PROVISION with empty state" \
  || fail "empty-state dry probe output: $EMPTY_PROBE"
cat > "$TMP/active.json" <<'JSON'
[{"handle":"fresh_warming","profile":"capafy-mkt-fresh","port":9247,"status":"warming","session_owner":"instagrapi"}]
JSON
ACTIVE_PROBE="$(HOME="$TMP/home-active" CAPAFY_IG_ACCOUNTS_FILE="$TMP/active.json" CAPAFY_IG_PROBE_ONLY=1 bash "$DAILY")"
[ "$ACTIVE_PROBE" = "active_handle=fresh_warming provision_needed=no reason=none" ] \
  && ok "daily dry probe resolves active handle" \
  || fail "active-state dry probe output: $ACTIVE_PROBE"
GOAL_PROBE="$(HOME="$TMP/home-active" CAPAFY_IG_ACCOUNTS_FILE="$TMP/active.json" \
  CAPAFY_ACCOUNT_STATE_HELPER="$HELPER" CAPAFY_GOAL_MONITOR_PROBE_ONLY=1 bash "$GOAL")"
[ "$GOAL_PROBE" = "active_handle=fresh_warming active_port=9247 accounts_path=$TMP/active.json" ] \
  && ok "goal monitor resolves handle and port from account state" \
  || fail "goal-monitor state probe output: $GOAL_PROBE"

if ! grep -q 'useclaudeskills' "$DAILY" "$WARM"; then
  ok "daily and warmup scripts contain no baked handle"
else
  fail "daily or warmup script still bakes useclaudeskills"
fi
if grep -Fq 'resolve_capafy_ig_handle "$ACCOUNTS_FILE"' "$GOAL" \
  && grep -Fq -- '--accounts-path "$ACCOUNTS_FILE"' "$GOAL" \
  && ! grep -Fq "sed -nE 's/^IG_HANDLE=" "$GOAL"; then
  ok "goal monitor uses account state instead of parsing daily source"
else
  fail "goal monitor is not fully wired to account state"
fi

for needle in 'PROVISION_NEEDED' 'Client().login' 'get_timeline_feed()' 'dump_settings' 'login_by_sessionid' 'provision-blocked:'; do
  grep -Fq "$needle" "$DAILY" && ok "daily prompt wires $needle" || fail "daily prompt missing $needle"
done

echo "=== test_capafy_ig_account_state: $P passed $F failed ==="
[ "$F" = 0 ]
