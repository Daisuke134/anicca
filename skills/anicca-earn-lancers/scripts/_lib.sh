#!/usr/bin/env bash
# Shared helpers for anicca-earn-lancers.
# Loads ~/.openclaw/.env (NEVER echo values), wraps Camofox :9377 REST,
# provides redacted logging + optional Slack post.
# Source this file: `source "$(dirname "$0")/_lib.sh"`.

set -uo pipefail

# Load env (= the ONE place secrets enter the process)
if [ -f "$HOME/.openclaw/.env" ]; then
  set -a; . "$HOME/.openclaw/.env"; set +a
fi

CAMOFOX="${CAMOFOX_URL:-http://localhost:9377}"
USER_ID="${ANICCA_USER_ID:-anicca}"
SESSION_KEY="${ANICCA_SESSION_KEY:-default}"
JQ="${JQ:-/usr/bin/jq}"
PYTHON="${PYTHON:-python3}"

# ─── logging (stderr, never stdout — stdout is the JSON contract) ──────────
log()  { echo "▶ [earn-lancers] $*" >&2; }
ok()   { echo "✅ [earn-lancers] $*" >&2; }
err()  { echo "❌ [earn-lancers] $*" >&2; }

# ─── camofox health ────────────────────────────────────────────────────────
cf_health() {
  curl -sS --max-time 5 "$CAMOFOX/health" \
    | "$JQ" -e '.ok == true and .browserConnected == true' >/dev/null
}

# ─── open new tab, return tabId on stdout ─────────────────────────────────
cf_open() {
  local url="$1"
  curl -sS -X POST "$CAMOFOX/tabs" \
    -H 'Content-Type: application/json' \
    -d "$("$JQ" -n --arg u "$url" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
            '{url:$u, userId:$uid, sessionKey:$sk}')" \
    | "$JQ" -r '.tabId // empty'
}

# ─── navigate existing tab ─────────────────────────────────────────────────
cf_navigate() {
  local tab="$1" url="$2"
  curl -sS -X POST "$CAMOFOX/tabs/$tab/navigate" \
    -H 'Content-Type: application/json' \
    -d "$("$JQ" -n --arg u "$url" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
            '{url:$u, userId:$uid, sessionKey:$sk}')" >/dev/null
}

# ─── snapshot (returns raw JSON on stdout) ─────────────────────────────────
cf_snapshot() {
  local tab="$1"
  curl -sS "$CAMOFOX/tabs/$tab/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY"
}

# ─── snapshot accessibility text (robust: camofox JSON has unescaped control ─
# chars that break jq, so parse with python json.loads(strict=False)) ────────
cf_snapshot_text() {
  local tab="$1"
  curl -sS "$CAMOFOX/tabs/$tab/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY" \
    | "$PYTHON" -c '
import sys,json
raw=sys.stdin.read()
try:
    print(json.loads(raw, strict=False).get("snapshot",""))
except Exception:
    print(raw)
'
}

# ─── current tab URL (same robust parse) ───────────────────────────────────
cf_url() {
  local tab="$1"
  curl -sS "$CAMOFOX/tabs/$tab/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY" \
    | "$PYTHON" -c '
import sys,json
raw=sys.stdin.read()
try:
    print(json.loads(raw, strict=False).get("url",""))
except Exception:
    print("")
'
}

# ─── evaluate JS in tab (returns raw JSON on stdout) ───────────────────────
# Forbidden in --dry-run; callers MUST gate.
cf_evaluate() {
  local tab="$1" js="$2"
  curl -sS -X POST "$CAMOFOX/tabs/$tab/evaluate" \
    -H 'Content-Type: application/json' \
    -d "$("$JQ" -n --arg e "$js" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
            '{expression:$e, userId:$uid, sessionKey:$sk}')" \
    --max-time 60
}

# ─── close tab ─────────────────────────────────────────────────────────────
cf_close() {
  local tab="$1"
  curl -sS -X DELETE "$CAMOFOX/tabs/$tab?userId=$USER_ID&sessionKey=$SESSION_KEY" >/dev/null
}

# ─── slack post (optional, swallows errors) ────────────────────────────────
slack_post() {
  local msg="$1" channel="${SLACK_REPORT_CHANNEL:-C091G3PKHL2}"
  [ -z "${SLACK_BOT_TOKEN:-}" ] && return
  local payload
  payload=$(MSG="$msg" CH="$channel" "$PYTHON" -c \
    'import json,os; print(json.dumps({"channel":os.environ["CH"],"text":os.environ["MSG"]}))')
  curl -s -X POST https://slack.com/api/chat.postMessage \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H 'Content-type: application/json; charset=utf-8' \
    -d "$payload" >/dev/null 2>&1 || true
}

# ─── redact: replace any env-loaded secret token in $1 with ***REDACTED*** ──
redact() {
  local s="$1"
  for v in "${LANCERS_PASSWORD:-}" "${GOOGLE_LOGIN_PASSWORD:-}" "${SLACK_BOT_TOKEN:-}" "${GITHUB_TOKEN:-}"; do
    [ -n "$v" ] && s="${s//$v/***REDACTED***}"
  done
  printf '%s' "$s"
}
