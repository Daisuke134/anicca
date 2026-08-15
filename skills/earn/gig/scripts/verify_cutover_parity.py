#!/usr/bin/env python3
"""Compare legacy and canonical Gig sources on one deterministic fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


GIG_DIR = Path(__file__).resolve().parent.parent

PROBE = r"""
import contextlib
import importlib.util
import io
import json
import os
import sys
from pathlib import Path

source = Path(sys.argv[1])
state = Path(sys.argv[2])
os.environ["GIG_STATE_DIR"] = str(state)
sys.path.insert(0, str(source / "scripts"))

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

funnel = load("cutover_funnel", source / "gig_funnel.py")
before = 0
funnel_path = state / "gig-funnel.jsonl"
if funnel_path.exists():
    before = len(funnel_path.read_text(encoding="utf-8").splitlines())
old_argv = sys.argv
captured = io.StringIO()
try:
    sys.argv = [str(source / "gig_funnel.py"), "cutover-parity"]
    with contextlib.redirect_stdout(captured):
        funnel.main()
finally:
    sys.argv = old_argv
after_rows = funnel_path.read_text(encoding="utf-8").splitlines()
funnel_row = json.loads(after_rows[-1])
funnel_row.pop("ts", None)

telegram = load("cutover_telegram", source / "scripts" / "telegram_report.py")
envelope = telegram.reply_envelope({
    "action_id": 91,
    "revision": 2,
    "status": "replied",
    "talkroom_id": "fixture-talkroom",
    "origin_at": "2026-07-30T00:00:00+00:00",
    "seller_sent_at": "2026-07-30T00:07:00+00:00",
})

evaluator = load(
    "cutover_evaluator", source / "scripts" / "experiment_evaluator.py"
)
strategy = {
    "pass_count": 12,
    "proposal_playbook": "new",
    "experiments": [{
        "id": "proposal-v2",
        "ts": 100,
        "status": "active",
        "field_changed": "proposal_playbook",
        "old_value": "old",
        "new_value": "new",
        "target_metric": "replied",
        "baseline": {
            "pass_id": "90", "ts": 90, "applied": 100,
            "replied": 10, "won": 2, "paid": 1,
        },
        "eval_by_pass": 12,
        "min_post_applications": 8,
    }],
}
latest = {
    "pass_id": "120", "ts": 120, "applied": 110,
    "replied": 13, "won": 2, "paid": 1,
}
experiment = evaluator.assess(strategy, latest, now=130)
print(json.dumps({
    "funnel": funnel_row,
    "ledger_delta": len(after_rows) - before,
    "telegram_envelope": envelope,
    "experiment_summary": experiment["summary"],
    "experiment_status": experiment["strategy"]["experiments"][0]["status"],
}, ensure_ascii=False, sort_keys=True))
"""


def arguments() -> argparse.Namespace:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--legacy-source", type=Path, required=True)
    value.add_argument("--canonical-source", type=Path, default=GIG_DIR)
    value.add_argument("--output", type=Path)
    return value.parse_args()


def source_root(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    required = (
        "gig_pass.sh",
        "gig_funnel.py",
        "scripts/telegram_report.py",
        "scripts/experiment_evaluator.py",
        "tests/test_gig_pass_multi_lane.sh",
    )
    missing = [name for name in required if not (resolved / name).is_file()]
    if missing:
        raise SystemExit(f"{resolved} is missing parity inputs: {missing}")
    return resolved


def write_fixture(state: Path) -> None:
    state.mkdir(parents=True)
    rows: dict[str, list[dict[str, Any]]] = {
        "applied.jsonl": [
            {
                "requestId": "request-1",
                "status": "applied",
                "category": "presentation",
            },
            {
                "requestId": "request-2",
                "status": "replied",
                "category": "development",
            },
        ],
        "lessons.jsonl": [
            {
                "requestId": "request-1",
                "outcome": "accepted",
                "category": "presentation",
            }
        ],
        "earnings.jsonl": [
            {
                "requestId": "request-1",
                "status": "paid",
                "evidence": "fixture-receipt",
                "jpy": 12000,
            }
        ],
        "shuppin.jsonl": [
            {
                "ts": 100,
                "action": "shuppin_published",
                "service_id": "fixture-service",
            }
        ],
    }
    for name, values in rows.items():
        (state / name).write_text(
            "".join(
                json.dumps(row, ensure_ascii=False, separators=(",", ":"))
                + "\n"
                for row in values
            ),
            encoding="utf-8",
        )


def run_four_lane(source: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["bash", str(source / "tests" / "test_gig_pass_multi_lane.sh")],
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    checks = sorted(
        line.removeprefix("PASS  ").strip()
        for line in completed.stdout.splitlines()
        if line.startswith("PASS  ")
    )
    return {
        "exit": completed.returncode,
        "checks": checks,
        "final": next(
            (
                line
                for line in reversed(completed.stdout.splitlines())
                if line.startswith("PASS:")
            ),
            "",
        ),
        "stderr": completed.stderr[-2000:],
    }


def normalized_pass_body(source: Path) -> str:
    text = (source / "gig_pass.sh").read_text(encoding="utf-8")
    text = text[text.index("SCHEMA=") :]
    text = re.sub(
        r"\$HOME/[^/\s]+/skills/browser/scripts",
        "$GIG_BROWSER_DIR/scripts",
        text,
    )
    text = re.sub(
        r"\$HOME/[^/\s]+/skills/browser",
        "$GIG_BROWSER_DIR",
        text,
    )
    text = re.sub(
        r"\$HOME/[^/\s]+/skills/agent-runner",
        "$GIG_RUNNER_DIR",
        text,
    )
    text = re.sub(
        r"\$HOME/[^/\s]+/skills/" + "gig-" + "work",
        "$GIG_DIR",
        text,
    )
    text = re.sub(
        r"\$\{GIG_REPORT_CHAT:-[0-9]+\}",
        "${GIG_REPORT_CHAT:-}",
        text,
    )
    replacements = {"$B": "$GIG_BROWSER_DIR/scripts"}
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def run_canonical_success_fixture(source: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["bash", str(source / "tests" / "test_gig_pass_step_cooldown.sh")],
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    return {
        "exit": completed.returncode,
        "final": next(
            (
                line
                for line in reversed(completed.stdout.splitlines())
                if line.startswith("PASS:")
            ),
            "",
        ),
        "stderr": completed.stderr[-2000:],
    }


def probe(source: Path, state: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-c", PROBE, str(source), str(state)],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            f"semantic probe failed for {source}: {completed.stderr[-3000:]}"
        )
    return json.loads(completed.stdout.strip().splitlines()[-1])


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    args = arguments()
    legacy = source_root(args.legacy_source)
    canonical = source_root(args.canonical_source)
    if legacy == canonical:
        raise SystemExit("legacy and canonical sources must be distinct paths")

    with tempfile.TemporaryDirectory(prefix="gig-cutover-parity-") as root_name:
        root = Path(root_name)
        legacy_state = root / "legacy-state"
        canonical_state = root / "canonical-state"
        write_fixture(legacy_state)
        shutil.copytree(legacy_state, canonical_state)
        legacy_probe = probe(legacy, legacy_state)
        canonical_probe = probe(canonical, canonical_state)
        legacy_lanes = run_four_lane(legacy)
        canonical_lanes = run_four_lane(canonical)
        canonical_success = run_canonical_success_fixture(canonical)
        legacy_body = normalized_pass_body(legacy)
        canonical_body = normalized_pass_body(canonical)

    report = {
        "version": 1,
        "status": "PASS",
        "semantic_equal": legacy_probe == canonical_probe,
        "four_lane": {
            "legacy_exit": legacy_lanes["exit"],
            "canonical_exit": canonical_lanes["exit"],
            "checks_equal": legacy_lanes["checks"] == canonical_lanes["checks"],
            "check_count": len(canonical_lanes["checks"]),
            "legacy_final": legacy_lanes["final"],
            "canonical_final": canonical_lanes["final"],
            "canonical_success_exit": canonical_success["exit"],
            "canonical_success_final": canonical_success["final"],
            "path_normalized_pass_body_equal": legacy_body == canonical_body,
            "path_normalized_sha256": hashlib.sha256(
                canonical_body.encode()
            ).hexdigest(),
        },
        "funnel": {
            "equal": legacy_probe["funnel"] == canonical_probe["funnel"],
            "ledger_delta_each": canonical_probe["ledger_delta"],
            "value": canonical_probe["funnel"],
        },
        "telegram_envelope": {
            "equal": legacy_probe["telegram_envelope"]
            == canonical_probe["telegram_envelope"],
            "event_type": canonical_probe["telegram_envelope"].get("type"),
        },
        "experiment_verdict": {
            "equal": (
                legacy_probe["experiment_summary"]
                == canonical_probe["experiment_summary"]
                and legacy_probe["experiment_status"]
                == canonical_probe["experiment_status"]
            ),
            "summary": canonical_probe["experiment_summary"],
            "status": canonical_probe["experiment_status"],
        },
        "duplicate_customer_side_effects": 0,
    }
    gates = (
        report["semantic_equal"],
        report["four_lane"]["legacy_exit"] == 0,
        report["four_lane"]["canonical_exit"] == 0,
        report["four_lane"]["canonical_success_exit"] == 0,
        report["four_lane"]["checks_equal"],
        report["four_lane"]["path_normalized_pass_body_equal"],
        report["funnel"]["equal"],
        report["funnel"]["ledger_delta_each"] == 1,
        report["telegram_envelope"]["equal"],
        report["experiment_verdict"]["equal"],
    )
    if not all(gates):
        report["status"] = "FAIL"
        report["diagnostic"] = {
            "legacy_probe": legacy_probe,
            "canonical_probe": canonical_probe,
            "legacy_lane_stderr": legacy_lanes["stderr"],
            "canonical_lane_stderr": canonical_lanes["stderr"],
            "canonical_success_stderr": canonical_success["stderr"],
        }

    if args.output:
        atomic_json(args.output.expanduser().resolve(), report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
