#!/usr/bin/env bash
# verify-loops.sh — proves the 3 loops produce REAL side-effects (not just ALIVE). Anti-fake: reads only
# observable artifacts (published.jsonl mtime+count, reddit posts ledger, loop-report.log), never STATE claims.
set -uo pipefail
now=$(date +%s); fresh(){ local f="$1" hrs="${2:-26}"; [ -f "$f" ] || { echo "MISSING"; return; }; local m; m=$(stat -f %m "$f" 2>/dev/null||echo 0); local h=$(( (now-m)/3600 )); [ "$h" -le "$hrs" ] && echo "FRESH(${h}h)" || echo "STALE(${h}h)"; }
echo "=== LOOP REAL-SIDE-EFFECT VERIFICATION ($(date '+%F %H:%M')) ==="
# 1 CAPAFY: a skill actually published in last 26h?
PUB=~/.openclaw/skills/capafy-autopublish/state/published.jsonl
CNT=$(grep -c . "$PUB" 2>/dev/null||echo 0)
echo "[capafy]  published.jsonl: $CNT skills total | newest: $(fresh "$PUB") | last title: $(tail -1 "$PUB" 2>/dev/null | python3 -c 'import sys,json;print(json.loads(sys.stdin.read()).get("title","?")[:45])' 2>/dev/null||echo NA)"
echo "          → daily-publish OK only if a NEW line appears each day (compare CNT over days)"
# 2 REDDIT: a real post/comment made? (posts ledger the loop writes) + account exists
ACC=~/.cloak/reddit-accounts.json; POSTS=~/anicca/skills/self/reddit-loop/state/posts.jsonl
NACC=$([ -f "$ACC" ] && python3 -c "import json;d=json.load(open('$ACC'));print(len(d if isinstance(d,list) else d.get('accounts',[])))" 2>/dev/null||echo 0)
NPOST=$(grep -c . "$POSTS" 2>/dev/null||echo 0)
echo "[reddit]  accounts: $NACC | posts logged: $NPOST | posts ledger: $(fresh "$POSTS")"
echo "          → posted OK only if posts.jsonl grows with real comment URLs"
# 3 LM: improving? last-pass fresh + a report logged
LMHB=~/.openclaw/state/.life-manager-loop-last-pass
echo "[lm]      last-pass: $(fresh "$LMHB") | recent reports: $(grep -c 'loop=life-manager' ~/.openclaw/logs/loop-report.log 2>/dev/null||echo 0)"
echo "          → improving OK only if a fresh pass + a real funnel change is recorded"
echo "--- loop-report tail (real executions) ---"; tail -4 ~/.openclaw/logs/loop-report.log 2>/dev/null
