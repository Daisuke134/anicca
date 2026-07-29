#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; runtime dependencies live in homebrew
# auditor.sh — INDEPENDENT verification that the gig loop self-runs (master-spec AUDITOR, gig-scoped).
# Runs via its OWN launchd (hourly at :45, offset from the core's :27 cron), so it observes the loop
# WITHOUT the main session and WITHOUT being the core. Each run it answers, from the files the core
# writes, three questions and appends one verdict line to ~/gig/audit.jsonl:
#   (a) IS IT FIRING?      heartbeat ~/gig/.last-pass age < 90min  → the in-session :27 cron is alive
#   (b) IS IT PROGRESSING? applied.jsonl / earnings.jsonl grew since the last audit (real work happening)
#   (c) IS IT EARNING?     any settled (検収/支払 + evidence) ¥ row (deterministic guard, no fake)
# It also flags STALE (cron stopped though tmux alive) and DEAD (tmux gone). The
# bounded healer may restart isolated infrastructure or non-killing kickstart the
# pass, but it never performs a customer-facing marketplace action itself.
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
# safety net and must not be blocked by this). Spawns a fresh, report-independent judge
# that navigates the REAL Coconala screens and judges the core's jsonl claims report-skeptically
# (docs/loop-engineering/26-gig-loop-asis-tobe-plan.md §8, BP=25). Missing/non-executable script must
# never abort this audit run.
REALITY_VERIFY="$(dirname "${BASH_SOURCE[0]}")/gig_reality_verify.sh"
REALITY_VERIFY_INTERVAL_SECS="${GIG_REALITY_VERIFY_INTERVAL_SECS:-21600}"
REALITY_VERIFY_MARKER="$G/.reality-verify-last-start"
REALITY_VERIFY_NOW="$(date +%s)"
REALITY_VERIFY_LAST=0
if [ -f "$REALITY_VERIFY_MARKER" ]; then
  REALITY_VERIFY_LAST="$(cat "$REALITY_VERIFY_MARKER" 2>/dev/null || echo 0)"
fi
case "$REALITY_VERIFY_LAST" in (*[!0-9]*|'') REALITY_VERIFY_LAST=0 ;; esac
if [ -x "$REALITY_VERIFY" ] && [ $(( REALITY_VERIFY_NOW - REALITY_VERIFY_LAST )) -ge "$REALITY_VERIFY_INTERVAL_SECS" ]; then
  printf '%s\n' "$REALITY_VERIFY_NOW" > "$REALITY_VERIFY_MARKER"
  bash "$REALITY_VERIFY" >/dev/null 2>>"$G/.reality-verify.err.log" || true
else
  echo "$(date '+%F %T') auditor: deterministic audit complete; reality judge not due" >> "$G/.reality-verify.err.log"
fi

# ─── self-heal wire (gig L1-a) ────────────────────────────────────────────────────────────────────
# If the reality-verifier just wrote a self-heal request (verdict:false = the core's jsonl claims did
# NOT match the real Coconala UI), hand it to the dedicated autonomous fixer self-fix.sh (a fresh
# Sonnet with browser+Bash+Edit that diagnoses the root cause, fixes the code, and commits — no human).
# Then remove the request so it dispatches exactly once per discrepancy. self-fix.sh self-guards
# against duplicate/hung fixers, so a second hourly run while a fixer is live is a safe no-op.
SELFHEAL_REQ="$HOME/.openclaw/state/.gig-core-selfheal-request.json"
SELF_FIX="$HOME/anicca/skills/self/self-fix.sh"
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
# JUDGE-KILLED COOLDOWN (2026-07-19 self-fix, incident realityverify-1784457900-26730 and 2 more same
# hour): kind=judge_process_killed means gig_reality_verify.sh's fresh judge spawn got SIGKILLed by
# macOS (jetsam) before it could navigate anything -- host memory/swap exhaustion (confirmed live:
# ~67MB free RAM, 727MB free swap, 89 concurrent claude processes at incident time), NOT a claim/
# reality mismatch. Same shape as auth_wall/timeout: without this cooldown, every hourly audit pass
# would spawn ANOTHER full self-fix.sh Sonnet agent to "find the code bug" for a condition that (a)
# isn't a code bug and (b) gets WORSE every time we spawn one more claude process onto an already
# starved host.
JUDGE_KILLED_COOLDOWN_MARKER="$G/.judge-killed-selfheal-cooldown"
JUDGE_KILLED_COOLDOWN_SECS=21600  # 6h: same window as auth_wall/timeout
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
  elif [ "$KIND" = "judge_process_killed" ]; then
    cooldown_age=999999
    [ -f "$JUDGE_KILLED_COOLDOWN_MARKER" ] && cooldown_age=$(( $(date +%s) - $(cat "$JUDGE_KILLED_COOLDOWN_MARKER" 2>/dev/null || echo 0) ))
    if [ "$cooldown_age" -lt "$JUDGE_KILLED_COOLDOWN_SECS" ]; then
      SKIP_SELFHEAL=1
      echo "$(date '+%F %T') auditor: judge_process_killed selfheal within cooldown (${cooldown_age}s<${JUDGE_KILLED_COOLDOWN_SECS}s) -- skip self-fix.sh spawn (host resource exhaustion, already diagnosed)" >> "$G/.self-fix.err.log"
    else
      date +%s > "$JUDGE_KILLED_COOLDOWN_MARKER"
    fi
  fi
  if [ "$SKIP_SELFHEAL" = "0" ]; then
    bash "$SELF_FIX" gig "reality-verify FAIL: ${REASON}. The gig core reported side-effects the fresh reality-verifier could NOT confirm on the real Coconala UI. Find why claim != reality and fix the code so future claims are backed by real on-page state." >/dev/null 2>>"$G/.self-fix.err.log" || true
  fi
  rm -f "$SELFHEAL_REQ"
fi

# (d) ARE OPEN THREADS STILL OBSERVED? (C3, 2026-07-27)
# Checks (a)-(c) prove the pass fires, progresses and earns, but none of them notice
# if a single OPEN talkroom silently stops being polled -- and an unobserved open
# thread means missed buyer messages, which is the expensive failure. Closed rooms are
# excluded by construction (the open set comes from the marketplace snapshot), so a
# room going quiet after it closes is not flagged. Read-only, appends one row.
GIG_FRESHNESS_MAX_AGE_MIN="${GIG_FRESHNESS_MAX_AGE_MIN:-60}"
freshness_row="$("$PY" "$(dirname "$0")/scripts/thread_freshness.py" \
  --max-age-min "$GIG_FRESHNESS_MAX_AGE_MIN" 2>/dev/null)" || freshness_row=""
if [ -n "$freshness_row" ]; then
  printf '%s\n' "$freshness_row" >> "$AUDIT"
  case "$freshness_row" in
    *'"verdict": "STALE'*)
      echo "$(date '+%F %T') auditor: open talkroom(s) unobserved > ${GIG_FRESHNESS_MAX_AGE_MIN}min -- reply detector may be stalled" >> "$G/.self-fix.err.log"
      ;;
  esac
fi

# (e) IS EACH LANE PRODUCTIVE? (2026-07-27)
# Checks (a)-(d) all pass while a lane silently does nothing: (a) watches one global
# heartbeat, (b) sums applied.jsonl across every lane so a working lane masks a dead one,
# and a run that succeeds having done zero work looks identical to a healthy one. That is
# how applications stopped for 4.5 days unnoticed. This reads the per-lane clocks --
# last success AND last real work -- and appends one row per evaluation.
# check exits 1 when any lane is down, which is a verdict and not an error -- capture the
# output either way. Guarding with || here silently discarded exactly the rows we need.
lane_row="$("$PY" "$(dirname "$0")/scripts/lane_health.py" check --json 2>/dev/null)"
if [ -n "$lane_row" ]; then
  printf '%s\n' "$lane_row" >> "$AUDIT"
  # Only announce transitions; lane_health already suppresses unchanged states.
  changed="$(printf '%s' "$lane_row" | "$PY" -c 'import json,sys
try:
    rows = json.load(sys.stdin).get("changed") or []
except Exception:
    rows = []
print("; ".join(f"{r[\"lane\"]}->{r[\"to\"]} ({\", \".join(r.get(\"problems\") or [])})" for r in rows))' 2>/dev/null)"
  if [ -n "$changed" ]; then
    echo "$(date '+%F %T') auditor: lane status changed -- $changed" >> "$G/.self-fix.err.log"
  fi
fi

# (f) CANONICAL SLO + TRANSACTIONAL REPAIR QUEUE (G3)
# Each control-plane surface is evaluated independently: a healthy scheduler cannot
# mask one dead revenue lane, and a sent pass report cannot erase an older
# delivery_unknown. Incidents are coalesced by fingerprint in SQLite and remain there
# until a fenced healer records fresh verification. Detection never performs a
# customer-facing retry.
slo_row="$("$PY" "$(dirname "$0")/scripts/gig_slo.py" \
  --state-dir "$G" \
  --host-state-dir "$HOME/.openclaw/state" \
  --telegram-database "$G/telegram-outbox.sqlite3" \
  --repair-database "$G/gig-control.sqlite3" 2>>"$G/.gig-slo.err.log")" || slo_row=""
if [ -n "$slo_row" ]; then
  printf '%s\n' "$slo_row" >> "$AUDIT"
  slo_count="$(printf '%s' "$slo_row" | "$PY" -c 'import json,sys
try:
    print(int(json.load(sys.stdin).get("incident_count", 0)))
except Exception:
    print(-1)' 2>/dev/null)"
  if [ "${slo_count:--1}" -gt 0 ]; then
    echo "$(date '+%F %T') auditor: ${slo_count} SLO incident(s) persisted in gig-control.sqlite3" >> "$G/.self-fix.err.log"
  fi
fi

# (g) FENCED RECONCILIATION CONTROLLER (D3)
# Claim one incident, re-observe current state, request only an allowlisted
# deterministic repair, then re-observe again. launchctl success alone is never
# recovery. Persistent fingerprints remain nonterminal in the queue with bounded
# exponential backoff; unknown classes are blocked behind canary/rollback.
HEAL_CONTROLLER="$(cd "$(dirname "$0")/../.." && pwd)/src/gig/healing/controller.py"
healer_row="$("$PY" "$HEAL_CONTROLLER" \
  --state-dir "$G" \
  --host-state-dir "$HOME/.openclaw/state" \
  --telegram-database "$G/telegram-outbox.sqlite3" \
  --repair-database "$G/gig-control.sqlite3" \
  --audit "$AUDIT" 2>>"$G/.gig-healer.err.log")" || healer_row=""
if [ -n "$healer_row" ]; then
  echo "$(date '+%F %T') auditor: healer $healer_row" >> "$G/.self-fix.err.log"
  healer_recovered="$(printf '%s' "$healer_row" | "$PY" -c 'import json,sys
try:
    print(int(json.load(sys.stdin).get("recovered", 0)))
except Exception:
    print(0)' 2>/dev/null)"
  if [ "${healer_recovered:-0}" -gt 0 ]; then
    "$PY" "$(dirname "$0")/scripts/work_event_projector.py" --gig-dir "$G" \
      >>"$G/work-event-projector.log" 2>&1 || true
    "$PY" "$(dirname "$0")/scripts/telegram_report.py" work-events \
      >>"$G/work-event-report.log" 2>&1 || true
  fi
fi
