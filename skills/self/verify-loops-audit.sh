#!/usr/bin/env bash
# verify-loops-audit.sh — INDEPENDENT scheduled auditor (FIND-016). launchd runs this every 6h. It (1) runs the
# real-side-effect verifier, (2) sends the honest scorecard to the report channel so no-op loops become visible
# (covers life-manager, which has no daily artifact for its own healthcheck), and (3) escalates any loop whose REAL
# output artifact is stale to an autonomous self-fix — grounded in the artifact, never a self-graded marker.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail
SELF="${VERIFY_LOOPS_SELF_DIR:-$HOME/anicca/skills/self}"; now=$(date +%s)
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
# LM has no daily artifact; if its liveness heartbeat is stale the healthcheck restarts it — the audit surfaces both
# the staleness (in HOURS, FIND-022 bug fix: was interpolating the file PATH) and the live Stripe MRR so a no-op LM
# loop is visible in every 6h report.
LMH="$(stale_hrs "$LMHB")"
LM_MRR="$(grep -E '^lm_mrr_usd:' "$SELF/life-manager-loop/state/STATE.md" 2>/dev/null|awk '{print $2}'|tail -1)"; LM_MRR="${LM_MRR:-NA}"
if [ "$LMH" -ge 26 ] 2>/dev/null; then LM_NOTE=" | ⚠ LM last-pass STALE ${LMH}h, mrr=\$$LM_MRR"; else LM_NOTE=" | LM last-pass ${LMH}h, mrr=\$$LM_MRR"; fi

# --- REQ-LV-102/103/104: Cadence Contract escalation + scorecard for the 7 contract loops. This
# REPLACES the old fresh()/stale_hrs() judgment for these 7 loops ONLY — capafy/reddit/lm (above)
# keep stale_hrs()/self-fix unchanged (REQ-LV-104, out of this feature's scope).
STATE_DIR="$HOME/.openclaw/state"; mkdir -p "$STATE_DIR"
TODAY_JST="$(TZ=Asia/Tokyo date +%F)"
NOW_HOUR_JST="$(TZ=Asia/Tokyo date +%H)"
CADENCE_LOOPS="clip affiliate video gig bounty pm-earner founder-loop"
CADENCE_SCORECARD=""
for L in $CADENCE_LOOPS; do
  STATUS_JSON="$(python3 "$SELF/cadence-evidence.py" status "$L" 2>>"$LOG")"
  MET="$(printf '%s' "$STATUS_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['met'])" 2>/dev/null || echo False)"
  SCORECARD_LINE="$(printf '%s' "$STATUS_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['scorecard'])" 2>/dev/null || echo "❌missed (streak=0)")"
  CADENCE_SCORECARD="$CADENCE_SCORECARD [$L] $SCORECARD_LINE;"
  # REQ-LV-102: at/after JST 21:00, escalate any loop whose TODAY's cadence is unmet — never
  # suppressed by a past-days success (the exact bug class REQ-LV-101's row-exists/increment/
  # recency dispatch fixes). Escalate at most once per loop per JST calendar day (marker file).
  if [ "$NOW_HOUR_JST" -ge 21 ] 2>/dev/null && [ "$MET" = "False" ]; then
    MK="$STATE_DIR/.cadence-escalated-$L-$TODAY_JST"
    if [ ! -f "$MK" ]; then
      touch "$MK"
      bash "$SELF/self-fix.sh" "$L" "cadence audit: $L's Cadence Contract was NOT met by 21:00 JST today ($TODAY_JST) — diagnose why today's contracted cadence (see $SELF/cadence-contracts.json) did not happen and fix it. This is a DAILY judgment (not artifact staleness): a real pass days ago does NOT satisfy today's contract." >> "$LOG" 2>&1 || true
    fi
  fi
done

# send the honest scorecard to the report channel (visibility = no-op auto-detection for every loop incl LM)
if [ -x "$SELF/../report/loop-report.sh" ]; then
  bash "$SELF/../report/loop-report.sh" audit "$(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-900)$LM_NOTE |$CADENCE_SCORECARD" no-op 0 "none: routine 6h scorecard, no per-pass artifact" >> "$LOG" 2>&1 || true
fi
echo "[verify-loops-audit] done $(date '+%F %T')"
