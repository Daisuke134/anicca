#!/usr/bin/env bash
# earn/video — faceless-video earn SLOT entrypoint for the ONE loop (run-skill.mjs spawns this).
# Does EXACTLY ONE bounded state-machine transition per wake (idempotent), prints a one-line JSON
# result on stdout, exit 0. Slot contract: no human, 5-gate + record-earn (real USDC only), bounded.
# The whole faceless-video lifecycle (create→warmup→affiliate-link@day7→post→record) is loop-driven;
# EVERY step incl. the affiliate link is a transition here — never a manual後工程.
set -uo pipefail
SK="$HOME/anicca/skills/earn/video"; PY=/opt/homebrew/bin/python3
# SHARED-1: the free VERIFIED posting path is poster.py (earn/marketing-engine), not the retired
# post_reel.py web composer (structural dead end, IG silently drops automated web posts). It needs
# the instagrapi package, so it always runs under this dedicated venv (self-healed below, shared
# with earn/clip -- never installed into the bare $PY used for this script's own glue logic).
INSTA_VENV="$HOME/.cache/instagrapi-venv"
INSTA_PY="$INSTA_VENV/bin/python"
export PATH="$HOME/.local/bin:$PATH"
# Delegates to the shared helper (anicca-spawn-identity-resolution-fix REQ-003/FIND-001) instead of
# sourcing $HOME/.openclaw/.env directly under `set -a`, which would otherwise clobber this caller's
# per-instance ANICCA_HOME with the automaton's own.
. "$HOME/anicca/skills/_shared/lib/load-instance-env.sh"
TIMEOUT="${SKILL_TIMEOUT_S:-900}"
DRY="${EARN_VIDEO_DRY:-0}"
HANDLE="${EARN_VIDEO_HANDLE:-money_blueprintdaily}"
CREDS="$HOME/.cloak/ig-moneyblueprint.json"          # account creds (tid, email, …)
STATE="$HOME/.cloak/earn-video-${HANDLE}.json"        # slot state (status/warmup_day/…)
LEDGER="$HOME/.cloak/earn-video-ledger.jsonl"
AFFLINK="${MONEY_AFFILIATE_URL:-${MONK_EBOOK_URL:-}}"  # affiliate/ebook link (set in env); empty ⇒ S2 waits
TODAY="$(date +%Y-%m-%d)"
TID="$($PY -c "import json,os;p=os.path.expanduser('$CREDS');print(json.load(open(p)).get('tid','') if os.path.exists(p) else '')" 2>/dev/null)"

# ★ FIND-603/702: load-or-init via state_io — atomic writes + .bak restore. A corrupt/missing primary is restored
#   from .bak (progress preserved), re-init to day-0 only as last resort; never a truncated-write dead-end. ★
$PY -c "import sys;sys.path.insert(0,'$SK');from state_io import load_or_init;load_or_init('$STATE','$HANDLE')"

# ★ D1: refresh affiliate_available from env EVERY wake (re-evaluable; no permanent trap). Atomic via state_io. ★
AVAIL=false; [ -n "$AFFLINK" ] && AVAIL=true
AVAIL="$AVAIL" $PY -c "import os,sys;sys.path.insert(0,'$SK');from state_io import update;update('$STATE',{'affiliate_available':os.environ['AVAIL']=='true'})"

TRANS="$($PY -c "import json,sys;sys.path.insert(0,'$SK');from decide import decide;print(decide(json.load(open('$STATE')),'$TODAY'))" 2>/dev/null)"
[ -z "$TRANS" ] && TRANS="noop"   # ★ FIND-603: decide load failure ⇒ safe noop, never an 'unknown transition' dead-end ★
DID=""; EARNED=0; COST=0

# atomic state update via state_io (tmp+os.replace + .bak) so a kill mid-write can't truncate STATE
set_state(){ $PY -c "import json,sys;sys.path.insert(0,'$SK');from state_io import update;update('$STATE',json.loads(sys.argv[1]))" "$1"; }
wday(){ $PY -c "import json;print(int(json.load(open('$STATE')).get('warmup_day',0)))"; }

# ★ #7 AUDIT LEDGER (P0-3 fix, REQ-LV-070): append every wake's transition + evidence — including
#   EARLY-EXIT branches (warmup deferred, verify-only abort), not just the normal end-of-script
#   path. Root cause of the real 07-02..07-07 warmup stall (day 3 for 6 days straight): the old
#   S1_warmup "deferred" branch (ensure_warmup_browser.py failing) exited BEFORE the audit append
#   at the bottom of this script ever ran, so 6 days of "browser/login not ready" failures were
#   completely invisible in the ledger — every wake after the first just saw
#   last_warmup_date==today and silently no-opped, with zero trace of WHY warmup never advanced.
#   Calling this same function from every exit path makes any future stall diagnosable same-day. ★
AUDIT="$HOME/.cloak/earn-video-audit-${HANDLE}.jsonl"
write_audit(){
  R_HANDLE="$HANDLE" R_TRANS="$TRANS" R_DID="$DID" R_EARNED="$EARNED" R_DATE="$TODAY" R_AUDIT="$AUDIT" $PY -c "import json,os
rec={'date':os.environ['R_DATE'],'handle':os.environ['R_HANDLE'],'transition':os.environ['R_TRANS'],'did':os.environ['R_DID'],'earned_usdc':float(os.environ['R_EARNED'])}
open(os.environ['R_AUDIT'],'a').write(json.dumps(rec,ensure_ascii=False)+'\n')" 2>/dev/null || true
}

case "$TRANS" in
  S1_warmup)
    # REAL warmup in a DEDICATED anti-throttle CloakBrowser (NOT the daily-driver): an occluded reels tab in the
    # daily-driver is visibilityState=hidden → Chrome pauses the video → 0 real views. The dedicated instance is
    # launched with occlusion/throttle/autoplay flags so reels really play while staying out of Dais's way.
    # ★ Dim4: advance warmup_day ONLY when warm_iso REALLY watched >=3 DISTINCT reels (verified playback); never fake. ★
    WATCHED=0; BAN=0
    if [ "$DRY" = 1 ]; then WATCHED=5; else
      WPORT=$($PY -c "import json;print(json.load(open('$CREDS')).get('warmup_cdp_port',9334))" 2>/dev/null)
      WPROF=$($PY -c "import json,os;print(json.load(open('$CREDS')).get('warmup_profile',os.path.expanduser('~/.cloak/profiles/warmup-$HANDLE')))" 2>/dev/null)
      # ★ FIND (2026-07-14): a 1/3-2/3 split (EBUD=73s/WBUD=146s @ TIMEOUT=220) was starving warm_iso —
      #   confirmed live that reaching 3 real distinct niche views can take ~180-190s (candidate hit rate
      #   is low since IG's hashtag-page redirect leaves mostly /p/ image posts), while ensure_warmup_browser
      #   only needs its full budget on the rare day the persisted session gets OTP-challenged again; the
      #   common case (session already logged in) finishes in a few seconds. Shift the split accordingly. ★
      EBUD=$(( TIMEOUT / 6 )); [ "$EBUD" -lt 30 ] && EBUD=30; WBUD=$(( TIMEOUT - EBUD ))   # ensure-browser + warm ≤ TIMEOUT
      WTID=$(timeout "$EBUD" $PY "$HOME/.claude/skills/ig-account-warmer/scripts/ensure_warmup_browser.py" --handle "$HANDLE" --port "$WPORT" --profile "$WPROF" --creds "$CREDS" 2>/tmp/ev_ensure.log | tail -1)
      if [ -z "$WTID" ] || printf '%s' "$WTID" | grep -q ERROR; then
        # ★ FIND-904 fix (2026-07-12): do NOT stamp last_warmup_date here — that poisoned decide()
        #   into "noop" (already warmed today) for every remaining wake THAT SAME DAY, so a single
        #   transient ensure_warmup_browser failure (e.g. the dedicated instance not up yet) silently
        #   burned the entire day's Cadence Contract with zero retries. This is an INFRA precondition
        #   failure, not a real warmup attempt (no reels were watched) — unlike the ban-signal and
        #   too-few-real-views branches below, which DO stamp the date because a real attempt happened
        #   and a same-day retry would just re-trigger the same ban/low-view outcome. Leaving the date
        #   unset here lets decide() re-fire S1_warmup on the next wake instead. ★
        DID="warmup deferred: dedicated browser/login not ready ($(tail -1 /tmp/ev_ensure.log 2>/dev/null|cut -c1-60))"
        write_audit   # ★ P0-3 fix: this failure MUST be visible in the audit ledger, never silently eaten ★
        R_HANDLE="$HANDLE" R_TRANS="$TRANS" R_DID="$DID" $PY -c "import json,os;print(json.dumps({'slot':'earn/video','handle':os.environ['R_HANDLE'],'transition':os.environ['R_TRANS'],'did':os.environ['R_DID'],'earned_usdc':0.0,'cost_usdc':0.0},ensure_ascii=False))"; exit 0
      fi
      # ★ NICHE warmup: watch the content the TARGET audience watches (money/finance) so the account becomes the
      #   persona + the algo learns the niche. Tags configurable per account (AI-agnostic); default = money niche. ★
      NICHE="${EARN_VIDEO_NICHE_TAGS:-personalfinance,investing,moneytips,financetips,moneytok}"
      CDP_PORT="$WPORT" timeout "$WBUD" $PY "$HOME/.claude/skills/ig-account-warmer/scripts/warm_iso.py" --tid "$WTID" --handle "$HANDLE" --reels 6 --niche-tags "$NICHE" >/tmp/ev_warm.log 2>&1 || true
      # ★ FIND-901: warm_iso.py's final JSON summary line only prints on clean exit — a `timeout $WBUD` SIGTERM
      #   mid-candidate-loop kills it first, discarding real progress already logged. Fall back to counting the
      #   "REAL DISTINCT" log lines it already flushed, so a truncated-but-real warmup still counts. ★
      WATCHED=$($PY -c "import json,sys
try:
  for l in open('/tmp/ev_warm.log'):
    l=l.strip()
    if l.startswith('{') and 'reels_watched_real' in l: print(json.loads(l)['reels_watched_real']); break
  else:
    print(sum(1 for l in open('/tmp/ev_warm.log') if 'REAL DISTINCT' in l))
except: print(0)" 2>/dev/null)
      grep -q "STOP_BAN_SIGNAL" /tmp/ev_warm.log 2>/dev/null && BAN=1
    fi
    if [ "$BAN" = 1 ]; then
      # ★ FIND-703: on ban, mark today done so decide does NOT re-drive a banned account every wake (per-day backoff). Day NOT advanced. ★
      set_state "{\"last_warmup_date\": \"$TODAY\", \"ban_signal_date\": \"$TODAY\"}"
      DID="warmup STOPPED: ban signal — NOT advancing day; backing off for today";
    elif [ "${WATCHED:-0}" -ge 3 ]; then
      set_state "{\"warmup_day\": $(( $(wday) + 1 )), \"last_warmup_date\": \"$TODAY\", \"status\": \"warming\"}"
      DID="warmup day→$(wday) (real reels watched=$WATCHED)"
    else
      set_state "{\"last_warmup_date\": \"$TODAY\"}"   # mark attempt today (idempotent) but do NOT advance day on too-few real views
      DID="warmup INCOMPLETE: only $WATCHED real views (<3) — day NOT advanced"
    fi ;;
  S2_affiliate)
    # ★ D1 round-2 fix: decide returns S2 ONLY when affiliate_available (AFFLINK set), so the install is reachable. ★
    # ★ FIND-402 fix: set affiliate_set=true ONLY after setup_profile VERIFIES the website persisted (website_set==true).
    #   On failure, leave affiliate_set=false so decide re-fires S2 next wake (never lie that the link is installed). ★
    if [ -z "$AFFLINK" ]; then
      DID="S2 reached with empty AFFLINK (unexpected) — no-op; decide routes to post next wake"   # defensive only
    elif [ "$DRY" = 1 ]; then
      set_state '{"affiliate_set": true, "status": "warmed"}'; DID="[DRY] affiliate link would be set: $AFFLINK"
    else
      timeout "$TIMEOUT" $PY "$HOME/.claude/skills/ig-account-create/scripts/setup_profile.py" --tid "$TID" --website "$AFFLINK" --username "$HANDLE" >/tmp/ev_aff.log 2>&1 || true
      WSET=$($PY -c "import json
ok=False
try:
  for l in open('/tmp/ev_aff.log'):
    l=l.strip()
    if l.startswith('{') and 'website_set' in l:
      ok = json.loads(l).get('website_set') is True
except: ok=False
print('1' if ok else '0')" 2>/dev/null)
      # ★ FIND-801: stamp affiliate_attempt_date EITHER way so S2 retries at most once/day and never starves S4_record. ★
      if [ "$WSET" = 1 ]; then set_state "{\"affiliate_set\": true, \"status\": \"warmed\", \"affiliate_attempt_date\": \"$TODAY\"}"; DID="affiliate link VERIFIED+set (post-warmup): $AFFLINK"
      else set_state "{\"status\": \"warmed\", \"affiliate_attempt_date\": \"$TODAY\"}"; DID="affiliate set FAILED (not verified) — affiliate_set stays false, S2 retries tomorrow; S4 records today"; fi
    fi ;;
  S3_post)
    OUT="$HOME/.claude/skills/faceless-money-factory/state/renders"
    VFYBUD=$(( TIMEOUT / 10 )); GENBUD=$(( TIMEOUT * 4 / 10 )); POSTBUD=$(( TIMEOUT * 3 / 10 ))   # ★ FIND-604: sum=0.8×TIMEOUT, headroom for glue/writes so kills are exceptional, not the norm ★
    PR="$HOME/anicca/skills/earn/marketing-engine/poster.py"
    IG_PORT=9222
    if [ ! -x "$INSTA_PY" ]; then
      /opt/homebrew/bin/python3 -m venv "$INSTA_VENV" >/tmp/ev-insta-venv.log 2>&1
      "$INSTA_PY" -m pip install --quiet instagrapi websocket-client pillow >/tmp/ev-insta-pip.log 2>&1 || true
    fi
    if [ "$DRY" = 1 ]; then
      timeout "$GENBUD" bash "$HOME/.claude/skills/faceless-money-factory/scripts/run-daily.sh" "${EARN_VIDEO_SCRIPT:-$OUT/today.txt}" en >/dev/null 2>&1 || true
      set_state "{\"last_post_date\": \"$TODAY\", \"status\": \"warmed\", \"post_attempt_date\": \"$TODAY\"}"; DID="[DRY] would post reel"
    else
      # ★ FIND (2026-07-15): the (ctx, tid) pair in $CREDS is an ISOLATED incognito browserContext on the
      #   daily-driver, created once at account-creation time — it's memory-only and vanishes on any
      #   daily-driver restart, after which post_reel.py's CDP handshake fails with "No such target id"
      #   and this whole stage aborted silently forever (verify-only "unauthoritative" every wake). Refresh
      #   it first: idempotent/fast when the stored tid is still live+logged-in, only recreates+relogs in
      #   when the context is actually gone. On failure (OTP/captcha not solved this attempt) keeps the old
      #   TID so the pre-existing "unauthoritative → abort, retry next wake" safety below still applies. ★
      EPC_BUD=$(( TIMEOUT / 6 )); [ "$EPC_BUD" -lt 30 ] && EPC_BUD=30
      EPC_OUT=$(timeout "$EPC_BUD" $PY "$HOME/.claude/skills/ig-reels-poster/scripts/ensure_post_context.py" --port "$IG_PORT" --creds "$CREDS" 2>/tmp/ev_postctx.log | tail -1)
      if [ -n "$EPC_OUT" ] && ! printf '%s' "$EPC_OUT" | grep -q ERROR; then TID="$EPC_OUT"; fi
      # ★ FIND-502 fix: ONE verify-only call serves BOTH (a) reconcile — if a prior attempt TODAY was timeout-killed
      #   AFTER シェア (post_attempt_date==today, last_post_date unset) and a reel appeared that wasn't in pre_reels,
      #   that post DID land → set last_post_date, DO NOT double-post; AND (b) snapshot pre_reels for THIS attempt.
      # SHARED-1 (INV-4): reads via poster.py --verify-only (instagrapi API), not the
      # retired post_reel.py browser-DOM read. ensure_post_context.py above still keeps the
      # daily-driver tab logged in as the tier2 sessionid fallback inside login_resilient(). ★
      timeout "$VFYBUD" env CDP_PORT="$IG_PORT" "$INSTA_PY" "$PR" --handle "$HANDLE" --port "$IG_PORT" --verify-only >/tmp/ev_vfy.log 2>&1 || true
      # ★ FIND-601: parse VOK (authoritative success) + CUR (reels, compact JSON, no spaces). VOK=1 ONLY when the
      #   verify_only line had ok==true. A failed/aborted verify (not-logged-in, account-guard None, timeout) → VOK=0. ★
      read VOK CUR < <($PY -c "import json
ok='0'; r='[]'
try:
  for l in open('/tmp/ev_vfy.log'):
    l=l.strip()
    if l.startswith('{') and 'verify_only' in l:
      d=json.loads(l)
      if d.get('ok') is True: ok='1'; r=json.dumps(d.get('reels') or [], separators=(',',':'))
except: ok='0'; r='[]'
print(ok, r)" 2>/dev/null)
      if [ "${VOK:-0}" != 1 ]; then
        # ★ FIND-601: verify-only NOT authoritative → ABORT this wake. NEVER treat a failed read as '0 reels' (that
        #   would miss reconcile AND overwrite pre_reels=[] → double-post). Leave state untouched; retry next wake. ★
        DID="verify-only failed/unauthoritative — aborting wake to avoid double-post (retry next wake)"
        write_audit   # ★ P0-3 fix: same observability fix — an abort must not be silently invisible either ★
        R_HANDLE="$HANDLE" R_TRANS="$TRANS" R_DID="$DID" $PY -c "import json,os;print(json.dumps({'slot':'earn/video','handle':os.environ['R_HANDLE'],'transition':os.environ['R_TRANS'],'did':os.environ['R_DID'],'earned_usdc':0.0,'cost_usdc':0.0},ensure_ascii=False))"
        exit 0
      fi
      NEWURL=$(STATE="$STATE" TODAY="$TODAY" CUR="$CUR" $PY -c "import json,os
new=''
try:
  s=json.load(open(os.environ['STATE']))
  if s.get('post_attempt_date')==os.environ['TODAY'] and s.get('last_post_date')!=os.environ['TODAY']:
    pre=set(s.get('pre_reels') or []); cur=json.loads(os.environ['CUR'])
    fresh=[h for h in cur if h not in pre]
    if fresh: new='https://www.instagram.com'+fresh[0]
except: new=''
print(new)" 2>/dev/null)
      if [ -n "$NEWURL" ]; then
        set_state "{\"last_post_date\": \"$TODAY\", \"status\": \"warmed\", \"last_post_url\": \"$NEWURL\"}"
        # ★ FIND-D2-01: a RECONCILED real post must ALSO enter the eval loop (link post↔script), else it's invisible to self-improvement ★
        $PY -c "import sys;sys.path.insert(0,'$SK');import selfimprove as S;S.record_post('$HANDLE','$NEWURL', open('${EARN_VIDEO_SCRIPT:-$OUT/today.txt}').read() if __import__('os').path.exists('${EARN_VIDEO_SCRIPT:-$OUT/today.txt}') else '', '$TODAY')" 2>/dev/null || true
        DID="reconciled prior timeout-killed post (already live, no double-post): $NEWURL"
      else
        # snapshot pre_reels for THIS attempt (ATOMIC via state_io; so a timeout-kill is reconciled next wake) + mark attempt date
        CUR="$CUR" $PY -c "import json,os,sys;sys.path.insert(0,'$SK');from state_io import update;update('$STATE',{'pre_reels':json.loads(os.environ['CUR']),'post_attempt_date':'$TODAY'})"
        # ★ FIND-701: require a FRESH render. Stamp GEN_START, then accept ONLY an mp4 whose mtime >= GEN_START.
        #   A failed/killed generation that leaves a stale prior-day render must NOT be posted as today's fresh reel. ★
        GEN_START=$(date +%s)
        timeout "$GENBUD" bash "$HOME/.claude/skills/faceless-money-factory/scripts/run-daily.sh" "${EARN_VIDEO_SCRIPT:-$OUT/today.txt}" en >/tmp/ev_gen.log 2>&1 || true
        # ★ FIND-803: fresh (mtime>=GEN_START) AND non-trivial size (>100KB) — a partial mp4 from a timeout-killed
        #   gen would otherwise be selected and waste a posting attempt. Min-size filters obvious truncations. ★
        MP4="$(GEN_START="$GEN_START" OUT="$OUT" $PY -c "import os,glob
gs=float(os.environ['GEN_START']); out=os.environ['OUT']
c=[f for f in glob.glob(os.path.join(out,'*.mp4')) if os.path.getmtime(f)>=gs and os.path.getsize(f)>100000]
c.sort(key=os.path.getmtime, reverse=True)
print(c[0] if c else '')" 2>/dev/null)"
        if [ -n "$MP4" ]; then
          printf 'Daily money tips. Follow @%s for more. #moneytok #personalfinance\n' "$HANDLE" > /tmp/ev_cap.txt
          # ★ FIND-001: account is warmed (warmup_day>=7) → post LIVE (affiliate link optional for posting).
          # SHARED-1 (INV-1/INV-2): publishes via poster.py --live (the verified-free path), not
          # the retired post_reel.py web composer. ★
          timeout "$POSTBUD" env CDP_PORT="$IG_PORT" "$INSTA_PY" "$PR" --video "$MP4" --caption-file /tmp/ev_cap.txt --handle "$HANDLE" --port "$IG_PORT" --live >/tmp/ev_post.log 2>&1 || true
          # ★ FIND-401 (adapted, SHARED-1 INV-2): mark posted ONLY when poster.py VERIFIES
          #   outcome=="published" AND non-empty post_url; else leave last_post_date unset → retry, report REAL failure. ★
          PURL=$($PY -c "import json
u=''
try:
  for l in open('/tmp/ev_post.log'):
    l=l.strip()
    if l.startswith('{') and 'outcome' in l:
      d=json.loads(l)
      if d.get('outcome')=='published' and d.get('post_url'): u=d['post_url']
except: u=''
print(u)" 2>/dev/null)
          if [ -n "$PURL" ]; then set_state "{\"last_post_date\": \"$TODAY\", \"status\": \"warmed\", \"last_post_url\": \"$PURL\"}"; DID="posted reel LIVE: $PURL"
            # ★ self-improve: link this post_url ↔ the script that made it, so metrics can be attributed to the script ★
            $PY -c "import sys;sys.path.insert(0,'$SK');import selfimprove as S;S.record_post('$HANDLE','$PURL', open('${EARN_VIDEO_SCRIPT:-$OUT/today.txt}').read() if __import__('os').path.exists('${EARN_VIDEO_SCRIPT:-$OUT/today.txt}') else '', '$TODAY')" 2>/dev/null || true
          else set_state '{"status": "warmed"}'; DID="post FAILED/unverified ($(tail -1 /tmp/ev_post.log 2>/dev/null|cut -c1-80)) — last_post_date NOT set, will retry/reconcile next wake"; fi
        else DID="post skipped: no FRESH mp4 from this wake's generation ($(tail -1 /tmp/ev_gen.log 2>/dev/null|cut -c1-50)) — honest skip, NOT posting a stale render"; fi
      fi
    fi ;;
  S4_record)
    # ★ ②③ REAL: onchain.detect() scans Base for USDC inflows to the founder/ChangeNOW-payout wallet and appends
    #   them to INFLOWS; then record_earn records each, RE-CONFIRMED on-chain via onchain.confirm_usdc_inflow
    #   (fail-closed: a spoofed inflows line that isn't a real matching transfer is rejected). Records only real money. ★
    REC=$(LEDGER="$LEDGER" timeout 60 $PY -c "
import json,os,sys,io,contextlib
sys.path.insert(0,'$SK')
from record_earn import record_earn
from onchain import confirm_usdc_inflow, INFLOWS, detect
try:
  with contextlib.redirect_stdout(io.StringIO()): detect()   # scan chain → append new confirmed inflows (suppress its print)
except Exception: pass
led=os.environ['LEDGER']; n=0.0; c=0
if os.path.exists(INFLOWS):
  for l in open(INFLOWS):
    l=l.strip()
    if not l: continue
    try: e=json.loads(l)
    except: continue
    st,val=record_earn(e,led,onchain_check=confirm_usdc_inflow)   # ← REAL on-chain re-verify, not the False stub
    if st=='recorded': n+=float(val); c+=1
print(json.dumps({'recorded_count':c,'recorded_usdc':n}))" 2>/dev/null)
    [ -z "$REC" ] && REC='{"recorded_count":0,"recorded_usdc":0}'
    EARNED=$($PY -c "import json;print(json.loads('''$REC''').get('recorded_usdc',0))" 2>/dev/null || echo 0)
    # ★ self-improve MEASURE: on a logged-in tab of the dedicated browser, measure recent posts' views/likes so the
    #   agent can see what works. Bounded; best-effort (no post yet ⇒ nothing). ★
    if [ "$DRY" != 1 ]; then
      WPORT=$($PY -c "import json;print(json.load(open('$CREDS')).get('warmup_cdp_port',9334))" 2>/dev/null)
      MTID=$(curl -s --max-time 4 "http://localhost:$WPORT/json" 2>/dev/null | $PY -c "import json,sys
try:
  t=[x for x in json.load(sys.stdin) if x.get('type')=='page' and 'instagram' in x.get('url','')]
  print(t[0]['id'] if t else '')
except: print('')" 2>/dev/null)
      [ -n "$MTID" ] && timeout 45 $PY "$SK/selfimprove.py" measure --handle "$HANDLE" --tid "$MTID" --port "$WPORT" --date "$TODAY" >/dev/null 2>&1 || true
    fi
    set_state '{"status": "monetized"}'
    DID="record-earn (onchain): $REC" ;;
  noop) DID="noop (already warmed today)" ;;
  S0_create)
    # one-time bootstrap (0-human via ig-account-create+setup_profile, proven). Not a per-wake human step.
    DID="bootstrap: account not created yet — ig-account-create (0-human) runs once, then S1–S4 loop takes over" ;;
  *) DID="unknown transition: $TRANS" ;;
esac

# ★ #7 AUDIT LEDGER: append every wake's transition + evidence (append-only) so warmup/posts are PROVABLY recorded,
#   not faked — a per-day trail anyone can inspect. (Early-exit branches above call the same write_audit — P0-3.) ★
write_audit

# ★ Dim5 fix: emit valid one-line JSON via json.dumps (escapes any "/\ in DID from logs) ★
R_HANDLE="$HANDLE" R_TRANS="$TRANS" R_DID="$DID" R_EARNED="$EARNED" R_COST="$COST" $PY -c "import json,os;print(json.dumps({'slot':'earn/video','handle':os.environ['R_HANDLE'],'transition':os.environ['R_TRANS'],'did':os.environ['R_DID'],'earned_usdc':float(os.environ['R_EARNED']),'cost_usdc':float(os.environ['R_COST'])},ensure_ascii=False))"
exit 0
