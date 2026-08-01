import importlib.util
import json
import os
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "ig_metrics.py"
SPEC = importlib.util.spec_from_file_location("ig_metrics", SCRIPT)
ig_metrics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ig_metrics)


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


def _setup(monkeypatch, tmp_path: Path, sync_exit: int) -> tuple[Path, Path]:
    source = tmp_path / "ig-ledger.jsonl"
    metrics = tmp_path / "ig-metrics.jsonl"
    source.write_text(
        json.dumps(
            {
                "reel_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
                "agent_id": "4866150011",
                "listing_name": "Decision Debate",
            }
        )
        + "\n"
    )
    sync, calls = _sync_stub(tmp_path, sync_exit)
    monkeypatch.setattr(ig_metrics, "IGLEDGER", str(source))
    monkeypatch.setattr(ig_metrics, "METRICS", str(metrics))
    monkeypatch.setattr(ig_metrics, "MARKETING_TERMINAL", str(tmp_path / "missing-terminal.json"))
    monkeypatch.setattr(ig_metrics, "ACCOUNTS", str(tmp_path / "missing-accounts.json"))
    monkeypatch.setattr(
        ig_metrics,
        "_read",
        lambda _url, _handle, _port: {"views": 3, "likes": 1, "comments": 0},
    )
    monkeypatch.setenv("CAPAFY_EVENT_SYNC", str(sync))
    monkeypatch.setenv("CAPAFY_EVENT_LEDGER", str(tmp_path / "events.jsonl"))
    monkeypatch.setenv("CAPAFY_EVENT_EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("SYNC_CALLS", str(calls))
    return metrics, calls


def test_metrics_snapshot_invokes_event_sync(monkeypatch, tmp_path: Path) -> None:
    metrics, calls = _setup(monkeypatch, tmp_path, 0)

    result = ig_metrics.main()

    assert result == 0
    assert len(metrics.read_text().splitlines()) == 1
    arguments = json.loads(calls.read_text().splitlines()[0])
    assert arguments[:3] == ["sync-metrics", "--metrics-ledger", str(metrics)]
    assert "--ledger" in arguments
    assert "--evidence-dir" in arguments


def test_sync_failure_keeps_metric_snapshot_and_fails_pass(monkeypatch, tmp_path: Path) -> None:
    metrics, calls = _setup(monkeypatch, tmp_path, 7)

    result = ig_metrics.main()

    assert result != 0
    assert len(metrics.read_text().splitlines()) == 1
    assert calls.exists()


def test_verified_marketing_terminal_is_measured_without_legacy_ig_ledger(
    monkeypatch, tmp_path: Path
) -> None:
    missing_legacy = tmp_path / "missing-ig-ledger.jsonl"
    terminal = tmp_path / "capafy-marketing-terminal.json"
    accounts = tmp_path / "capafy-accounts.json"
    metrics = tmp_path / "ig-metrics.jsonl"
    terminal.write_text(
        json.dumps(
            {
                "telegram_message_id": "5166",
                "outcome": {
                    "kind": "marketing_published",
                    "handle": "capafy.skills8m4q2z",
                    "agent_id": "4866150011",
                    "title": "Decision Debate",
                    "reel_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
                    "owner_session_verified": True,
                },
            }
        )
    )
    accounts.write_text(
        json.dumps(
            [
                {
                    "handle": "capafy.skills8m4q2z",
                    "port": 65063,
                    "session_owner": "browser",
                }
            ]
        )
    )
    sync, calls = _sync_stub(tmp_path, 0)
    read_urls = []
    monkeypatch.setattr(ig_metrics, "IGLEDGER", str(missing_legacy))
    monkeypatch.setattr(ig_metrics, "MARKETING_TERMINAL", str(terminal))
    monkeypatch.setattr(ig_metrics, "ACCOUNTS", str(accounts))
    monkeypatch.setattr(ig_metrics, "METRICS", str(metrics))
    monkeypatch.setattr(
        ig_metrics,
        "_read",
        lambda url, handle, port: read_urls.append((url, handle, port))
        or {"views": 95, "likes": None, "comments": None},
    )
    monkeypatch.setenv("CAPAFY_EVENT_SYNC", str(sync))
    monkeypatch.setenv("CAPAFY_EVENT_LEDGER", str(tmp_path / "events.jsonl"))
    monkeypatch.setenv("CAPAFY_EVENT_EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("SYNC_CALLS", str(calls))

    result = ig_metrics.main()

    assert result == 0
    assert read_urls == [
        ("https://www.instagram.com/reel/DbgsvEbo5kd/", "capafy.skills8m4q2z", 65063)
    ]
    snapshot = json.loads(metrics.read_text().splitlines()[0])
    assert snapshot["agent_id"] == "4866150011"
    assert snapshot["views"] == 95
    assert snapshot["likes"] is None
    assert snapshot["comments"] is None
    assert calls.exists()


def test_browser_read_failure_is_not_recorded_as_zero_engagement(
    monkeypatch, tmp_path: Path
) -> None:
    metrics, calls = _setup(monkeypatch, tmp_path, 0)
    monkeypatch.setattr(ig_metrics, "_read", lambda _url, _handle, _port: {})

    result = ig_metrics.main()

    assert result != 0
    assert not metrics.exists()
    assert not calls.exists()
