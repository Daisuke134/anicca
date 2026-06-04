#!/usr/bin/env bash
# restart.sh — prove a fresh instance boots clean from a checkpoint (spec 18 §3 RESURRECTION;
# P14 #337 Wave 1 = LOCAL restart proof on the same machine).
#
#   restart.sh <checkpoint_id>
#
# Reads the checkpoint, builds a fresh ~/.hermes-resurrected-<id>/ mockup HERMES_HOME, copies the
# essential state into it, then runs `hermes status` against that home to prove it boots. The
# mockup is always removed on exit. Wave 2 targets a Daytona clean sandbox instead of a local dir.
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$DIR/_lib.sh"

usage() { echo "usage: restart.sh <checkpoint_id>" >&2; exit 64; }
[ "$#" -eq 1 ] || usage
CKID="$1"
CKFILE="$CHECKPOINTS_DIR/$CKID.json"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

[ -f "$CKFILE" ] || { echo "restart: no checkpoint $CKID at $CKFILE" >&2; exit 66; }

RHOME="$HOME/.hermes-resurrected-$CKID"
cleanup() { rm -rf "$RHOME" 2>/dev/null || true; }
trap cleanup EXIT

# Fresh clean home + the essential state the resurrected instance needs to know itself.
mkdir -p "$RHOME/state" "$RHOME/cron"
cp "$CKFILE" "$RHOME/state/checkpoint.json" 2>/dev/null || true
[ -f "$HERMES_LIVE_HOME/cron/jobs.json" ] && cp "$HERMES_LIVE_HOME/cron/jobs.json" "$RHOME/cron/jobs.json" 2>/dev/null || true
[ -f "$HERMES_LIVE_HOME/state/heartbeat.jsonl" ] && cp "$HERMES_LIVE_HOME/state/heartbeat.jsonl" "$RHOME/state/heartbeat.jsonl" 2>/dev/null || true

# PROVE BOOT: hermes status against the fresh home. exit 0 = resurrection OK.
# (HARD RULE #-1: hermes status IS the proof tool; if absent we record the genuine error, not a lie.)
STATUS_EXIT=1
if command -v hermes >/dev/null 2>&1; then
  HERMES_HOME="$RHOME" timeout 60 hermes status >/dev/null 2>&1
  STATUS_EXIT=$?
else
  echo "restart: hermes binary not found — cannot prove boot" >&2
fi

OK=false; [ "$STATUS_EXIT" -eq 0 ] && OK=true

rs_log "$("$JQ" -nc --arg ts "$TS" --arg id "$CKID" --arg rhome "$RHOME" \
  --argjson sx "$STATUS_EXIT" --argjson ok "$OK" \
  '{ts:$ts, op:"restart", checkpoint_id:$id, resurrected_home:$rhome, status_exit:$sx, ok:$ok}')"

echo "restart: $CKID → hermes status exit=$STATUS_EXIT ok=$OK (mockup $RHOME, cleaned)"
[ "$OK" = true ]
