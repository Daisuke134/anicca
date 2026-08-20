#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
WORKER="$ROOT/skills/article-writer/scripts/zenn-deferred-worker.sh"
TMP="$(mktemp -d /tmp/zenn-backlog.XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
for run in old newer; do
  mkdir -p "$TMP/runs/$run/gates"
  printf '{"status":"pending","run_id":"%s","handed_off_at":"%s"}\n' "$run" \
    "$([ "$run" = old ] && printf 2000-01-01T00:00:00Z || printf 2001-01-01T00:00:00Z)" \
    >"$TMP/runs/$run/gates/zenn-deferred.json"
done
cat >"$TMP/notify" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$NOTIFY_CALLS"
SH
chmod +x "$TMP/notify"
printf 'not-json\n' >"$TMP/backlog-state.json"
NOTIFY_CALLS="$TMP/notify.calls" bash "$WORKER" --runs-root "$TMP/runs" --ledger "$TMP/ledger" \
  --notify-bin "$TMP/notify" --backlog-state "$TMP/backlog-state.json" \
  --lock-file "$TMP/worker.lock" --publication-lock-dir "$TMP/publication.lockdir" \
  --log "$TMP/worker.log"
rg -q 'backlog count=2 oldest_run=old oldest_age_seconds=[1-9][0-9]+' "$TMP/worker.log"
rg -q 'Zenn retry backlog: count=2 oldest_run=old oldest_age=' "$TMP/notify.calls"
test "$(jq -r .last_action "$TMP/runs/old/gates/zenn-deferred.json")" = quarantined

# Unchanged queue state is advisory-rate-limited.
NOTIFY_CALLS="$TMP/notify.calls" bash "$WORKER" --runs-root "$TMP/runs" --ledger "$TMP/ledger" \
  --notify-bin "$TMP/notify" --backlog-state "$TMP/backlog-state.json" \
  --lock-file "$TMP/worker.lock" --publication-lock-dir "$TMP/publication.lockdir" \
  --log "$TMP/worker.log"
test "$(grep -c 'Zenn retry backlog:' "$TMP/notify.calls")" -eq 1

echo 'PASS: backlog count/age are observable and Telegram advisory is rate-limited'
