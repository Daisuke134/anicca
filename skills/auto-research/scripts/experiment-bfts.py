#!/usr/bin/env python3
"""experiment-bfts.py — pick the best experiment branch via Sakana BFTSManager (Stage 15),
then hand the chosen plan to scripts/run-local.sh for sandboxed execution.

Hard-gate on `human_flags`: any of {wet-lab, expensive-compute, external-data, {{profile.lateness.stakeholders.senderType}}-review}
forces a Slack ack via workspace/auto-research/acks/<project>.pending and exits without
running the experiment until acks/<project>.ack appears.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace/auto-research"))
DRY_RUN = os.environ.get("AUTO_RESEARCH_DRY_RUN", "false").lower() == "true"
CHASSIS = Path(os.path.expanduser("~/.openclaw/workspace/AutoResearchClaw"))
HUMAN_FLAGS = {"wet-lab", "expensive-compute", "external-data", "{{profile.lateness.stakeholders.senderType}}-review"}


def needs_ack(project: dict) -> bool:
    flags = set(project.get("human_flags") or [])
    return bool(flags & HUMAN_FLAGS)


def main(project: dict) -> int:
    pid = project["id"]
    today = dt.date.today().isoformat()
    hyp_path = WORKSPACE / "hypotheses" / pid / f"{today}.json"
    out_dir = WORKSPACE / "experiments" / pid / today
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / "plan.json"
    results_path = out_dir / "results.json"
    acks = WORKSPACE / "acks"
    acks.mkdir(parents=True, exist_ok=True)
    pending = acks / f"{pid}.pending"
    ack = acks / f"{pid}.ack"

    if needs_ack(project) and not ack.exists():
        pending.write_text(json.dumps({
            "project": pid,
            "human_flags": project.get("human_flags"),
            "requested_at": dt.datetime.utcnow().isoformat() + "Z",
            "message": f"Project '{pid}' needs Slack ack before experiment cron runs (flags: {project.get('human_flags')}).",
        }, indent=2))
        print(f"experiment-bfts[{pid}][HOLD]: human ack required (flags={project.get('human_flags')}). Pending file: {pending}")
        return 0

    if not hyp_path.exists():
        print(f"experiment-bfts[{pid}]: no hypotheses at {hyp_path} — skipping.")
        return 0

    if DRY_RUN:
        plan_path.write_text(json.dumps({
            "project": pid,
            "stub": True,
            "bfts": {"manager": "Sakana.BFTSManager", "{{profile.lateness.stakeholders.senderType}}": 15, "use_bfts_for_decision": True, "branches": 4, "depth": 3},
            "sandbox": {"image": "ghcr.io/sakana-ai/research-sandbox:latest", "wallclock_s": 1800, "network": "none", "memory": "4g"},
        }, indent=2))
        print(f"experiment-bfts[{pid}][DRY_RUN]: wrote plan {plan_path}")
        print(f"experiment-bfts[{pid}][DRY_RUN]: would call Sakana BFTSManager (Stage 15) → run-local.sh sandbox (no network, 30 min wallclock).")
        return 0

    sys.path.insert(0, str(CHASSIS))
    try:
        from researchclaw.pipeline.{{profile.lateness.stakeholders.senderType}}_impls._execution import BFTSManager  # type: ignore
    except Exception as e:
        print(f"experiment-bfts[{pid}]: chassis import failed ({e}).")
        return 1

    hyp = json.loads(hyp_path.read_text())
    mgr = BFTSManager(use_bfts_for_decision=True)
    chosen = mgr.pick(hyp.get("candidates", []), branches=4, depth=3)
    plan_path.write_text(json.dumps({"project": pid, "chosen": chosen}, indent=2, ensure_ascii=False))
    print(f"experiment-bfts[{pid}]: BFTS chose branch {chosen.get('branch_id')} → plan written.")

    # Run sandbox
    script = Path(__file__).parent / "run-local.sh"
    rc = subprocess.call(["bash", str(script), str(plan_path), str(results_path)])
    print(f"experiment-bfts[{pid}]: sandbox exit={rc}")
    return rc


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: experiment-bfts.py <project-json>", file=sys.stderr); raise SystemExit(64)
    blob = json.loads(sys.argv[1])
    raise SystemExit(main(blob["project"]))
