#!/bin/bash
# Watches the x402 server access pattern + posts to Slack #metrics every time a
# /v0/echo or /v0/learn route returns HTTP 200 (= a paying call was honored).
#
# Source of truth: /tmp/anicca-x402.log (Hono via tsx) — the server itself emits
# request-line traces via Hono's default logger isn't on; instead we instrument
# server.ts to write a single REVENUE line per 200 response. This wrapper tails
# that file and forwards each REVENUE line to Slack chat.postMessage.
#
# Channel: #metrics (C091G3PKHL2). Token: SLACK_BOT_TOKEN in ~/.openclaw/.env.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${HOME}/.openclaw/.env"
SERVER_LOG="/tmp/anicca-x402.log"
STATE_FILE="${HOME}/.openclaw/state/anicca_x402_revenue.jsonl"
SLACK_CHANNEL="C091G3PKHL2"
CFO_HOOK="${X402_CFO_HOOK:-$SCRIPT_DIR/cfo-hook.sh}"

# shellcheck disable=SC1090
[ -f "${ENV_FILE}" ] && set -a && . "${ENV_FILE}" && set +a

mkdir -p "${HOME}/.openclaw/state"
: >>"${STATE_FILE}"

if [ -z "${SLACK_BOT_TOKEN:-}" ]; then
  echo "[monitor] FATAL: SLACK_BOT_TOKEN missing from ${ENV_FILE}" >&2
  exit 1
fi

echo "[monitor] tailing ${SERVER_LOG} for REVENUE lines → Slack #metrics" >&2

tail -F -n 0 "${SERVER_LOG}" 2>/dev/null | while read -r line; do
  case "${line}" in
    *REVENUE*)
      # Persist the raw line so we have an append-only ledger.
      printf '%s\n' "${line}" >>"${STATE_FILE}"
      # Fire the CFO hook (best-effort; never blocks the Slack post).
      if [ -x "${CFO_HOOK}" ]; then
        "${CFO_HOOK}" "${line}" >/dev/null 2>&1 || true
      fi
      # Post to Slack.
      /usr/bin/curl -sS -m 10 -X POST \
        -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
        -H "Content-Type: application/json; charset=utf-8" \
        -d "$(printf '{"channel":"%s","text":"x402-revenue: %s"}' \
              "${SLACK_CHANNEL}" \
              "$(printf '%s' "${line}" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read())[1:-1])')")" \
        https://slack.com/api/chat.postMessage >/dev/null 2>&1 || true
      ;;
  esac
done
