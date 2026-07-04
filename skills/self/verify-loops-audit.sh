#!/usr/bin/env bash
# verify-loops-audit.sh — INDEPENDENT scheduled auditor (FIND-016). launchd runs this every 6h. It (1) runs the
# real-side-effect verifier, (2) sends the honest scorecard to the report channel so no-op loops become visible
# (covers life-manager, which has no daily artifact for its own healthcheck), and (3) escalates any loop whose REAL
# output artifact is stale to an autonomous self-fix — grounded in the artifact, never a self-graded marker.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail
SELF="$HOME/anicca/skills/self"; now=$(date +%s)
OUT="$(bash "$SELF/verify-loops.sh" 2>&1)"
LOG="$HOME/.openclaw/logs/verify-loops-audit.log"; mkdir -p "$(dirname "$LOG")"
printf '=== %s ===\n%s\n' "$(date '+%F %T')" "$OUT" >> "$LOG"

stale_hrs(){ [ -f "$1" ] || { echo 99999; return; }; echo $(( (now-$(stat -f %m "$1" 2>/dev/null||echo 0))/3600 )); }
CAP="$HOME/.openclaw/skills/capafy-autopublish/state/published.jsonl"
POSTS="$SELF/reddit-loop/state/posts.jsonl"
LMHB="$HOME/.openclaw/state/.life-manager-loop-last-pass"

# escalate stale real outputs (only via self-fix.sh, which self-guards against duplicate/hung fixers)
[ "$(stale_hrs "$CAP")" -ge 30 ] && bash "$SELF/self-fix.sh" capafy "audit: no new capafy skill published in >30h (published.jsonl stale). Fix the publish pipeline so a real skill lands." >> "$LOG" 2>&1 || true
# reddit: only escalate if an account exists (else it is legitimately pre-provision)
NACC=0; [ -f "$HOME/.cloak/reddit-accounts.json" ] && NACC="$(python3 -c "import json;d=json.load(open('$HOME/.cloak/reddit-accounts.json'));print(len(d if isinstance(d,list) else d.get('accounts',[])))" 2>/dev/null||echo 0)"
{ [ "$NACC" -ge 1 ] 2>/dev/null && [ "$(stale_hrs "$POSTS")" -ge 30 ]; } && bash "$SELF/self-fix.sh" reddit "audit: reddit has an account but no real post in >30h (posts.jsonl stale). Make it post one honest disclosed contribution and log the URL." >> "$LOG" 2>&1 || true
# LM has no daily artifact; if its liveness heartbeat is stale the healthcheck restarts it — the audit just surfaces it.
LM_NOTE=""; [ "$(( $(stale_hrs "$LMHB")/1 ))" -ge 26 ] && LM_NOTE=" | ⚠ LM last-pass stale ${LMHB}"

# send the honest scorecard to the report channel (visibility = no-op auto-detection for every loop incl LM)
if [ -x "$SELF/../report/loop-report.sh" ]; then
  bash "$SELF/../report/loop-report.sh" audit "$(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-900)$LM_NOTE" no-op 0 none >> "$LOG" 2>&1 || true
fi
echo "[verify-loops-audit] done $(date '+%F %T')"
