#!/usr/bin/env bash
# lib/outbound-realtime.sh — ElevenLabs Twilio outbound realtime calling
# Source this from phase scripts. Provides:
#   - outbound_call <to_e164> <context_text> [first_message] -> emits {conversation_id, callSid, to}
#   - poll_conversation <conversation_id> [timeout_s] -> waits + emits transcript JSON
#   - slack_report_call <conv_json>
set -euo pipefail

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

: "${ELEVENLABS_AGENTS_KEY:?ELEVENLABS_AGENTS_KEY required}"
: "${ANICCA_AGENT_ID:=agent_6601kr8fjyj3e4hrdb00kv1942ne}"
: "${ANICCA_PHONE_ID:=phnum_0901kr8gsfzsfdarm6emj5dk6csv}"
: "${ANICCA_PHONE_E164:=+13366526842}"

ELEVEN_BASE="https://api.elevenlabs.io"

# outbound_call <to_e164> <context_text> [first_message]
outbound_call() {
  local to="${1:?to (E.164) required, e.g. {{profile.contact.phone}}}"
  local context="${2:?context required}"
  local first="${3:-Hello, this is Anicca, an autonomous AI Buddhist entity. I would like to talk briefly. Is this a good time?}"

  local payload
  payload=$(TO="$to" CTX="$context" FIRST="$first" python3 -c '
import json, os
print(json.dumps({
  "agent_id": os.environ.get("ANICCA_AGENT_ID","'$ANICCA_AGENT_ID'"),
  "agent_phone_number_id": os.environ.get("ANICCA_PHONE_ID","'$ANICCA_PHONE_ID'"),
  "to_number": os.environ["TO"],
  "conversation_initiation_client_data": {
    "conversation_config_override": {
      "agent": {
        "first_message": os.environ["FIRST"]
      }
    },
    "dynamic_variables": {
      "call_context": os.environ["CTX"]
    }
  }
}))')

  curl -sS -X POST "$ELEVEN_BASE/v1/convai/twilio/outbound-call" \
    -H "xi-api-key: $ELEVENLABS_AGENTS_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload"
}

# poll_conversation <conversation_id> [timeout_s]
poll_conversation() {
  local conv="${1:?conversation_id required}"
  local timeout="${2:-300}"
  local elapsed=0
  while [ "$elapsed" -lt "$timeout" ]; do
    local resp
    resp=$(curl -sS "$ELEVEN_BASE/v1/convai/conversations/$conv" -H "xi-api-key: $ELEVENLABS_AGENTS_KEY")
    local status
    status=$(echo "$resp" | python3 -c "import sys,json;print(json.load(sys.stdin).get('status',''))")
    if [ "$status" = "done" ] || [ "$status" = "failed" ] || [ "$status" = "completed" ]; then
      echo "$resp"
      return 0
    fi
    sleep 6
    elapsed=$((elapsed+6))
  done
  curl -sS "$ELEVEN_BASE/v1/convai/conversations/$conv" -H "xi-api-key: $ELEVENLABS_AGENTS_KEY"
}

# slack_report_call <to> <conv_json> <subject>
slack_report_call() {
  local to="${1:?to required}"
  local conv_json="${2:?conv json required}"
  local subject="${3:-outbound call}"
  python3 - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$to" "$subject" "$conv_json" <<'PY'
import sys, json, urllib.request
ch, token, to, subject, conv_json = sys.argv[1:6]
try:
    conv = json.loads(conv_json)
except Exception:
    conv = {"_raw": conv_json[:500]}
cid = conv.get("conversation_id") or conv.get("id") or "?"
status = conv.get("status","?")
duration = (conv.get("metadata",{}) or {}).get("call_duration_secs", "?")
transcript = conv.get("transcript", []) or []
preview_lines = []
for m in transcript[:8]:
    role = m.get("role","?")
    msg = (m.get("message","") or "")[:120]
    preview_lines.append(f"{role}: {msg}")
preview = "\n".join(preview_lines) or "(empty transcript)"
payload = {
  "channel": ch,
  "text": f"📞 {subject} → {to} ({status})",
  "blocks": [
    {"type":"header","text":{"type":"plain_text","text":f"📞 {subject}"}},
    {"type":"section","fields":[
      {"type":"mrkdwn","text":f"*to:*\n`{to}`"},
      {"type":"mrkdwn","text":f"*conv:*\n`{cid}`"},
      {"type":"mrkdwn","text":f"*status:*\n{status}"},
      {"type":"mrkdwn","text":f"*duration:*\n{duration}s"},
    ]},
    {"type":"section","text":{"type":"mrkdwn","text":f"```\n{preview}\n```"}},
  ],
}
req = urllib.request.Request("https://slack.com/api/chat.postMessage",
    data=json.dumps(payload).encode(),
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json; charset=utf-8"},
    method="POST")
with urllib.request.urlopen(req, timeout=15) as r:
    print(json.loads(r.read().decode()).get("ts","?"))
PY
}
