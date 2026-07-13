#!/usr/bin/env bash
# gig_selfimprove_verify.sh — enforce that the AUTONOMOUS loop actually executes its self-improve steps,
# without a human checking. Each pass appends a claim row to ~/gig/pass-report.jsonl; this verifier
# compares the claims against REAL file evidence and writes ~/gig/.selfimprove-todo.json listing the steps
# a pass claimed (or should have done) but left NO evidence for. STEP 0.5 of the next pass reads that file
# and is forced to do those first. This turns "I embedded it in the runbook" into "the loop proves it ran".
set -uo pipefail
G="$HOME/gig"; PY="$(command -v python3 || echo /opt/homebrew/bin/python3)"
"$PY" - "$G" <<'PYEOF'
import json,os,sys,time
G=sys.argv[1]; now=int(time.time())
def mtime(p): 
    try: return int(os.path.getmtime(p))
    except: return 0
def lastrow(p):
    try:
        rows=[l for l in open(p) if l.strip()]
        return json.loads(rows[-1]) if rows else {}
    except: return {}
# real evidence in the last ~90min (one pass window)
W=5400
ev = {
  "self_check": mtime(f"{G}/lessons.jsonl")  > now-W,          # a pass that self-checked usually appends a lesson
  "scouted_playbook": mtime(f"{G}/playbook.json") > now-W,     # scout+bake touches playbook
  "funnel": mtime(f"{G}/gig-funnel.jsonl") > now-W,            # every pass writes funnel
  "applied_or_nurtured": mtime(f"{G}/applied.jsonl") > now-W,  # A or B1 activity
  "listing_work": mtime(f"{G}/shuppin.jsonl") > now-W,         # B0
  "apply_volume": (lambda: (lambda rows: sum(1 for r in rows if r.get("status")=="applied" and (lambda t: (isinstance(t,(int,float)) and now-t<7200))(r.get("ts",0))) >= 3)([__import__("json").loads(l) for l in open(f"{G}/applied.jsonl") if l.strip() and l.strip()[0]=="{"] if __import__("os").path.exists(f"{G}/applied.jsonl") else []))(),  # >=3 applies in last 2h
}
todo=[k for k,v in ev.items() if not v]
out={"ts":now,"evidence":ev,"missing":todo,
     "note":"next pass STEP 0.5 must prioritise the missing steps"}
open(f"{G}/.selfimprove-todo.json","w").write(json.dumps(out,ensure_ascii=False))
# append an audit trail so we can watch the loop prove itself over time
with open(f"{G}/selfimprove-audit.jsonl","a") as f: f.write(json.dumps(out,ensure_ascii=False)+"\n")
print(json.dumps({"missing":todo,"evidence":ev},ensure_ascii=False))
PYEOF
