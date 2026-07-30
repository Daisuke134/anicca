#!/usr/bin/env bash
# run.sh — the MAIN-loop entrypoint for the earn/gig slot (runtime/loop/earn-slot.mjs resolves
# earn/gig → skills/earn/gig/run.sh). earn/gig is a COCONALA human-funded loop (¥ → Dais MUFG),
# NOT an on-chain USDC earner. The REAL earning runs in an independent claude-p tmux+cron core
# (gig-cli.sh). When the main loop picks earn/gig, this does a cheap, honest SUPERVISE+REPORT pass:
#   1) ensure the Coconala gig-core is alive (idempotent start; healthcheck also covers it)
#   2) emit an honest status line — applied/earnings counts in ¥. NEVER claims USDC, NEVER calls
#      record-earn (the archived dealwork/USDC machinery is not part of this loop).
# The model's args arrive as $ANICCA_ARGS (JSON); they are not needed here (no per-call action).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/scripts/gig_paths.sh"
WAKE="${WAKE_ID:-$(date +%s)}"
PY="${PYTHON3:-$(command -v python3)}"

# 1) ensure the real Coconala earner (tmux core) is alive — idempotent
bash "$HERE/gig-cli.sh" >/dev/null 2>&1 || true
CORE=$(bash "$HERE/gig-cli.sh" --status 2>/dev/null | head -1)

# 2a) sprint-3 #31 SHIM: read LAYER B (proactive-loop) observability via
#     lib.proactive_observe (read-only; ZERO writes under ~/loops/gig/).
SHARED_DIR="$(cd "$HERE/../../_shared" && pwd)"
PL_JSON="$( cd "$SHARED_DIR" && "$PY" -m lib.proactive_observe gig "$HOME/loops/gig" 2>/dev/null || echo '{}' )"

# 2b) honest status from the core's ledgers (¥ only; 検収/支払 rows are the only earned rows)
"$PY" - "$WAKE" "$CORE" "$PL_JSON" "$GIG_STATE_DIR" <<'PY'
import json,sys,os
wake,core,pl_json,G=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]
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
applied=[r for r in rows("applied.jsonl") if r.get("status")=="applied"]
SETTLED={"検収","支払","検収完了","completed","paid"}
earned=[r for r in rows("earnings.jsonl") if r.get("status") in SETTLED and r.get("evidence") and jnum(r.get("jpy",0))>0]
jpy=sum(jnum(r.get("jpy",0)) for r in earned)
try:
    pl = json.loads(pl_json) if pl_json else {}
except Exception:
    pl = {}
# Defaults so REQ-S2 shape is honored even if the observer subprocess failed
pl_obj = {
    "installed": bool(pl.get("installed", False)),
    "last_pass_ts": pl.get("last_pass_ts"),
    "last_pass_step": pl.get("last_pass_step"),
    "build_log_passes": int(pl.get("build_log_passes", 0)),
}
print(json.dumps({"wallet":None,"source":"gig","task":"supervise","funding":"human(¥→MUFG)",
  "earn_usdc":0,"cost_usdc":0,"jpy_earned":round(jpy,0),"applied_total":len(applied),
  "core":core,"wake":wake,"note":"Coconala loop; ¥ human-funded; no USDC; earned=検収-only",
  "proactive_loop": pl_obj}))
PY
exit 0
