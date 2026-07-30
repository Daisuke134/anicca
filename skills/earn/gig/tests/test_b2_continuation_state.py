import json
import subprocess
import sys
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "b2_continuation_state.py"
)


def run_builder(tmp_path, result, ledger_rows):
    result_path = tmp_path / "result.json"
    summary_path = tmp_path / "summary.json"
    ledger_path = tmp_path / "applied.jsonl"
    result_path.write_text(json.dumps(result), encoding="utf-8")
    summary_path.write_text(
        json.dumps({"result_path": str(result_path)}),
        encoding="utf-8",
    )
    ledger_path.write_text(
        "".join(json.dumps(row) + "\n" for row in ledger_rows),
        encoding="utf-8",
    )
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runner-summary",
            str(summary_path),
            "--ledger",
            str(ledger_path),
            "--pass-id",
            "pass-1",
        ],
        capture_output=True,
        text=True,
    )


def test_unverified_model_application_is_not_carried_into_next_attempt(tmp_path):
    result = {
        "applications": [
            {"request_id": "5183271", "title": "form opened only"},
            {"request_id": "5183739", "title": "actually submitted"},
        ],
        "current_b2": {
            "inspected_requests": [{"request_id": "5183271"}],
            "search_sources": [{"source_id": "single:new"}],
        },
    }
    ledger_rows = [
        {
            "pass_id": "pass-1",
            "requestId": "5183739",
            "status": "applied",
            "submit_verified": True,
            "applied_page_verified": True,
        }
    ]

    proc = run_builder(tmp_path, result, ledger_rows)

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert [row["request_id"] for row in payload["applications"]] == ["5183739"]
    assert payload["current_b2"] == result["current_b2"]


def test_wrong_pass_or_incomplete_proof_never_becomes_continuation_application(
    tmp_path,
):
    result = {
        "applications": [
            {"requestId": "5183271"},
            {"requestId": "5183739"},
            {"requestId": "5183597"},
        ],
        "current_b2": {},
    }
    ledger_rows = [
        {
            "pass_id": "older-pass",
            "requestId": "5183271",
            "status": "applied",
            "submit_verified": True,
            "applied_page_verified": True,
        },
        {
            "pass_id": "pass-1",
            "requestId": "5183739",
            "status": "applied",
            "submit_verified": False,
            "applied_page_verified": True,
        },
        {
            "pass_id": "pass-1",
            "requestId": "5183597",
            "status": "applied",
            "submit_verified": True,
            "applied_page_verified": False,
        },
    ]

    proc = run_builder(tmp_path, result, ledger_rows)

    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["applications"] == []
