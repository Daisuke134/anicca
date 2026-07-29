#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
# auditor.sh — INDEPENDENT verification that the gig loop self-runs (master-spec AUDITOR, gig-scoped).
# Runs via its OWN launchd (hourly at :45, offset from the core's :27 cron), so it observes the loop
# WITHOUT the main session and WITHOUT being the core. Each run it answers, from the files the core
# writes, three questions and appends one verdict line to ~/gig/audit.jsonl:
#   (a) IS IT FIRING?      heartbeat ~/gig/.last-pass age < 90min  → the in-session :27 cron is alive
#   (b) IS IT PROGRESSING? applied.jsonl / earnings.jsonl grew since the last audit (real work happening)
#   (c) IS IT EARNING?     any settled (検収/支払 + evidence) ¥ row (deterministic guard, no fake)
# It also flags STALE (cron stopped though tmux alive) and DEAD (tmux gone) so a human/監視 can see at a
# glance whether the autonomous loop is genuinely working. It takes NO action on Coconala (read-only).
set -uo pipefail
G="$HOME/gig"; AUDIT="$G/audit.jsonl"; HB="$G/.last-pass"
SOCK="/tmp/anicca-gig-tmux.sock"; SESSION="anicca-gig-core"
PY=/opt/homebrew/bin/python3
alive=0; tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && alive=1

"$PY" - "$G" "$AUDIT" "$HB" "$alive" <<'PY'
import json,sys,os,time
G,AUDIT,HB,alive=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]=="1"
def jnum(v):
    try: return float(str(v).replace(',','').replace('¥','').replace('円','').strip() or 0)
    except Exception: return 0.0
def rows(f):
    p=os.path.join(G,f); out=[]
    if os.path.exists(p):
        for l in open(p):
            l=l.strip()
            if l:
                try: out.append(json.loads(l))
                except: pass
    return out
all_rows=rows("applied.jsonl")
applied=[r for r in all_rows if r.get("status")=="applied"]  # FIND-006: align with run/monitor
SETTLED={"検収","支払","検収完了","completed","paid"}
earned=[r for r in rows("earnings.jsonl") if r.get("status") in SETTLED and r.get("evidence") and jnum(r.get("jpy",0))>0]
jpy=sum(jnum(r.get("jpy",0)) for r in earned)
hb_age=int((time.time()-os.path.getmtime(HB))/60) if os.path.exists(HB) else None
# last audit for deltas — FIND-R2-004: guard first row (no prev actions_total → delta=0, progressing=false)
prev=rows("audit.jsonl")
prev_last=prev[-1] if prev else {}
prev_actions=prev_last.get("actions_total")  # None if first audit row
if prev_actions is None:
    actions_delta=0
    progressing=False
else:
    actions_delta=len(all_rows)-prev_actions
    progressing=actions_delta>0 or jpy>0
# verdict
if not alive: verdict="DEAD (tmux gone — healthcheck should restart)"
elif hb_age is None: verdict="NO_HEARTBEAT (no pass yet)"
elif hb_age>=90: verdict="STALE (no pass in %dmin — in-session cron likely stopped; healthcheck should restart)"%hb_age
else: verdict="FIRING (last pass %dmin ago)"%hb_age
row={"ts":int(time.time()),"verdict":verdict,"core_alive":alive,"heartbeat_age_min":hb_age,
     "applied_total":len(applied),"actions_total":len(all_rows),"actions_delta_since_last_audit":actions_delta,
     "earn_rows":len(earned),"jpy_earned":round(jpy,0),
     "progressing": progressing}
os.makedirs(G,exist_ok=True)
open(AUDIT,"a").write(json.dumps(row,ensure_ascii=False)+"\n")
print(json.dumps(row,ensure_ascii=False))
PY

# ─── reality-verifier (feature gig-reality-verify, 増分2b) ────────────────────────────────────────
# AFTER the deterministic verdict above (never before — the deterministic audit is the pre-existing
# safety net and must not be blocked by this). Spawns a FRESH, report-independent `claude -p` judge
# that navigates the REAL Coconala screens and judges the core's jsonl claims report-skeptically
# (docs/loop-engineering/26-gig-loop-asis-tobe-plan.md §8, BP=25). Missing/non-executable script must
# never abort this audit run.
REALITY_VERIFY="$(dirname "${BASH_SOURCE[0]}")/gig_reality_verify.sh"
if [ -x "$REALITY_VERIFY" ]; then
  bash "$REALITY_VERIFY" >/dev/null 2>>"$G/.reality-verify.err.log" || true
fi

# ─── self-heal wire (gig L1-a) ────────────────────────────────────────────────────────────────────
# If the reality-verifier just wrote a self-heal request (verdict:false = the core's jsonl claims did
# NOT match the real Coconala UI), hand it to the dedicated autonomous fixer self-fix.sh (a fresh
# Sonnet with browser+Bash+Edit that diagnoses the root cause, fixes the code, and commits — no human).
# Then remove the request so it dispatches exactly once per discrepancy. self-fix.sh self-guards
# against duplicate/hung fixers, so a second hourly run while a fixer is live is a safe no-op.
SELFHEAL_REQ="$HOME/.local/state/life-manager/state/.gig-core-selfheal-request.json"
SELF_FIX="$LIFE_MANAGER_REPO/skills/self/self-fix.sh"
# AUTH-WALL COOLDOWN (2026-07-13 self-fix, gh#1015): kind=auth_wall means the reality-verifier hit a
# login wall (reached_captcha=true) -- an external/session precondition (Coconala logged out, iPhone
# Bluetooth 2FA relay down), NOT a code bug. Before this fix, every hourly audit pass respawned a full
# self-fix.sh Sonnet agent to "find why claim != reality and fix the code" for a condition that never
# changes without Dais physically toggling Bluetooth -- confirmed from audit-reality.jsonl: 5 of the
# last 6 reality-verify rounds set reached_captcha=true yet still wrote the generic selfheal-request,
# and self-fix.sh has no cross-invocation memory once a prior fixer already exited. kind=claim_mismatch
# (the judge DID reach the real screen and the claim genuinely did not hold) is unthrottled, unchanged.
AUTH_WALL_COOLDOWN_MARKER="$G/.auth-wall-selfheal-cooldown"
AUTH_WALL_COOLDOWN_SECS=21600  # 6h: re-alert periodically without spawning a fresh agent every hour
# TIMEOUT COOLDOWN (2026-07-15 self-fix, incident realityverify-1784123104-80599): same shape as the
# auth_wall cooldown above. kind=timeout means the fresh judge spawn itself never finished investigating
# within the cap (gig_reality_verify.sh's own `timeout` killed it) -- there was no claim/reality mismatch
# to diagnose, the verifier just ran out of time on a legitimately heavy round (many distinct entities/
# talkrooms to check). The 2026-07-15 fix already addresses the root cause (entity dedup + raised cap),
# but a hung/overloaded round could still recur before that fix is fully proven out; without this
# cooldown a recurring timeout would respawn a full self-fix.sh Sonnet agent every single hour forever.
TIMEOUT_COOLDOWN_MARKER="$G/.timeout-selfheal-cooldown"
TIMEOUT_COOLDOWN_SECS=21600  # 6h: same window as auth_wall
if [ -f "$SELFHEAL_REQ" ] && [ -x "$SELF_FIX" ]; then
  KIND="$(python3 -c "import json;print(json.load(open('$SELFHEAL_REQ')).get('kind','claim_mismatch'))" 2>/dev/null || echo 'claim_mismatch')"
  REASON="$(python3 -c "import json;print(json.load(open('$SELFHEAL_REQ')).get('reason','') or json.load(open('$SELFHEAL_REQ')).get('failure_reason',''))" 2>/dev/null || echo '')"
  [ -z "$REASON" ] && REASON="reality-verifier could not confirm the gig core's reported 出品/応募/納品 on the real Coconala pages"
  SKIP_SELFHEAL=0
  if [ "$KIND" = "auth_wall" ]; then
    cooldown_age=999999
    [ -f "$AUTH_WALL_COOLDOWN_MARKER" ] && cooldown_age=$(( $(date +%s) - $(cat "$AUTH_WALL_COOLDOWN_MARKER" 2>/dev/null || echo 0) ))
    if [ "$cooldown_age" -lt "$AUTH_WALL_COOLDOWN_SECS" ]; then
      SKIP_SELFHEAL=1
      echo "$(date '+%F %T') auditor: auth_wall selfheal within cooldown (${cooldown_age}s<${AUTH_WALL_COOLDOWN_SECS}s) -- skip self-fix.sh spawn (already diagnosed)" >> "$G/.self-fix.err.log"
    else
      date +%s > "$AUTH_WALL_COOLDOWN_MARKER"
    fi
  elif [ "$KIND" = "timeout" ]; then
    cooldown_age=999999
    [ -f "$TIMEOUT_COOLDOWN_MARKER" ] && cooldown_age=$(( $(date +%s) - $(cat "$TIMEOUT_COOLDOWN_MARKER" 2>/dev/null || echo 0) ))
    if [ "$cooldown_age" -lt "$TIMEOUT_COOLDOWN_SECS" ]; then
      SKIP_SELFHEAL=1
      echo "$(date '+%F %T') auditor: timeout selfheal within cooldown (${cooldown_age}s<${TIMEOUT_COOLDOWN_SECS}s) -- skip self-fix.sh spawn (already diagnosed)" >> "$G/.self-fix.err.log"
    else
      date +%s > "$TIMEOUT_COOLDOWN_MARKER"
    fi
  fi
  if [ "$SKIP_SELFHEAL" = "0" ]; then
    bash "$SELF_FIX" gig "reality-verify FAIL: ${REASON}. The gig core reported side-effects the fresh reality-verifier could NOT confirm on the real Coconala UI. Find why claim != reality and fix the code so future claims are backed by real on-page state." >/dev/null 2>>"$G/.self-fix.err.log" || true
  fi
  rm -f "$SELFHEAL_REQ"
fi
