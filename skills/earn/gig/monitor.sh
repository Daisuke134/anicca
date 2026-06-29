#!/usr/bin/env bash
# monitor.sh — observe the Coconala gig loop (cloned from clip/monitor.sh's role). Reports, from the
# files the core writes, WITHOUT taking any action: applications made, replies, deliveries, and the
# ¥ earned ledger. ¥ is HUMAN-FUNDED (settles to Dais's Coconala account → MUFG) — there is NO
# on-chain USDC here, so this NEVER calls record-earn. A ¥ earn is recorded ONLY by the core when
# Coconala's UI actually shows 検収/支払 (real side-effect), appended to ~/gig/earnings.jsonl.
#
#   monitor.sh            # one-line JSON status of the gig loop
set -uo pipefail
G="$HOME/gig"
APPLIED="$G/applied.jsonl"
EARN="$G/earnings.jsonl"      # {ts, requestId, jpy, status:"検収"|"支払", evidence} — written by the core on real 検収 only
PY=/opt/homebrew/bin/python3

"$PY" - "$APPLIED" "$EARN" <<'PY'
import json,sys,os
applied_f,earn_f=sys.argv[1],sys.argv[2]
def rows(f):
    if not os.path.exists(f): return []
    out=[]
    for l in open(f):
        l=l.strip()
        if not l: continue
        try: out.append(json.loads(l))
        except: pass
    return out
ap=rows(applied_f); ea=rows(earn_f)
applied=[r for r in ap if r.get("status")=="applied"]
# deterministic earned guard (FIND-003): a ¥ row counts ONLY with a settled status AND non-empty
# evidence — an applied/in-progress/fabricated row can NEVER be summed as earned.
SETTLED={"検収","支払","検収完了","completed","paid"}
valid=[r for r in ea if r.get("status") in SETTLED and r.get("evidence")]
rejected=len(ea)-len(valid)
jpy=sum(float(r.get("jpy",0) or 0) for r in valid)
core_alive=os.system("tmux -S /tmp/anicca-gig-tmux.sock has-session -t anicca-gig-core 2>/dev/null")==0
print(json.dumps({"slot":"gig/coconala","core":"ALIVE" if core_alive else "DEAD",
  "applied_total":len(applied),"earn_rows_valid":len(valid),"earn_rows_rejected":rejected,
  "jpy_earned":round(jpy,0),
  "note":"¥ human-funded -> Dais MUFG; earned = settled-status + evidence only (no USDC)"}))
PY
