"""A real submit screenshot must recover a minimal ledger row without model help."""

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "application_report.py"
SPEC = importlib.util.spec_from_file_location("application_report", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_fresh_submit_proof_recovers_the_application_identity(tmp_path):
    evidence_root = tmp_path / "evidence"
    step_evidence = evidence_root / "gig-pass-fixture" / "agent-B2"
    step_evidence.mkdir(parents=True)
    result = step_evidence / "attempt-01.result.json"
    result.write_text(
        json.dumps(
            {
                "status": "ok",
                "summary": "model omitted the application row",
                "evidence": ["browser submit evidence exists"],
                "eligible_count": 0,
                "applications": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    summary = step_evidence / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "status": "success",
                "task_label": "gig-B2",
                "result_path": str(result),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proof = evidence_root / "gig-fixture-B2-5179000-submitted.png"
    proof.write_bytes(b"fresh proof")
    ledger = tmp_path / "applied.jsonl"
    ledger.write_text("", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runner-summary",
            str(summary),
            "--step-evidence",
            str(step_evidence),
            "--ledger",
            str(ledger),
            "--evidence-root",
            str(evidence_root),
            "--pass-id",
            "fixture",
            "--min-mtime",
            str(time.time() - 1),
        ],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert rows == [
        {
            "ts": rows[0]["ts"],
                "pass_id": "fixture",
                "requestId": "5179000",
                "bucket": "single",
                "status": "applied",
            "category": None,
            "category_source": None,
            "evidence": "5179000-submitted.png",
            "recorded_by": "application_report_proof_recovery",
        }
    ]


def test_retainer_ulid_proof_recovers_a_retainer_ledger_row(tmp_path):
    retainer_id = "01KYKDECET9WAY0CKRBCKH81RC"
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    proof = evidence_root / f"gig-fixture-B2-{retainer_id}-submitted.png"
    proof.write_bytes(b"fresh retainer proof")

    proven = MODULE._fresh_proven_ids(
        evidence_root,
        min_mtime=proof.stat().st_mtime - 0.1,
    )
    assert proven == {retainer_id}

    rows, recovered = MODULE.recover_from_proofs(
        existing_rows=[],
        request_ids=proven,
        now=1785270000,
        pass_id="fixture",
    )
    assert recovered == 1
    assert rows[0]["requestId"] == retainer_id
    assert rows[0]["bucket"] == "retainer"


def test_fresh_submit_intent_recovers_candidate_for_canonical_readback(tmp_path):
    request_id = "5170842"
    evidence_root = tmp_path / "evidence"
    step_evidence = evidence_root / "gig-pass-fixture"
    step_evidence.mkdir(parents=True)
    intent = step_evidence / f"gig-fixture-B2-{request_id}-submitted.intent.json"
    intent.write_text(json.dumps({
        "request_id": request_id,
        "bucket": "single",
        "url": f"https://coconala.com/requests/{request_id}",
        "title": "AIツール活用のWebサイト制作",
        "state": "prepared",
    }) + "\n", encoding="utf-8")

    recovered = MODULE._fresh_submit_intents(
        evidence_root,
        min_mtime=intent.stat().st_mtime - 0.1,
    )
    rows, count = MODULE.recover_from_intents(
        existing_rows=[],
        intents=recovered,
        now=1785278864,
        pass_id="1785278864-65816",
    )

    assert count == 1
    assert rows == [{
        "ts": 1785278864,
        "pass_id": "1785278864-65816",
        "requestId": request_id,
        "bucket": "single",
        "status": "reconcile_pending",
        "title": "AIツール活用のWebサイト制作",
        "url": f"https://coconala.com/requests/{request_id}",
        "category": None,
        "category_source": None,
        "evidence": intent.name,
        "recorded_by": "application_report_intent_recovery",
        "submit_verified": False,
        "applied_page_verified": False,
    }]
