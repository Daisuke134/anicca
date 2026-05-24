#!/usr/bin/env bash
# connpass-lt-apply.sh — daily: discover AI LT events on connpass, register for OPEN
# speaker (LT/発表/登壇) slots that pass 3 gates (AI-relevant + no Mon-Fri 9-17 + no
# gcal time-overlap incl 🎓 school / 💼 work, 60min travel buffer), gcal + report.
#
# Replayable by any agent. Login = camofox session "connpass" (DaisNar / GitHub OAuth).
# stdout last line: CONNPASS_DISCOVER: {...}
set -uo pipefail

SKILL="$HOME/.openclaw/skills/anicca-meetup-talk-applier"
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
: "${GOG_ACCOUNT:={{profile.contact.personalEmail}}}"; : "${GOG_KEYRING_PASSWORD:=<password>}"
export GOG_ACCOUNT GOG_KEYRING_PASSWORD
U="anicca"; S="connpass"; CF="http://localhost:9377"

bash "$HOME/.openclaw/skills/camofox-{{profile.lateness.stakeholders.channel}}/scripts/start.sh" >/dev/null 2>&1

# ── ensure connpass login (idempotent; cookie persists per session) ───────────
TAB=$(curl -sS -X POST "$CF/tabs" -H 'Content-Type: application/json' \
  -d "{\"url\":\"https://connpass.com/dashboard/\",\"userId\":\"$U\",\"sessionKey\":\"$S\"}" | jq -r .tabId)
sleep 5
SNAP=$(curl -sS "$CF/tabs/$TAB/snapshot?userId=$U&sessionKey=$S" 2>/dev/null)
if ! echo "$SNAP" | grep -q "ログアウト\|イベント検索\|ダッシュボード"; then
  curl -sS -X POST "$CF/tabs/$TAB/navigate" -H 'Content-Type: application/json' \
    -d "{\"url\":\"https://connpass.com/login/\",\"userId\":\"$U\",\"sessionKey\":\"$S\"}" >/dev/null 2>&1
  sleep 4
  # find username/password refs from snapshot (e11/e12/e13 typical)
  curl -sS -X POST "$CF/tabs/$TAB/evaluate" -H 'Content-Type: application/json' \
    -d "{\"expression\":\"(()=>{const u=document.querySelector('input[name=username],input[type={{profile.lateness.stakeholders.channel}}],#id_username');const p=document.querySelector('input[type=password]');if(u){u.value='${CONNPASS_USERNAME}';u.dispatchEvent(new Event('input',{bubbles:true}));}if(p){p.value='${CONNPASS_PASSWORD}';p.dispatchEvent(new Event('input',{bubbles:true}));}const b=[...document.querySelectorAll('button,input[type=submit]')].find(e=>/ログイン|login/i.test(e.textContent||e.value||''));if(b)b.click();return 'login-submitted';})()\",\"userId\":\"$U\",\"sessionKey\":\"$S\"}" >/dev/null 2>&1
  sleep 6
fi
curl -sS -X DELETE "$CF/tabs/$TAB?userId=$U&sessionKey=$S" >/dev/null 2>&1

# ── discover + apply (3-gate safe auto-register) ──────────────────────────────
OUT=$(python3 "$SKILL/scripts/connpass-lt-discover.py" --apply --max 30 \
  --keywords "AI,LT,AIエージェント,LLM,なんでもLT,Claude,生成AI,MCP" 2>&1 | tail -1)
echo "$OUT"

# ── Slack report ──────────────────────────────────────────────────────────────
if command -v openclaw &>/dev/null; then
  APPLIED=$(echo "$OUT" | sed 's/^CONNPASS_DISCOVER: //' | jq -r '(.applied//[])|length' 2>/dev/null || echo "?")
  OPEN=$(echo "$OUT" | sed 's/^CONNPASS_DISCOVER: //' | jq -r '(.open_speaker//[])|length' 2>/dev/null || echo "?")
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --text "🎤 connpass AI-LT daily: open-speaker=$OPEN, registered=$APPLIED (3-gate: relevant+no-dayjob+no-conflict)." 2>/dev/null || true
fi
