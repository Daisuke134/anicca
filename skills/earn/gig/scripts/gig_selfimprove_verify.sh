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
def latest_pass_report():
    rows, _ = read_jsonl_rows(f"{G}/pass-report.jsonl")
    return rows[-1] if rows else {}

latest_pass = latest_pass_report()
poll_control, poll_control_diagnostic = latest_poll_control()
try:
    authoritative_pass = json.loads(open(f"{G}/.last-pass", encoding="utf-8").read())
except (OSError, ValueError):
    authoritative_pass = {}
pass_report_matches = (
    latest_pass.get("status") == "success"
    and authoritative_pass.get("status") == "success"
    and latest_pass.get("pass_id") == authoritative_pass.get("pass_id")
)
executed = set(latest_pass.get("steps_executed") or []) if pass_report_matches else None
# The verifier is launched from the pass finalizer and can race the heartbeat
# replacement.  During that small window .last-pass may be absent/corrupt while
# pass-report.jsonl still contains the last completed pass.  Treat that completed
# row as a provisional snapshot (only when its poll-control proof is fresh and
# internally valid) so a stale applied.jsonl mtime cannot manufacture a gap for
# B1/B2.  A genuinely invalid or stale snapshot still fails closed below.
if executed is None and poll_control_diagnostic.get("kind") in {"invalid_last_pass", "invalid_last_pass_contract"}:
    candidate_id = latest_pass.get("pass_id")
    candidate_path = f"{G}/evidence/gig-pass-{candidate_id}/poll-control.json" if isinstance(candidate_id, str) and candidate_id else ""
    try:
        with open(candidate_path, encoding="utf-8") as handle:
            candidate_poll = json.load(handle)
        candidate_fresh = mtime(candidate_path) > now-W
        candidate_valid = (
            latest_pass.get("status") == "success"
            and mtime(f"{G}/pass-report.jsonl") > now-W
            and isinstance(candidate_poll, dict)
            and type(candidate_poll.get("version")) is int
            and candidate_poll.get("version") == 1
            and candidate_poll.get("pass_id") == candidate_id
            and candidate_poll.get("outcome") in {"no_change", "deterministic_event_handled", "material_event_handled"}
            and isinstance(candidate_poll.get("model_calls"), int)
            and not isinstance(candidate_poll.get("model_calls"), bool)
            and candidate_poll.get("model_calls") >= 0
            and isinstance(candidate_poll.get("model_call_labels"), list)
            and all(isinstance(label, str) for label in candidate_poll.get("model_call_labels"))
            and len(candidate_poll.get("model_call_labels")) == candidate_poll.get("model_calls")
            and not (candidate_poll.get("outcome") == "no_change" and candidate_poll.get("model_calls") != 0)
            and candidate_fresh
        )
    except (OSError, TypeError, ValueError):
        candidate_valid = False
    if candidate_valid:
        executed = set(latest_pass.get("steps_executed") or [])
        poll_control = candidate_poll
        poll_control_diagnostic = {"kind": "provisional_completed_pass", "path": candidate_path}

def fresh_listing_proof(pass_row, allowed_window=W):
    """Validate B0's fresh owned browser proof; never infer it from ledger mtime."""
    if not isinstance(pass_row, dict) or pass_row.get("status") != "success":
        return False
    if "B0" not in (pass_row.get("steps_executed") or []):
        return False
    root = pass_row.get("evidence_dir")
    if not isinstance(root, str) or not root:
        return False
    evidence = os.path.realpath(os.path.join(root, "agent-B0"))
    summary_path = os.path.join(evidence, "summary.json")
    if mtime(summary_path) <= now - allowed_window:
        return False
    try:
        summary = json.load(open(summary_path, encoding="utf-8"))
        if summary.get("status") != "success" or summary.get("task_label") != "gig-B0":
            return False
        result_path = summary.get("result_path")
        if not isinstance(result_path, str):
            return False
        result_path = os.path.realpath(result_path)
        if os.path.commonpath([result_path, evidence]) != evidence or mtime(result_path) <= now - allowed_window:
            return False
        result = json.load(open(result_path, encoding="utf-8"))
        current = result.get("current_b0")
        if result.get("status") != "ok" or not isinstance(current, dict):
            return False
        if current.get("action") not in {"published", "created", "updated", "verified_noop"}:
            return False
        service_id = str(current.get("service_id") or "")
        url = str(current.get("url") or "")
        if not service_id.isdigit() or url != f"https://coconala.com/services/{service_id}":
            return False
        paths = []
        for key in ("screenshot_path", "live_dom_path"):
            path = current.get(key)
            if not isinstance(path, str):
                return False
            path = os.path.realpath(path)
            if os.path.commonpath([path, evidence]) != evidence or mtime(path) <= now - allowed_window or os.path.getsize(path) <= 0:
                return False
            paths.append(path)
        live_dom = json.load(open(paths[1], encoding="utf-8"))
        return live_dom.get("url") == url and live_dom.get("observed") is True and live_dom.get("not_found") is not True
    except (OSError, TypeError, ValueError, KeyError):
        return False

listing_work_proof = fresh_listing_proof(latest_pass) if executed is not None else False
authoritative_snapshot = executed is not None
ev = {
  # Evidence is scoped to the steps the authoritative pass report says ran.
  # A B0/B1-only pass must not be accused of missing B2 apply volume, and a
  # REFLECT-only wake must not be accused of scouting a playbook.  Previously
  # these were unconditional mtime checks, turning legitimate partial passes
  # into self-heal claims about work they never promised to do.
  "self_check": (executed is not None and "REFLECT" not in executed) or mtime(f"{G}/lessons.jsonl") > now-W,
  "scouted_playbook": (executed is not None and "LEARN" not in executed) or mtime(f"{G}/playbook.json") > now-W,
  "funnel": (not authoritative_snapshot) or mtime(f"{G}/gig-funnel.jsonl") > now-W,
  "applied_or_nurtured": (executed is not None and not ({"B1", "B2"} & executed)) or mtime(f"{G}/applied.jsonl") > now-W,
  "listing_work": (not authoritative_snapshot) or ("B0" not in executed) or listing_work_proof,
  "apply_volume": (executed is not None and "B2" not in executed) or sum(1 for r in applied_rows if r.get("status")=="applied" and (lambda t: (isinstance(t,(int,float)) and now-t<7200))(r.get("ts",0))) >= 3,
}
normal_noop=poll_control.get("outcome")=="no_change"
verification_mode=("normal_noop" if normal_noop else "material_or_improve") if authoritative_snapshot else "deferred_no_authoritative_pass"
todo=[] if normal_noop else [k for k,v in ev.items() if not v]
if not authoritative_snapshot:
    todo=[]
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
