#!/usr/bin/env bash
# loop-report.sh — per-pass mail report for claude-p loops (clip/affiliate/video/bounty/gig).
# Thin wrapper around the AgentMail POST already proven in anicca-report.sh (see that file for
# the ClawRouter/genesis wallet-net-worth variant). claude-p loops carry no wallet (SOL_WALLET is
# a display-only address, spec §6) so this version reports WHAT the loop did, not net worth.
# Spec: docs/superpowers/specs/2026-07-04-openclaw-claude-p-merge-design.md §10.2
#
#   bash loop-report.sh <loop_name> <did> <result> <earned_usdc> [evidence_url]
#     <loop_name>    clip | affiliate | video | bounty | gig
#     <did>          one-line natural-language summary of what happened this pass
#                     (agent-authored — judgment stays with the agent, this tool only sends it)
#     <result>       success | failure | queue-empty (short state word)
#     <earned_usdc>  USDC confirmed this pass, or 0
#     [evidence_url] optional, defaults to "none". The actual verifiable URL for this pass
#                     (the IG reel/post you published, the PR you opened, the gig you
#                     delivered). Agent-authored, same as <did> — this tool only sends it.
#                     If nothing was posted/shipped this pass, pass the literal string "none".
#
# Dais 2026-07-04 verbatim: "if they were given that, given the credential, they have to do
# that. If they are not given, they do not need to do [it]." -> fail-closed no-op when the
# credential is absent, never an error, never blocks the loop that calls it (exit 0 always).
#
# Dais 2026-07-04 verbatim (spec §14): "I want to receive the actual video, the actual link
# of the video, as evidence... If they just say 'yeah I've done it' there's no meaning."
# -> evidence_url exists so the report is verifiable, not a self-reported vibe.
set -u

# lr_valid_evidence — REQ-LV-003 evidence gate predicate, pure (no I/O). Mirrors this codebase's
# `--<flag>` direct-call convention (self-fix.sh::sf_should_continue --should-continue,
# healthcheck-runtime-loop.sh::hrl_classify --classify). Rejects (rc=1) an empty string or a bare
# "none" (case-insensitive, whitespace trimmed); "none: <reason>" or any other non-empty string
# is accepted (rc=0).
lr_valid_evidence(){
  local v="${1:-}"
  v="$(printf '%s' "$v" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  [ -z "$v" ] && return 1
  local lower; lower="$(printf '%s' "$v" | tr '[:upper:]' '[:lower:]')"
  [ "$lower" = "none" ] && return 1
  return 0
}

if [ "${1:-}" = "--valid-evidence" ]; then
  lr_valid_evidence "${2:-}"
  exit $?
fi

LOOP_NAME="${1:-unknown}"
DID="${2:-(no summary provided)}"
RESULT="${3:-unknown}"
EARNED="${4:-0}"
EVIDENCE_URL="${5:-none}"

LOG="$HOME/.local/state/life-manager/logs/loop-report.log"
mkdir -p "$(dirname "$LOG")" 2>/dev/null

# REQ-LV-003: evidence gate — an empty or bare-"none" evidence_url is rejected before anything is
# sent or resolved, regardless of AGENTMAIL_API_KEY state (a caller must always supply a reason).
if ! lr_valid_evidence "$EVIDENCE_URL"; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) loop=$LOOP_NAME REJECTED (empty-or-bare-none evidence)" >> "$LOG" 2>/dev/null
  exit 1
fi

# REQ-LV-001: self-resolve AGENTMAIL_API_KEY from $HOME/.local/state/life-manager/.env before deciding NO-OP (the
# caller is no longer required to have pre-sourced it).
if [ -z "${AGENTMAIL_API_KEY:-}" ] && [ -f "$HOME/.local/state/life-manager/.env" ]; then
  set -a; . "$HOME/.local/state/life-manager/.env" 2>/dev/null || true; set +a
fi

# Credential not given, even after self-resolve -> silently no-op (Dais: do not report if not
# given the credential).
if [ -z "${AGENTMAIL_API_KEY:-}" ]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) loop=$LOOP_NAME NO-OP (AGENTMAIL_API_KEY unset)" >> "$LOG" 2>/dev/null
  exit 0
fi

TO_ADDR="${LOOP_REPORT_TO:?LOOP_REPORT_TO is required}"
SUBJECT="Anicca loop report: $LOOP_NAME"
BODY="LOOP $LOOP_NAME
DID $DID
RESULT $RESULT
EARNED \$$EARNED USDC
EVIDENCE $EVIDENCE_URL"

PAYLOAD=$(python3 -c "
import json, sys
to_addr, subject, body = sys.argv[1], sys.argv[2], sys.argv[3]
print(json.dumps({'to': [to_addr], 'subject': subject, 'text': body}))
" "$TO_ADDR" "$SUBJECT" "$BODY" 2>/dev/null)

if [ -z "$PAYLOAD" ]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) loop=$LOOP_NAME FAIL (payload build error)" >> "$LOG" 2>/dev/null
  exit 0
fi

RESPONSE=$(curl -s --max-time 20 -w $'\nHTTP_STATUS:%{http_code}' \
  -X POST "https://api.agentmail.to/v0/inboxes/anicca-genesis@agentmail.to/messages/send" \
  -H "Authorization: Bearer $AGENTMAIL_API_KEY" -H "Content-Type: application/json" \
  -d "$PAYLOAD" 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
RESP_BODY=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:[0-9]*$//')

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) loop=$LOOP_NAME SENT http=$HTTP_CODE" >> "$LOG" 2>/dev/null
else
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) loop=$LOOP_NAME FAIL http=$HTTP_CODE resp=$RESP_BODY" >> "$LOG" 2>/dev/null
fi

exit 0   # never block the calling loop — mail failure is logged, not fatal
