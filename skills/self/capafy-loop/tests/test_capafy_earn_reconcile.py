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


def test_daily_reconciles_before_full_first_version_queue_action_selection(tmp_path: Path) -> None:
    _fixtures(tmp_path)
    home = tmp_path / "home"
    publisher = home / "publisher"
    publisher.mkdir(parents=True)
    publish_list = publisher / "packager.py"
    publish_list.write_text(
        "import json,os,sys\n"
        "from pathlib import Path\n"
        "calls=Path(os.environ['INVENTORY_CALLS']); calls.write_text(str(int(calls.read_text())+1) if calls.exists() else '1')\n"
        "Path(os.environ['ORDER_MARKER']).write_text('ready' if Path(os.environ['CAPAFY_RECONCILE_LEDGER']).exists() else 'missing')\n"
        "statuses=[('online',True)]*21+[('review_rejected',False)]*5+[('review_rejected',True)]*4+[('draft',True)]*2\n"
        "agents=[{'agentId':str(1000000000+i),'agentStatus':s,'hasOnlineVersion':v,'latestAgentVersionId':str(2000000000+i),'updatedAt':1785000000000+i} for i,(s,v) in enumerate(statuses)]\n"
        "print(json.dumps({'agents':{'list':agents}})); raise SystemExit(int(os.environ.get('INVENTORY_EXIT','0')))\n"
    )
    guard_probe = tmp_path / "guard-probe.py"
    guard_probe.write_text(
        "import os,sys\n"
        "sys.path.insert(0, os.environ['CAPAFY_PUBLISHER_ROOT'])\n"
        "import capafy_platform.api as api\n"
        "api.post_platform_json=lambda path,*args,**kwargs:{'path':path}\n"
        "try: api.create_agent({})\n"
        "except ValueError as exc: assert 'first-version review queue is full' in str(exc)\n"
        "else: raise AssertionError('new addAgent was not blocked')\n"
        "assert api.create_agent_version({})['path'].endswith('/addAgentVersion')\n"
        "open(os.environ['GUARD_MARKER'],'w').write('blocked-new-allowed-version')\n"
    )
    sender = tmp_path / "sender.sh"
    sender.write_text("#!/usr/bin/env bash\nprintf 'MSGID=1\\n'\n")
    sender.chmod(0o755)
    runner = tmp_path / "run-agent.sh"
    runner.write_text(
        "#!/usr/bin/env bash\n"
        "touch \"$RUN_AGENT_MARKER\"\n"
        "cat > \"$PROMPT_CAPTURE\"\n"
        "python3 \"$GUARD_PROBE\"\n"
        "printf '%s\\n' \"$RUN_AGENT_RESULT\" > \"$CAPAFY_BUILDER_RESULT\"\n"
    )
    runner.chmod(0o755)
    fixer = tmp_path / "self-fix.sh"
    fixer.write_text("#!/usr/bin/env bash\nexit 0\n")
    fixer.chmod(0o755)
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
        "CAPAFY_RUN_AGENT": str(runner),
        "CAPAFY_PUBLISH_LIST": str(publish_list),
        "CAPAFY_PORTFOLIO_STATE": str(tmp_path / "portfolio.json"),
        "CAPAFY_PUBLISHER_ROOT": str(Path.home() / ".openclaw/skills/capafy-autopublish/vendor/capafy-publisher"),
        "RUN_AGENT_MARKER": str(tmp_path / "run-agent-marker"),
        "GUARD_PROBE": str(guard_probe),
        "GUARD_MARKER": str(tmp_path / "guard-marker"),
        "PROMPT_CAPTURE": str(tmp_path / "prompt.txt"),
        "INVENTORY_CALLS": str(tmp_path / "inventory-calls"),
        "INVENTORY_EXIT": "0",
        "CAPAFY_SELF_FIX": str(fixer),
        "RUN_AGENT_RESULT": '{"result":"no_op","reason":"no rejected Agent has a verified safe correction yet"}',
    })
    result = subprocess.run(["bash", str(DAILY)], text=True, capture_output=True, env=env, check=False)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "order-marker").read_text() == "ready"
    assert (tmp_path / "run-agent-marker").exists()
    assert (tmp_path / "guard-marker").read_text() == "blocked-new-allowed-version"
    prompt = (tmp_path / "prompt.txt").read_text()
    assert "FIRST-VERSION REVIEW QUEUE FULL" in prompt
    assert "never_online=5, total=32, online=21, review_rejected=9, draft=2" in prompt
    assert "New addAgent creation is forbidden" in prompt
    assert "addAgentVersion for an existing agent_id remains allowed" in prompt
    assert prompt.rstrip().endswith("Use only the existing Capafy commands already named in this prompt.")
    assert "poll_review, measure, repair_rejected, reposition, retire_candidate, optimize_packaging, handoff_marketing, no_op" in prompt
    for forbidden in (
        "publishing ONE more", "brand-new", "PHASE B", "PACKAGING DEFAULT",
        "NEVER Download", "ONE paid week plan", "$9.99/week", "Portfolio Tracker",
    ):
        assert forbidden not in prompt
    assert "Creating a new Agent" in prompt and "it is never mandatory" in prompt
    assert "Do not assume a purchase model, delivery mode, price, trial, or cap" in prompt
    assert "recurring changing input = subscription" in prompt
    assert "value proportional to actions/results = usage" in prompt
    assert "one bounded deliverable = one_time" in prompt
    assert "combined recurring and metered/bounded value = hybrid" in prompt
    assert "capafy_packaging_decision.py" in prompt
    assert "missing economics must end as no_op or failure" in prompt
    assert (tmp_path / "inventory-calls").read_text() == "1"
    synced = json.loads((tmp_path / "portfolio.json").read_text())
    assert len(synced["products"]) == 32
    assert sum(not p["has_online_version"] for p in synced["products"]) == 5

    Path(env["RUN_AGENT_MARKER"]).unlink()
    env["INVENTORY_EXIT"] = "7"
    blocked = subprocess.run(["bash", str(DAILY)], text=True, capture_output=True, env=env, check=False)
    assert blocked.returncode != 0
    assert not Path(env["RUN_AGENT_MARKER"]).exists()
    assert (tmp_path / "inventory-calls").read_text() == "2"


def test_shared_inventory_counts_only_never_online_agents(capsys: pytest.CaptureFixture[str]) -> None:
    script = Path.home() / ".openclaw/skills/capafy-autopublish/scripts/inventory_status.py"
    spec = importlib.util.spec_from_file_location("capafy_inventory_status", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.ready_inventory = lambda: []
    module._load_archive = lambda: {}
    module._save_archive = lambda archive: None

    existing_versions = [
        {"name": f"existing-{i}", "agentStatus": "review_rejected", "hasOnlineVersion": True}
        for i in range(6)
    ]
    module.server_agents = lambda: existing_versions + [
        {"name": f"new-{i}", "agentStatus": "draft", "hasOnlineVersion": False}
        for i in range(5)
    ]
    assert module.main() == 0
    full = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert full["verdict"] == "CAP_FULL"
    assert full["never_online_count"] == 5
    assert full["cap_occupied_count"] == 5

    module.server_agents = lambda: existing_versions + [
        {"name": f"new-{i}", "agentStatus": "draft", "hasOnlineVersion": False}
        for i in range(4)
    ]
    assert module.main() == 0
    open_slot = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert open_slot["verdict"] == "DRAINED"
    assert open_slot["never_online_count"] == 4

    module.server_agents = lambda: [{"name": "unknown", "agentStatus": "draft"}]
    assert module.main() == 0
    malformed = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert malformed["verdict"] == "SERVER_UNREADABLE"


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
