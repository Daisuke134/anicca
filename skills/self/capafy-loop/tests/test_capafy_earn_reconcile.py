import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "capafy_earn_reconcile.py"
DAILY = SCRIPT.parent / "capafy-loop-daily.sh"


def _fixtures(tmp_path: Path) -> tuple[Path, Path]:
    sales, payout = tmp_path / "cap_trend.json", tmp_path / "cap_payout.json"
    rows = [("2026-06-23", 9.99), ("2026-08-05", 0.0), ("2026-08-08", 9.99), ("2026-08-10", 0.0), ("2026-08-12", 0.0)]
    sales.write_text(json.dumps({"data": {"data": [{"date": d, "orders": 1, "revenue": n, "netRevenue": n, "refundAmount": 0.0} for d, n in rows]}}))
    payout.write_text(json.dumps({"data": {"balancePayout": 8.0, "balancePending": 6.4, "balanceConfirmed": 0.0, "totalPayout": 0.0, "currency": "usd"}}))
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


def _run(tmp_path: Path, sync_exit: int, seed: list[dict] | None = None) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
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
    if seed:
        source_ledger.write_text("".join(json.dumps(row) + "\n" for row in seed))
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


def test_authoritative_fixture_upserts_stale_rows_and_keeps_zero_dollar_orders(tmp_path: Path) -> None:
    stale = [{"source": "capafy-sales", "date": "2026-08-08", "orders": 1, "gross_usd": 0.0}]
    first, ledger, _ = _run(tmp_path, 0, stale)
    summary = json.loads(first.stdout)
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    sales_rows = [row for row in rows if row.get("source") == "capafy-sales"]
    assert summary["lifetime_orders"] == 5
    assert summary["lifetime_gross_usd"] == 19.98
    assert summary["balance_payout_usd"] == 8.0 and summary["total_payout_usd"] == 0.0
    assert len(sales_rows) == 5
    assert sum(row["gross_usd"] > 0 for row in sales_rows) == 2
    assert sum(row["refund_amount_usd"] for row in sales_rows) == 0
    assert {row["date"] for row in sales_rows if row["gross_usd"] == 0} == {"2026-08-05", "2026-08-10", "2026-08-12"}
    assert not any(key in row for row in sales_rows if row["gross_usd"] == 0 for key in ("product", "trial", "subscription"))

    second, _, _ = _run(tmp_path, 0)
    second_rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    for data in (rows, second_rows):
        for row in data:
            if row.get("source") == "capafy-payout":
                row["ts"] = 0
    assert rows == second_rows
    assert json.loads(second.stdout)["lifetime_gross_usd"] == 19.98


def test_daily_reconciles_before_cap_full_builder_return(tmp_path: Path) -> None:
    _fixtures(tmp_path)
    home = tmp_path / "home"
    inventory = home / ".openclaw/skills/capafy-autopublish/scripts/inventory_status.py"
    inventory.parent.mkdir(parents=True)
    inventory.write_text("import os; from pathlib import Path; Path(os.environ['ORDER_MARKER']).write_text('ready' if Path(os.environ['CAPAFY_RECONCILE_LEDGER']).exists() else 'missing'); print('VERDICT=CAP_FULL'); print('{\"online_count\": 5}')\n")
    sender = tmp_path / "sender.sh"
    sender.write_text("#!/usr/bin/env bash\nprintf 'MSGID=1\\n'\n")
    sender.chmod(0o755)
    sync, calls = _sync_stub(tmp_path, 0)
    money = tmp_path / "money.json"; money.write_text('{"gross_usd":19.98,"pending_usd":8,"realized_usd":0,"mrr_usd":0,"cost_usd":0,"contribution_usd":0}')
    env = os.environ.copy()
    env.update({
        "HOME": str(home),
        "CAPAFY_TEST": "1",
        "CAPAFY_FIXTURE": str(tmp_path),
        "CAPAFY_RECONCILE_LEDGER": str(tmp_path / "capafy-earn-ledger.jsonl"),
        "ORDER_MARKER": str(tmp_path / "order-marker"),
        "CAPAFY_BUILDER_RESULT": str(tmp_path / "builder-result.json"),
        "CAPAFY_MONEY_JSON": str(money),
        "CAPAFY_OUTCOME_STATE_DIR": str(tmp_path / "outcome-state"),
        "CAPAFY_EVENT_LEDGER": str(tmp_path / "events.jsonl"),
        "CAPAFY_EVENT_EVIDENCE_DIR": str(tmp_path / "event-evidence"),
        "CAPAFY_TELEGRAM_SENDER": str(sender),
        "CAPAFY_EVENT_SYNC": str(sync),
        "SYNC_CALLS": str(calls),
    })
    result = subprocess.run(["bash", str(DAILY)], text=True, capture_output=True, env=env, check=False)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "order-marker").read_text() == "ready"


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
    assert len(source_ledger.read_text().splitlines()) == 6
    assert calls.exists()
    assert "event sync failed" in result.stderr
