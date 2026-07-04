#!/usr/bin/env bash
# reddit-loop/loop.sh — ONE no-human wake of the Reddit demand-gen loop (feeds life-manager-loop). This is
# NOT revenue; it measures the DEMAND engine's health/progress honestly. Anti-fake: a signup is "attributed"
# only if a real marker exists; karma/age come from the account ledger the ACT writes; nothing is invented.
# Seams: RD_TEST=1 + RD_ACCOUNTS=<file> + RD_DIR + RD_REQ.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; DIR="${RD_DIR:-$HERE}"; STATE_MD="$DIR/state/STATE.md"; mkdir -p "$DIR/state"
REQ="${RD_REQ:-$HOME/.openclaw/state/reddit-loop-selfheal-request.json}"
ACCTS="${RD_ACCOUNTS:-$HOME/.cloak/reddit-accounts.json}"
HEAL=""; add_heal(){ HEAL="$HEAL$1; "; }
# HEAL: is there at least one reddit account provisioned?
N_ACCT=0
if [ -f "$ACCTS" ]; then N_ACCT="$(python3 -c "import json,sys;d=json.load(open('$ACCTS'));print(len(d if isinstance(d,list) else d.get('accounts',[])))" 2>/dev/null||echo 0)"; fi
[ "$N_ACCT" -ge 1 ] 2>/dev/null || add_heal "NO-REDDIT-ACCOUNT → self-provision one (CloakBrowser :9222 + Gmail plus-address keiodaisuke+reddit<tag>@gmail.com, OTP via gog gmail; same zero-human flow as ig-account-create)"
# HEAL: CloakBrowser daily-driver reachable (needed to act)?
if [ "${RD_TEST:-}" != "1" ]; then
  curl -s --max-time 5 -o /dev/null http://127.0.0.1:9222/json/version 2>/dev/null || add_heal "CLOAKBROWSER-DOWN(:9222) → start the daily-driver"
fi
# READ: karma + age + attributed signups (from the ledger the ACT maintains)
KARMA="$(python3 -c "import json;d=json.load(open('$ACCTS'));a=(d if isinstance(d,list) else d.get('accounts',[]));print(sum(int(x.get('comment_karma',0)) for x in a))" 2>/dev/null||echo 0)"
SIGNUPS="$(grep -c . "$DIR/state/attributed-signups.jsonl" 2>/dev/null||echo 0)"
PREV="$(grep -E '^comment_karma_total:' "$STATE_MD" 2>/dev/null|awk '{print $2}'|tail -1)"; PREV="${PREV:-n/a}"
if [ -n "$HEAL" ]; then STATUS="HEAL-NEEDED — ${HEAL}"
elif [ "$KARMA" -lt 50 ] 2>/dev/null; then STATUS="WARMING — karma $KARMA (<50): keep making genuine value-first comments in r/ADHD etc; do NOT post product links yet (new/low-karma accounts get auto-removed)"
else STATUS="READY — karma $KARMA: post occasional genuine builder-story + answer real questions; product surfaces naturally as the lateness pain, never pushy; track reddit→LM signups"; fi
if [ -n "$HEAL" ]; then mkdir -p "$(dirname "$REQ")"; printf '{"loop":"reddit","ts":"%s","heal":"%s"}\n' "$(date -u +%FT%TZ)" "${HEAL//\"/}" > "$REQ"; else rm -f "$REQ" 2>/dev/null||true; fi
TMP="$STATE_MD.tmp.$$"
{
  echo "# Reddit demand-gen loop — STATE (feeds life-manager-loop; authentic conversation, NOT broadcast)"
  echo "goal: drive REAL LM signups via genuine community participation (trust, not link-drops). Attributed signup = a real marker only."
  echo "last_wake_utc: $(date -u +%FT%TZ)"
  echo "heal_first: ${HEAL:-account present ✓, CloakBrowser ✓}"
  echo "reddit_accounts: $N_ACCT"
  echo "comment_karma_total: $KARMA"
  echo "prev_comment_karma_total: $PREV"
  echo "attributed_lm_signups: $SIGNUPS"
  echo "status: $STATUS"
  echo "selfheal_request: ${HEAL:+written→$REQ}${HEAL:-none}"
  echo "next: HEAL→self-provision account / start CloakBrowser; WARMING→genuine value-first comments only (agent decides each, no scripts), grow karma; READY→one authentic builder-story + answer questions, never pushy; log any reddit→LM signup to state/attributed-signups.jsonl."
} > "$TMP" && mv "$TMP" "$STATE_MD"
echo "[reddit-loop] accounts=$N_ACCT karma=$KARMA signups=$SIGNUPS | heal=${HEAL:-none} | $STATUS"
