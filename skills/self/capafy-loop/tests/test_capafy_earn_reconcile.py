import json
import importlib.util
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import pytest


SCRIPT = Path(__file__).parents[1] / "capafy_earn_reconcile.py"
DAILY = SCRIPT.parent / "capafy-loop-daily.sh"
CANONICAL_SYNC = SCRIPT.parents[2] / "earn/capafy-marketing/scripts/capafy_event_sync.py"


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


def _run(tmp_path: Path, sync_exit: int, seed: list[dict] | None = None, payout_payload: dict | None = None, sales_payload: dict | None = None, sync_path: Path | None = None) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    sales, payout = _fixtures(tmp_path)
    if payout_payload is not None:
        payout.write_text(json.dumps(payout_payload))
    if sales_payload is not None:
        sales.write_text(json.dumps(sales_payload))
    sync, calls = (sync_path, tmp_path / "sync-calls.jsonl") if sync_path else _sync_stub(tmp_path, sync_exit)
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


def test_canonical_sync_same_day_retry_is_idempotent(tmp_path: Path) -> None:
    first, ledger, _ = _run(tmp_path, 0, sync_path=CANONICAL_SYNC)
    time.sleep(1.1)
    second, _, _ = _run(tmp_path, 0, sync_path=CANONICAL_SYNC)
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert len((tmp_path / "capafy-revenue-events.jsonl").read_text().splitlines()) == 6
    payout = next(json.loads(line) for line in ledger.read_text().splitlines() if '"source": "capafy-payout"' in line)
    assert payout["ts"] == int(datetime.strptime(payout["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def test_canonical_sync_preserves_legacy_payout_event(tmp_path: Path) -> None:
    legacy = {
        "ts": 1784330227,
        "source": "capafy-payout",
        "date": "2026-07-18",
        "balance_payout_usd": 8.0,
        "total_payout_usd": 0.0,
        "balance_pending_usd": 6.4,
        "balance_confirmed_usd": 0.0,
        "currency": "usd",
        "channel": "capafy_bank_wire",
        "account": "",
        "note": "legacy payout snapshot",
        "wake": "capafy_earn_reconcile",
    }
    source = tmp_path / "capafy-earn-ledger.jsonl"
    source.write_text(json.dumps(legacy) + "\n")
    event_ledger = tmp_path / "capafy-revenue-events.jsonl"
    seeded = subprocess.run(
        [sys.executable, str(CANONICAL_SYNC), "sync-money", "--money-ledger", str(source), "--cost-log", str(tmp_path / "cost.log"), "--ledger", str(event_ledger), "--evidence-dir", str(tmp_path / "event-evidence")],
        text=True,
        capture_output=True,
        check=False,
    )
    assert seeded.returncode == 0, seeded.stderr
    result, _, _ = _run(tmp_path, 0, seed=[legacy], sync_path=CANONICAL_SYNC)
    assert result.returncode == 0, result.stderr


def test_payout_failure_preserves_previous_source_evidence(tmp_path: Path) -> None:
    first, ledger, calls = _run(tmp_path, 0)
    before, sync_before = ledger.read_bytes(), calls.read_bytes()
    assert first.returncode == 0
    for payload in ({"code": 503, "message": "unavailable"}, {"data": []}):
        failed, _, calls_after = _run(tmp_path, 0, payout_payload=payload)
        assert failed.returncode != 0 and "payout" in failed.stderr
        assert ledger.read_bytes() == before and calls_after.read_bytes() == sync_before


def test_nonfinite_payout_preserves_previous_source_evidence(tmp_path: Path) -> None:
    first, ledger, calls = _run(tmp_path, 0)
    before, sync_before = ledger.read_bytes(), calls.read_bytes()
    failed, _, calls_after = _run(tmp_path, 0, payout_payload={"data": {"balancePayout": "NaN", "balancePending": "Infinity", "balanceConfirmed": 0, "totalPayout": 0}})
    assert first.returncode == 0
    assert failed.returncode != 0 and "payout" in failed.stderr
    assert ledger.read_bytes() == before and calls_after.read_bytes() == sync_before


def test_nonfinite_sales_preserves_previous_source_evidence(tmp_path: Path) -> None:
    first, ledger, calls = _run(tmp_path, 0)
    before, sync_before = ledger.read_bytes(), calls.read_bytes()
    failed, _, calls_after = _run(tmp_path, 0, sales_payload={"data": {"data": [{"date": "2026-08-12", "orders": 1, "revenue": "NaN", "netRevenue": "Infinity", "refundAmount": "NaN"}]}})
    assert first.returncode == 0
    assert failed.returncode != 0 and "sales" in failed.stderr
    assert ledger.read_bytes() == before and calls_after.read_bytes() == sync_before


def test_malformed_numeric_values_preserve_previous_source_evidence(tmp_path: Path) -> None:
    first, ledger, calls = _run(tmp_path, 0)
    before, sync_before = ledger.read_bytes(), calls.read_bytes()
    payout_fields = ("balancePayout", "balancePending", "balanceConfirmed", "totalPayout")
    for field in payout_fields:
        for bad in (None, [], {}):
            payout = {name: 0 for name in payout_fields}
            payout[field] = bad
            failed, _, calls_after = _run(tmp_path, 0, payout_payload={"data": payout})
            assert failed.returncode != 0 and "payout" in failed.stderr
            assert ledger.read_bytes() == before and calls_after.read_bytes() == sync_before
    sales_fields = ("orders", "revenue", "netRevenue", "refundAmount", "newBuyers")
    for field in sales_fields:
        for bad in (None, [], {}):
            row = {name: 1 for name in sales_fields} | {"date": "2026-08-12"}
            row[field] = bad
            failed, _, calls_after = _run(tmp_path, 0, sales_payload={"data": {"data": [row]}})
            assert failed.returncode != 0 and "sales" in failed.stderr
            assert ledger.read_bytes() == before and calls_after.read_bytes() == sync_before


def test_sales_window_failure_does_not_return_partial_rows() -> None:
    spec = importlib.util.spec_from_file_location("reconcile", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module._date_windows = lambda _: iter([("2026-08-01", "2026-08-07"), ("2026-08-08", "2026-08-13")])
    module._get = lambda path, token: {"code": 503, "message": "window unavailable"} if "2026-08-08" in path else {"code": 0, "data": {"data": [{"date": "2026-08-01", "orders": 1, "revenue": 1.0}]}}
    with pytest.raises(RuntimeError, match="sales window"):
        module.fetch_sales("token", 14)


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
    assert arguments[:2] == ["sync-money", "--money-ledger"]
    assert arguments[2] == str(source_ledger)
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
