#!/usr/bin/env python3
"""Closed loop-ID to immutable command mapping for jobs that require argv."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path


_SYMPHONY_COMMIT = "8001b52e3062495a16e520e4ceaf8f9de868c4d0"
_SYMPHONY_ARTIFACT_SHA256 = "a7c24792744eee5ab44188723267a9f11206ee834474028eda07c05a46867437"
_GITHUB_TOKEN = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82})"
)


def _validated_symphony_artifact(home: Path) -> Path:
    artifact_dir = home / ".local/libexec/openai-symphony" / _SYMPHONY_COMMIT
    artifact = artifact_dir / "symphony"
    try:
        if artifact_dir.is_symlink() or artifact.is_symlink():
            raise ValueError
        directory_stat = artifact_dir.stat()
        artifact_stat = artifact.stat()
        if (
            not artifact_dir.is_dir()
            or directory_stat.st_uid != os.getuid()
            or stat.S_IMODE(directory_stat.st_mode) != 0o700
            or not stat.S_ISREG(artifact_stat.st_mode)
            or artifact_stat.st_uid != os.getuid()
            or stat.S_IMODE(artifact_stat.st_mode) != 0o500
        ):
            raise ValueError
        digest = hashlib.sha256()
        with artifact.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != _SYMPHONY_ARTIFACT_SHA256:
            raise ValueError
    except (OSError, ValueError):
        raise ValueError("official Symphony artifact unavailable") from None
    return artifact


def command_for(loop_id: str, root: Path, home: Path) -> list[str]:
    if loop_id == "money-printer-symphony":
        artifact = _validated_symphony_artifact(home)
        return [
            str(home / ".local/share/mise/installs/erlang/28.5/bin/escript"),
            str(artifact),
            "--i-understand-that-this-will-be-running-without-the-usual-guardrails",
            "--logs-root",
            str(home / ".local/state/life-manager/money-printer-symphony/runtime-logs"),
            "--port", "4000",
            str(root / "ops/symphony/WORKFLOW.money-printer.md"),
        ]
    affiliate = root / "skills/affiliate/affiliate"
    affiliate_browser = root / "skills/affiliate/scripts/local_browser.py"
    scheduled = root / "skills/earn/marketing-engine/report/scheduled_runner.py"
    writer = root / "skills/writer-agent/scripts"
    writer_state = home / ".local/state/life-manager/writer"
    lancers = root / "skills/earn/lancers/scripts"
    lancers_state = home / ".local/state/anicca/lancers"
    python = sys.executable
    cloak_python = str(home / ".openclaw/skills/_shared/venv-cloak/bin/python")
    fixed = {
        "money-printer-symphony-bridge": [
            "/opt/homebrew/bin/node",
            str(root / "apps/life-manager/scripts/money-printer-symphony-bridge.js"),
        ],
        "affiliate-browser": [cloak_python, str(affiliate_browser)],
        "affiliate-impact-browser": [cloak_python, str(affiliate_browser)],
        "affiliate-x-browser": [cloak_python, str(affiliate_browser)],
        "life-manager-daily-driver": [
            cloak_python, str(root / "skills/browser/cdp_persistent_context.py"),
            "--profile", str(home / ".cloak/profiles/daily-driver"),
            "--port", "9222",
        ],
        "affiliate-composition": [str(affiliate), "compose", "wake"],
        "affiliate-loop": [str(affiliate), "loop", "wake"],
        "affiliate-source-refresh": [str(affiliate), "sources", "wake"],
        "clip-loop": [python, str(scheduled), "clip"],
        "marketing-dashboard": [python, str(scheduled), "dashboard"],
        "marketing-metrics-daily": [python, str(scheduled), "metrics"],
        "marketing-mine-daily": [python, str(scheduled), "mine"],
        "marketing-score-daily": [python, str(scheduled), "score"],
        "lancers-revenue-application": [
            python, str(lancers / "application_loop.py"), "--json",
            "--state-path", str(lancers_state / "application.json"),
        ],
        "lancers-revenue-work-sync": [
            python, str(lancers / "work_sync.py"), "--json",
            "--state-path", str(lancers_state / "work-sync.json"),
        ],
        "lancers-revenue-storefront": [
            python, str(lancers / "storefront_offer.py"), "--apply",
            "--product", str(lancers.parent / "products/monthly-sns-content-ops-v1.json"),
            "--state-path", str(lancers_state / "application.json"),
        ],
        "lancers-revenue-telegram-report": [
            python, str(lancers / "telegram_report.py"), "--json",
            "--database", str(lancers_state / "telegram.sqlite3"),
            "--ledger-database", str(lancers_state / "marketplace-ledger.sqlite3"),
            "--state-path", str(lancers_state / "application.json"),
            "--application-log", str(lancers_state / "logs/application.out.log"),
            "--storefront-log", str(lancers_state / "logs/storefront.stdout.log"),
        ],
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


def environment_for(loop_id: str, home: Path, base: dict[str, str]) -> dict[str, str]:
    environment = dict(base)
    if loop_id == "money-printer-symphony":
        private = home / ".local/share/anicca"
        credentials = private / "credentials.json"
        try:
            if private.is_symlink() or credentials.is_symlink():
                raise ValueError
            if private.stat().st_uid != os.getuid() or stat.S_IMODE(private.stat().st_mode) != 0o700:
                raise ValueError
            if credentials.stat().st_uid != os.getuid() or stat.S_IMODE(credentials.stat().st_mode) != 0o600:
                raise ValueError
            payload = json.loads(credentials.read_text(encoding="utf-8"))
            rows = [row for row in payload.get("credentials", [])
                    if isinstance(row, dict) and row.get("service") == "openai-symphony-github"]
            if len(rows) != 1 or not _GITHUB_TOKEN.fullmatch(rows[0].get("token", "")):
                raise ValueError
        except (OSError, AttributeError, TypeError, json.JSONDecodeError, ValueError):
            raise ValueError("Symphony GitHub credential unavailable") from None
        for alias in ("GH_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
            environment.pop(alias, None)
        environment.update({
            "GITHUB_TOKEN": rows[0]["token"],
            "PATH": "/opt/homebrew/bin:/usr/bin:/bin",
        })
        return environment
    if loop_id != "money-printer-symphony-bridge":
        return environment
    private = home / ".local/share/anicca"
    credentials = private / "credentials.json"
    try:
        if private.is_symlink() or credentials.is_symlink():
            raise ValueError
        if private.stat().st_uid != os.getuid() or stat.S_IMODE(private.stat().st_mode) != 0o700:
            raise ValueError
        if credentials.stat().st_uid != os.getuid() or stat.S_IMODE(credentials.stat().st_mode) != 0o600:
            raise ValueError
        payload = json.loads(credentials.read_text(encoding="utf-8"))
        bridge_rows = [row for row in payload.get("credentials", [])
                       if isinstance(row, dict)
                       and row.get("service") == "life-manager-symphony-bridge"]
        github_rows = [row for row in payload.get("credentials", [])
                       if isinstance(row, dict)
                       and row.get("service") == "openai-symphony-github"]
        if (len(bridge_rows) != 1
                or not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", bridge_rows[0].get("token", ""))
                or len(github_rows) != 1
                or not _GITHUB_TOKEN.fullmatch(github_rows[0].get("token", ""))):
            raise ValueError
    except (OSError, AttributeError, TypeError, json.JSONDecodeError, ValueError):
        raise ValueError("money printer bridge credential unavailable") from None
    for alias in ("GH_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
        environment.pop(alias, None)
    environment.update({
        "LM_SYMPHONY_API_BASE_URL": "https://life-call-production.up.railway.app",
        "LM_SYMPHONY_BRIDGE_SECRET": bridge_rows[0]["token"],
        "LM_RUNTIME_TENANT_ID": "webmcp-judge",
        "GITHUB_TOKEN": github_rows[0]["token"],
        "PATH": "/opt/homebrew/bin:/usr/bin:/bin",
    })
    return environment


def main() -> int:
    loop_id = os.environ.get("LIFE_MANAGER_LOOP_ID", "")
    root = Path(__file__).resolve().parents[2]
    try:
        home = Path.home()
        command = command_for(loop_id, root, home)
        environment = environment_for(loop_id, home, os.environ)
    except ValueError as error:
        print(f"entry-dispatch: {error}", file=sys.stderr); return 78
    os.execve(command[0], command, environment)
    return 70


if __name__ == "__main__":
    raise SystemExit(main())
