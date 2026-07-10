#!/usr/bin/env bash
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
