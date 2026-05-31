#!/usr/bin/env bash
# run.sh — one cycle of inbox scan + reply
# Usage: run.sh [--dry-run]   or   DRY_RUN=1 run.sh
set -euo pipefail

for arg in "$@"; do
  case "$arg" in
    --dry-run) export DRY_RUN=1 ;;
  esac
done

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

SKILL=~/.openclaw/skills/anicca-mail-auto-reply
mkdir -p "$SKILL/data/runs"
NOW=$(date +%Y-%m-%dT%H-%M-%S)
RUN="$SKILL/data/runs/$NOW"
mkdir -p "$RUN"

STATE="$SKILL/data/state.json"
SKIP="$SKILL/data/skip-patterns.json"
[ -f "$STATE" ] || echo '{"replied":[]}' > "$STATE"

ACCOUNT="${GMAIL_ACCOUNT:-${OSS_USER_EMAIL}}"
WINDOW_HOURS="${WINDOW_HOURS:-$(bash "$SKILL/scripts/lib/compute-window.sh")}"
MAX_REPLIES="${MAX_REPLIES:-5}"
DRY_RUN="${DRY_RUN:-0}"

echo "▶ scan inbox  account=$ACCOUNT  window=${WINDOW_HOURS}h"

# Step 1: list candidate threads from last N hours.
# TEST_MODE=1 drops `-from:me` so self → self test harness mails are visible.
RAW="$RUN/inbox.json"
if [ "${TEST_MODE:-0}" = "1" ]; then
  SEARCH_QUERY="in:inbox newer_than:${WINDOW_HOURS}h -label:CATEGORY_PROMOTIONS -label:CATEGORY_UPDATES"
else
  SEARCH_QUERY="in:inbox newer_than:${WINDOW_HOURS}h -from:me -label:CATEGORY_PROMOTIONS -label:CATEGORY_UPDATES"
fi
/opt/homebrew/bin/gog -a "$ACCOUNT" gmail search \
  "$SEARCH_QUERY" \
  --max 30 --json --results-only > "$RAW"

# Step 2: enrich each thread with from/subject/snippet + check we_replied
ENRICHED="$RUN/enriched.json"
"$SKILL/scripts/lib/enrich.py" "$RAW" "$ENRICHED" "$ACCOUNT" "$STATE"

# Step 3: triage
TRIAGED="$RUN/triaged.json"
"$SKILL/scripts/lib/triage.py" "$ENRICHED" "$SKIP" "$TRIAGED"

# Step 4: draft + send REPLY items
SENT_TS=()
SENT=0
SKIPPED=0
FAILED=0

PYBIN=python3
THREAD_COUNT=$($PYBIN -c "import json;d=json.load(open('$TRIAGED'));print(len(d))")
for i in $(seq 0 $((THREAD_COUNT-1))); do
  if [ "$SENT" -ge "$MAX_REPLIES" ]; then
    echo "  reached MAX_REPLIES=$MAX_REPLIES; stopping"
    break
  fi
  ROW=$($PYBIN -c "import json;d=json.load(open('$TRIAGED'));print(json.dumps(d[$i]))")
  VERDICT=$(echo "$ROW" | $PYBIN -c "import sys,json;print(json.load(sys.stdin).get('triage',''))")
  TRIAGE4=$(echo "$ROW" | $PYBIN -c "import sys,json;print(json.load(sys.stdin).get('triage4',''))")
  TID_SKIP=$(echo "$ROW" | $PYBIN -c "import sys,json;print(json.load(sys.stdin).get('thread_id',''))")
  REASON_SKIP=$(echo "$ROW" | $PYBIN -c "import sys,json;print(json.load(sys.stdin).get('triage_reason',''))")

  # ── FR-014 Power-Of-Free permanent BAN ─────────────────────────────────
  # If the thread matches the permanent BAN list, neither reply nor archive.
  # Leave it in the inbox for Dais's manual audit.
  POF_VERDICT=$(echo "$ROW" | python3 "$SKILL/scripts/lib/power-of-free-filter.py")
  if [ "$POF_VERDICT" = "BANNED" ]; then
    TID_LOG=$(echo "$ROW" | $PYBIN -c "import sys,json;print(json.load(sys.stdin).get('thread_id',''))")
    echo "  $TID_LOG Power-Of-Free BAN — no reply, no archive"
    bash "$HOME/.openclaw/skills/_shared/learnings-append.sh" \
      failure "policy.power-of-free" \
      "mail.reject.power-of-free" \
      0 \
      "Power-Of-Free BAN: $TID_LOG" \
      "thread=$TID_LOG" >/dev/null 2>&1 || true
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  # ── FR-015 Prompt-injection fail-CLOSED detector ───────────────────────
  # Any internal failure or detected injection → skip + Slack alert.
  BODY_FOR_INJ=$(echo "$ROW" | $PYBIN -c "import sys,json;print((json.load(sys.stdin).get('body','') or '')[:5000])")
  if echo "$BODY_FOR_INJ" | python3 "$SKILL/scripts/lib/injection-detector.py" | grep -qw INJECTION; then
    TID_LOG=$(echo "$ROW" | $PYBIN -c "import sys,json;print(json.load(sys.stdin).get('thread_id',''))")
    echo "  $TID_LOG injection detected · post #alert · skip"
    bash "$HOME/.openclaw/skills/_shared/learnings-append.sh" \
      failure "security.injection" \
      "mail.reject.injection" \
      0 \
      "Prompt-injection detected: $TID_LOG" \
      "thread=$TID_LOG" >/dev/null 2>&1 || true
    if [ -n "${SLACK_BOT_TOKEN:-}" ]; then
      python3 - "$SLACK_BOT_TOKEN" "${SLACK_REPORT_CHANNEL:-C091G3PKHL2}" "$TID_LOG" <<'PYALERT' >/dev/null 2>&1 || true
import sys, json, urllib.request
tok, ch, tid = sys.argv[1:4]
msg = {"channel": ch, "text": f":warning: prompt injection detected · thread {tid}"}
req = urllib.request.Request("https://slack.com/api/chat.postMessage",
  data=json.dumps(msg).encode(),
  headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
  method="POST")
try: urllib.request.urlopen(req, timeout=10)
except Exception: pass
PYALERT
    fi
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  if [ "$VERDICT" != "REPLY" ]; then
    # ★ Archive (INBOX label remove) で Dais の inbox を綺麗に保つ。
    # 対象: triage4=no かつ (a) SKIP_FROM/SUBJECT/voicemail/extra で hit (b) SELF_FROM だが subject が promo っぽい (FIX-TEST 等)
    # 除外: SELF_FROM で本当の通常 mail / FOLLOWUP / question / notify
    if [ "$TRIAGE4" = "no" ] && [ -n "$TID_SKIP" ]; then
      DO_ARCHIVE=0
      SUBJ_LC=$(echo "$ROW" | $PYBIN -c "import sys,json;print((json.load(sys.stdin).get('subject','') or '').lower())")
      if echo "$REASON_SKIP" | grep -qiE "SKIP_FROM regex|SKIP_SUBJECT regex|voicemail regex|extra_(from|subject)"; then
        DO_ARCHIVE=1
      elif echo "$REASON_SKIP" | grep -qi "SELF_FROM regex" \
           && echo "$SUBJ_LC" | grep -qiE "(sale|exclusive offer|50% off|promo|プロモーション|FIX-TEST|割引|セール|special offer|deal|clearance|free shipping|limited time)"; then
        DO_ARCHIVE=1
      fi
      if [ "$DO_ARCHIVE" = "1" ]; then
        /opt/homebrew/bin/gog -a "$ACCOUNT" gmail thread modify "$TID_SKIP" --remove INBOX --json > /dev/null 2>&1 \
          && echo "  $TID_SKIP archived (reason=$REASON_SKIP)" \
          || echo "  $TID_SKIP archive FAILED (continuing)"
      fi
    fi
    SKIPPED=$((SKIPPED+1))
    continue
  fi
  TID=$(echo "$ROW" | $PYBIN -c "import sys,json;print(json.load(sys.stdin).get('thread_id',''))")
  ALREADY=$($PYBIN -c "import json;d=json.load(open('$STATE'));print('yes' if '$TID' in d.get('replied',[]) else 'no')")
  if [ "$ALREADY" = "yes" ]; then
    echo "  $TID already replied — skip"
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  DRAFT="$RUN/draft-$i.txt"
  echo "$ROW" | "$SKILL/scripts/lib/draft.py" > "$DRAFT"

  # If draft.py signals "no reply" (LLM decided newsletter/skip), honour it
  DRAFT_CONTENT=$(cat "$DRAFT")
  # HARD RULE #6: draft.py is now a stub that returns "" — if empty, skip
  if [ -z "$(echo "$DRAFT_CONTENT" | tr -d "[:space:]")" ]; then
    echo "  $TID draft=empty(stub-no-llm) — heartbeat owns reply duty — skip"
    SKIPPED=$((SKIPPED+1))
    continue
  fi
  if echo "$DRAFT_CONTENT" | grep -qiE "^(No reply needed|返信不要|返信不要です|No response from|No response\.|返信は不要)"; then
    echo "  $TID draft=no-reply-signal — skip"
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  # Safety scan: reject drafts with unfilled placeholders
  if echo "$DRAFT_CONTENT" | grep -qE "\[記入\]|\[fill in\]|\[TBD\]|\[未定\]|\[name\]|\[NAME\]|\[.*\]|\{.*\}"; then
    echo "  $TID draft=placeholder-detected — STOP (Slack #inbox alert)"
    FAILED=$((FAILED+1))
    source ~/.openclaw/.env 2>/dev/null || true
    python3 - "$SLACK_BOT_TOKEN" "$TID" <<'PYALERT'
import sys, json, urllib.request
tok, tid = sys.argv[1], sys.argv[2]
msg = {"channel": "C091G3PKHL2", "text": f"⚠️ draft safety STOP: placeholder [記入] detected in draft for thread {tid}. Dais確認要・返信なし"}
req = urllib.request.Request("https://slack.com/api/chat.postMessage",
  data=json.dumps(msg).encode(),
  headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
  method="POST")
try:
    urllib.request.urlopen(req, timeout=10)
except Exception as e:
    print("slack err", e)
PYALERT
    continue
  fi

  SUBJ=$(echo "$ROW" | $PYBIN -c "import sys,json;s=json.load(sys.stdin).get('subject','') or '';print(('Re: '+s) if not s.startswith('Re:') else s)")
  MID=$(echo "$ROW" | $PYBIN -c "import sys,json;print(json.load(sys.stdin).get('latest_message_id',''))")

  echo "  reply → $TID  subject=$(echo "$SUBJ" | head -c 60)"

  if [ "$DRY_RUN" = "1" ]; then
    echo "    [DRY_RUN] would send (draft saved at $DRAFT)"
    SENT=$((SENT+1))
    continue
  fi

  # ── FR-006 Forbidden-substring safety gate ─────────────────────────────
  # Block reply draft if it contains [記入] / on behalf of Daisuke / +1 (336) etc.
  if ! cat "$DRAFT" | bash "$SKILL/scripts/lib/safety-scan.sh"; then
    echo "  $TID safety-scan BLOCK · skip send · escalate to .learnings (Plan-T19)"
    bash "$HOME/.openclaw/skills/_shared/learnings-append.sh" \
      failure "draft.placeholder" \
      "mail.reject.safety-scan" \
      0 \
      "Safety-scan blocked draft: $TID" \
      "thread=$TID" >/dev/null 2>&1 || true
    FAILED=$((FAILED+1))
    continue
  fi

  if /opt/homebrew/bin/gog -a "$ACCOUNT" gmail send \
       --reply-to-message-id "$MID" --reply-all \
       --subject "$SUBJ" --body-file "$DRAFT" --json > "$RUN/sent-$i.json"; then
    # record in state
    $PYBIN -c "
import json
d=json.load(open('$STATE'))
d.setdefault('replied',[]).append('$TID')
d['replied']=d['replied'][-1000:]
json.dump(d,open('$STATE','w'),ensure_ascii=False,indent=2)"
    VERDICT_LC=$(echo "$VERDICT" | tr '[:upper:]' '[:lower:]')
    bash "$HOME/.openclaw/skills/_shared/learnings-append.sh" \
      success "best_practice" \
      "mail.reply.success.${VERDICT_LC}" \
      1 \
      "Replied to $TID via $VERDICT" \
      "subject=$SUBJ" >/dev/null 2>&1 || true
    SENT=$((SENT+1))
  else
    echo "    ❌ send failed"
    FAILED=$((FAILED+1))
  fi
  sleep 3
done

echo "✅ run: sent=$SENT skipped=$SKIPPED failed=$FAILED  raw=$RUN"

# Update last-run-ts (FIX 4: missed-run detection)
mkdir -p "$SKILL/state"; date +%s > "$SKILL/state/last-run-ts.txt"

# Slack report
$PYBIN - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$SENT" "$SKIPPED" "$FAILED" "$RUN" "$DRY_RUN" <<'PY'
import sys, json, urllib.request
ch, tok, sent, skipped, failed, run, dry = sys.argv[1:8]
payload = {
  "channel": ch,
  "text": f"📬 anicca-mail-auto-reply: sent={sent} skipped={skipped} failed={failed}",
  "blocks":[
    {"type":"header","text":{"type":"plain_text","text":"📬 mail-auto-reply cycle"}},
    {"type":"section","fields":[
      {"type":"mrkdwn","text":f"*sent:*\n{sent}"},
      {"type":"mrkdwn","text":f"*skipped:*\n{skipped}"},
      {"type":"mrkdwn","text":f"*failed:*\n{failed}"},
      {"type":"mrkdwn","text":f"*dry_run:*\n{dry}"},
    ]},
    {"type":"context","elements":[{"type":"mrkdwn","text":f"raw `{run}`"}]},
  ],
}
req=urllib.request.Request("https://slack.com/api/chat.postMessage",
  data=json.dumps(payload).encode(),
  headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json; charset=utf-8"},
  method="POST")
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(json.loads(r.read().decode()).get("ts","?"))
except Exception as e:
    print("slack err",e)
PY
