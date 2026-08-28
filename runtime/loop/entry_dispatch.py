#!/usr/bin/env python3
"""Closed loop-ID to immutable command mapping for jobs that require argv."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def command_for(loop_id: str, root: Path, home: Path) -> list[str]:
    affiliate = root / "skills/affiliate/affiliate"
    affiliate_browser = root / "skills/affiliate/scripts/local_browser.py"
    scheduled = root / "skills/earn/marketing-engine/report/scheduled_runner.py"
    writer = root / "skills/writer-agent/scripts"
    writer_state = home / ".local/state/life-manager/writer"
    python = sys.executable
    fixed = {
        "affiliate-browser": [python, str(affiliate_browser)],
        "affiliate-impact-browser": [python, str(affiliate_browser)],
        "affiliate-x-browser": [python, str(affiliate_browser)],
        "affiliate-composition": [str(affiliate), "compose", "wake"],
        "affiliate-loop": [str(affiliate), "loop", "wake"],
        "affiliate-source-refresh": [str(affiliate), "sources", "wake"],
        "clip-loop": [python, str(scheduled), "clip"],
        "marketing-dashboard": [python, str(scheduled), "dashboard"],
        "marketing-metrics-daily": [python, str(scheduled), "metrics"],
        "marketing-mine-daily": [python, str(scheduled), "mine"],
        "marketing-score-daily": [python, str(scheduled), "score"],
        "self-improve-evolve": [python, str(scheduled), "self-improve"],
        "marketing-metrics": [str(root / "marketing/engine/bin/marketing"), "observe",
                              "--root", str(home / "Library/Application Support/AniccaMarketing")],
        "marketing-owner-events": [python, str(root / "skills/earn/marketing-engine/report/truth_pipeline.py"),
                                   "--repo-root", str(root), "--home", str(home)],
        "marketing-weekly-review": [str(root / "skills/earn/marketing-engine/bin/lm"),
                                    "intel", "gap", "--telegram"],
        "hf-gig-paid-direct": [
            python, str(root / "skills/earn/gig/scripts/gig_disk_guard.py"),
            python, str(root / "skills/earn/gig/scripts/paid_direct.py"),
            "--output", str(home / "gig/evidence/paid-direct-live/latest.json"),
            "--evidence-dir", str(home / "gig/evidence/paid-direct-live"),
            "--projects-root", str(home / "gig/projects"),
            "--lock-file", str(home / "gig/.paid-direct.lock"),
            "--cdp-lock-dir", str(home / "gig/.cdp-gig.lock"),
        ],
        "hf-gig-apply-direct": [
            python, str(root / "skills/earn/gig/scripts/gig_disk_guard.py"),
            python, str(root / "skills/earn/gig/scripts/application_direct.py"),
            "--all-eligible", "--planner-runner",
            str(root / "runtime/agent-runner/agent_runner.py"),
        ],
        "hf-gig-reply-detector": [
            python, str(root / "skills/earn/gig/scripts/gig_disk_guard.py"),
            python, str(root / "skills/earn/gig/scripts/reply_detector.py"),
            "--trigger", "fallback", "--runner",
            str(root / "runtime/agent-runner/agent_runner.py"),
            "--runner-config", str(root / "runtime/agent-runner/config.json"),
            "--continuous", "--poll-seconds", "30", "--workers", "2",
        ],
        "hf-gig-storefront-direct": [
            python, str(root / "skills/earn/gig/scripts/gig_disk_guard.py"),
            python, str(root / "skills/earn/gig/scripts/storefront_direct.py"),
            "--effect", "--auto-cadence", "--full-interval-seconds", "60",
        ],
        "writer-claim-loop": [python, str(writer / "claim_loop.py"),
                              "--state-dir", str(writer_state)],
        "writer-money-sync": [python, str(writer / "money_sync.py"),
                              "--state-dir", str(writer_state),
                              "--db", str(writer_state / "money.sqlite3")],
        "writer-opportunity-discovery": [
            python, str(writer / "opportunity_discovery.py"),
            "--db", str(writer_state / "opportunities.sqlite3"),
            "--claims-db", str(writer_state / "claims.sqlite3"),
            "--receipt", str(writer_state / "opportunity-discovery-latest.json"),
        ],
        "writer-opportunity-response": [
            python, str(writer / "opportunity_response.py"),
            "--db", str(writer_state / "opportunities.sqlite3"),
            "--receipt", str(writer_state / "opportunity-response-latest.json"),
        ],
        "writer-report": [python, str(writer / "writer_report_worker.py"),
                          "--state-dir", str(writer_state)],
    }
    if loop_id in {"marketing-owner-daily", "marketing-owner-weekly"}:
        kind = "product_daily" if loop_id.endswith("daily") else "portfolio_weekly"
        return [python, str(root / "skills/earn/marketing-engine/report/owner_report_cli.py"),
                "sweep", "--kind", kind, "--state-root",
                str(home / ".local/state/life-manager/marketing-engine")]
    if loop_id not in fixed:
        raise ValueError(f"no dispatch command for loop: {loop_id}")
    return fixed[loop_id]


def main() -> int:
    loop_id = os.environ.get("LIFE_MANAGER_LOOP_ID", "")
    root = Path(__file__).resolve().parents[2]
    try:
        command = command_for(loop_id, root, Path.home())
    except ValueError as error:
        print(f"entry-dispatch: {error}", file=sys.stderr); return 78
    os.execv(command[0], command)
    return 70


if __name__ == "__main__":
    raise SystemExit(main())
