import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "capafy_earn_reconcile.py"


def _fixtures(tmp_path: Path) -> tuple[Path, Path]:
    sales = tmp_path / "sales.json"
    payout = tmp_path / "payout.json"
    sales.write_text(
        json.dumps(
            {
                "data": {
                    "data": [
                        {
                            "date": "2026-06-23",
                            "orders": 1,
                            "revenue": 9.99,
                            "netRevenue": 9.99,
                        }
                    ]
                }
            }
        )
    )
    payout.write_text(
        json.dumps(
            {
                "data": {
                    "balancePayout": 8.0,
                    "totalPayout": 0.0,
                    "currency": "usd",
                    "accountNumber": "****1900",
                }
            }
        )
    )
    return sales, payout


def _sync_stub(tmp_path: Path, exit_code: int) -> tuple[Path, Path]:
    calls = tmp_path / "sync-calls.jsonl"
    stub = tmp_path / "event-sync.py"
    stub.write_text(
        "#!/usr/bin/env python3\n"
        "import json,os,sys\n"
        "with open(os.environ['SYNC_CALLS'],'a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')\n"
        f"raise SystemExit({exit_code})\n"
    )
    stub.chmod(0o755)
    return stub, calls


def _run(tmp_path: Path, sync_exit: int) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    sales, payout = _fixtures(tmp_path)
    sync, calls = _sync_stub(tmp_path, sync_exit)
    source_ledger = tmp_path / "capafy-earn-ledger.jsonl"
    event_ledger = tmp_path / "capafy-revenue-events.jsonl"
    environment = os.environ.copy()
    environment.update(
        {
            "CAPAFY_EVENT_SYNC": str(sync),
            "CAPAFY_EVENT_LEDGER": str(event_ledger),
            "CAPAFY_EVENT_EVIDENCE_DIR": str(tmp_path / "event-evidence"),
            "CAPAFY_EVENT_COST_LOG": str(tmp_path / "cost.log"),
            "SYNC_CALLS": str(calls),
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--sales-json",
            str(sales),
            "--payout-json",
            str(payout),
            "--ledger",
            str(source_ledger),
        ],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    return result, source_ledger, calls


def test_reconcile_syncs_money_after_source_ledger_write(tmp_path: Path) -> None:
    result, source_ledger, calls = _run(tmp_path, 0)

    assert result.returncode == 0, result.stderr
    arguments = json.loads(calls.read_text().splitlines()[0])
    assert arguments[:3] == ["sync-money", "--money-ledger", str(source_ledger)]
    assert "--cost-log" in arguments
    assert "--ledger" in arguments
    assert "--evidence-dir" in arguments


def test_sync_failure_keeps_source_evidence_but_fails_reconcile(tmp_path: Path) -> None:
    result, source_ledger, calls = _run(tmp_path, 7)

    assert result.returncode != 0
    assert source_ledger.exists()
    assert len(source_ledger.read_text().splitlines()) == 2
    assert calls.exists()
    assert "event sync failed" in result.stderr
