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
from datetime import datetime
from zoneinfo import ZoneInfo
G=sys.argv[1]; now=int(time.time()); JST=ZoneInfo("Asia/Tokyo")
def mtime(p): 
    try: return int(os.path.getmtime(p))
    except: return 0
def lastrow(p):
    try:
        rows=[l for l in open(p) if l.strip()]
        return json.loads(rows[-1]) if rows else {}
    except: return {}
def latest_poll_control():
    last_pass_path=f"{G}/.last-pass"
    try:
        with open(last_pass_path,encoding="utf-8") as handle:
            last_pass=json.load(handle)
    except (OSError,TypeError,ValueError) as exc:
        return {}, {"kind":"invalid_last_pass","path":last_pass_path,"error":type(exc).__name__}
    pass_id=last_pass.get("pass_id") if isinstance(last_pass,dict) else None
    last_pass_ts=last_pass.get("ts") if isinstance(last_pass,dict) else None
    if (
        not isinstance(pass_id,str)
        or not pass_id
        or last_pass.get("status")!="success"
        or not isinstance(last_pass_ts,(int,float))
        or isinstance(last_pass_ts,bool)
        or not now-W < last_pass_ts <= now+60
        or mtime(last_pass_path)<=now-W
    ):
        return {}, {"kind":"invalid_last_pass_contract","path":last_pass_path}
    path=f"{G}/evidence/gig-pass-{pass_id}/poll-control.json"
    try:
        with open(path,encoding="utf-8") as handle:
            payload=json.load(handle)
    except (OSError,TypeError,ValueError) as exc:
        return {}, {"kind":"invalid_poll_control","path":path,"error":type(exc).__name__}
    valid_outcomes={"no_change","deterministic_event_handled","material_event_handled"}
    model_calls=payload.get("model_calls") if isinstance(payload,dict) else None
    labels=payload.get("model_call_labels") if isinstance(payload,dict) else None
    valid=(
        isinstance(payload,dict)
        and type(payload.get("version")) is int
        and payload.get("version")==1
        and mtime(path)>now-W
        and payload.get("pass_id")==pass_id
        and payload.get("outcome") in valid_outcomes
        and isinstance(model_calls,int) and not isinstance(model_calls,bool) and model_calls>=0
        and isinstance(labels,list) and all(isinstance(label,str) for label in labels)
        and len(labels)==model_calls
        and not (payload.get("outcome")=="no_change" and model_calls!=0)
    )
    if not valid:
        return {}, {"kind":"invalid_contract","path":path}
    return payload, {"kind":"valid","path":path}
def gap_days(ts,delivery_date):
    try:
        if isinstance(ts,(int,float)):
            submitted=datetime.fromtimestamp(ts,JST).date()
        elif isinstance(ts,str) and ts.isdigit():
            submitted=datetime.fromtimestamp(int(ts),JST).date()
        else:
            parsed=datetime.fromisoformat(str(ts).replace("Z","+00:00"))
            if parsed.tzinfo is None: parsed=parsed.replace(tzinfo=JST)
            submitted=parsed.astimezone(JST).date()
        due=datetime.strptime(delivery_date,"%Y-%m-%d").date()
        return (due-submitted).days
    except: return None
def read_jsonl_rows(p):
    rows=[]
    diagnostics=[]
    try:
        handle=open(p,encoding="utf-8")
    except FileNotFoundError:
        return rows, diagnostics
    with handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row=json.loads(line)
            except (TypeError, ValueError) as exc:
                # A malformed or concatenated JSONL row is fail-closed: do
                # not recover actions from it, but leave a bounded diagnostic
                # for STEP 0.5 and the audit trail.
                diagnostics.append({
                    "line": line_number,
                    "kind": "invalid_json",
                    "error": type(exc).__name__,
                    "detail": str(exc),
                    "preview": line.strip()[:160],
                })
                continue
            if not isinstance(row,dict):
                diagnostics.append({
                    "line": line_number,
                    "kind": "invalid_row_shape",
                    "error": "JSON object required",
                    "preview": line.strip()[:160],
                })
                continue
            rows.append(row)
    return rows, diagnostics

def pending_deliveries(rows):
    reviews=[]
    for row in rows:
        if row.get("status") not in ("applied","delivered_pending"): continue
        reviews.append({k:row.get(k) for k in ("requestId","category","price_jpy","ts","delivery_date")} | {"gap_days":gap_days(row.get("ts"),row.get("delivery_date"))})
    return reviews

applied_rows, applied_diagnostics = read_jsonl_rows(f"{G}/applied.jsonl")
ledger_diagnostics = {
    "applied.jsonl": {
        "malformed_count": len(applied_diagnostics),
        "details": applied_diagnostics,
    }
}
# real evidence in the last ~90min (one pass window)
W=5400
ev = {
  "self_check": mtime(f"{G}/lessons.jsonl")  > now-W,          # a pass that self-checked usually appends a lesson
  "scouted_playbook": mtime(f"{G}/playbook.json") > now-W,     # scout+bake touches playbook
  "funnel": mtime(f"{G}/gig-funnel.jsonl") > now-W,            # every pass writes funnel
  "applied_or_nurtured": mtime(f"{G}/applied.jsonl") > now-W,  # A or B1 activity
  "listing_work": mtime(f"{G}/shuppin.jsonl") > now-W,         # B0
  "apply_volume": sum(1 for r in applied_rows if r.get("status")=="applied" and (lambda t: (isinstance(t,(int,float)) and now-t<7200))(r.get("ts",0))) >= 3,  # >=3 applies in last 2h
}
poll_control,poll_control_diagnostic=latest_poll_control()
normal_noop=poll_control.get("outcome")=="no_change"
verification_mode="normal_noop" if normal_noop else "material_or_improve"
todo=[] if normal_noop else [k for k,v in ev.items() if not v]
pending=pending_deliveries(applied_rows)
out={"ts":now,"evidence":ev,"missing":todo,
     "latest_poll_control":poll_control,
     "poll_control_diagnostic":poll_control_diagnostic,
     "verification_mode":verification_mode,
     "pending_deliveries_review":pending,
     "ledger_diagnostics":ledger_diagnostics,
     "note":"next pass STEP 0.5 must prioritise missing steps and review pending deliveries"}
open(f"{G}/.selfimprove-todo.json","w").write(json.dumps(out,ensure_ascii=False))
# append an audit trail so we can watch the loop prove itself over time
with open(f"{G}/selfimprove-audit.jsonl","a") as f: f.write(json.dumps(out,ensure_ascii=False)+"\n")
print(json.dumps({"missing":todo,"evidence":ev,"ledger_diagnostics":ledger_diagnostics},ensure_ascii=False))
PYEOF
