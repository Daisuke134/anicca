#!/usr/bin/env bash
# verify-loops.sh — proves the 3 loops produce REAL side-effects (not just ALIVE). Anti-fake: reads only observable
# artifacts AND, when an artifact records a URL, actually CURLS it to confirm the thing is live (FIND-007) — so a
# fabricated log line cannot pass. Never trusts a loop's STATE self-claim.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail
now=$(date +%s)
# FIND-010: safe non-empty-line count (grep -c prints "0" on no match; do NOT chain ||echo which double-prints).
count(){ [ -f "$1" ] || { echo 0; return; }; local n; n="$(grep -c . "$1" 2>/dev/null)"; echo "${n:-0}"; }
fresh(){ local f="$1" hrs="${2:-26}"; [ -f "$f" ] || { echo "MISSING"; return; }; local m h; m=$(stat -f %m "$f" 2>/dev/null||echo 0); h=$(( (now-m)/3600 )); [ "$h" -le "$hrs" ] && echo "FRESH(${h}h)" || echo "STALE(${h}h)"; }
# extract the last URL recorded in a jsonl file (any http(s) url), then curl it: LIVE(code) / DEAD(code) / NO-URL.
liveurl(){ local f="$1"; [ -f "$f" ] || { echo "NO-FILE"; return; }
  local u; u="$(grep -oE 'https?://[^"[:space:]]+' "$f" 2>/dev/null | tail -1)"
  [ -z "$u" ] && { echo "NO-URL-IN-LEDGER"; return; }
  local code; code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 12 -L "$u" 2>/dev/null||echo 000)"
  case "$code" in 200|201|202|301|302|308) echo "LIVE($code) $u";; *) echo "DEAD($code) $u";; esac; }

echo "=== LOOP REAL-SIDE-EFFECT VERIFICATION ($(date '+%F %H:%M')) ==="
# 1 CAPAFY: a skill actually published + the newest listing URL actually live
PUB="$HOME/.openclaw/skills/capafy-autopublish/state/published.jsonl"
echo "[capafy]  published: $(count "$PUB") skills | newest-line: $(fresh "$PUB") | live-check: $(liveurl "$PUB")"
echo "          → PASS only if count grows daily AND newest listing URL is LIVE"
# 2 REDDIT: a real post made + its URL live + an account exists
ACC="$HOME/.cloak/reddit-accounts.json"; POSTS="$HOME/anicca/skills/self/reddit-loop/state/posts.jsonl"
NACC=0; [ -f "$ACC" ] && NACC="$(python3 -c "import json;d=json.load(open('$ACC'));print(len(d if isinstance(d,list) else d.get('accounts',[])))" 2>/dev/null||echo 0)"
echo "[reddit]  accounts: $NACC | posts: $(count "$POSTS") | newest-post: $(fresh "$POSTS") | live-check: $(liveurl "$POSTS")"
echo "          → PASS only if posts.jsonl grows AND newest comment URL is LIVE"
# 3 LM: improving (fresh pass + report) — revenue truth is Stripe (separate), no daily artifact to curl
LMHB="$HOME/.openclaw/state/.life-manager-loop-last-pass"
echo "[lm]      last-pass: $(fresh "$LMHB") | reports: $(grep -c 'loop=life-manager' "$HOME/.openclaw/logs/loop-report.log" 2>/dev/null||echo 0)"
echo "          → PASS only if a fresh pass + a real recorded funnel change (revenue via Stripe verify)"
echo "--- self-fix result markers (autonomous fixes) ---"
for L in capafy reddit life-manager; do r="$HOME/.openclaw/state/.self-fix-$L.result"; [ -f "$r" ] && echo "  [$L] $(cat "$r")"; done
echo "--- loop-report tail (real executions) ---"; tail -4 "$HOME/.openclaw/logs/loop-report.log" 2>/dev/null
