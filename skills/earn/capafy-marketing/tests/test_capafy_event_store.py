import copy
import json
import multiprocessing
import os
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capafy_event_store as store
from capafy_event_store import validate_event


def valid_event() -> dict:
    return {
        "schema_version": 1,
        "event_id": "capafy:content.published:instagram:DbgsvEbo5kd",
        "event_type": "content.published",
        "occurred_at": "2026-08-01T20:32:53Z",
        "recorded_at": "2026-08-01T20:32:54Z",
        "loop": "marketer",
        "entity": {"type": "content", "id": "instagram:DbgsvEbo5kd"},
        "correlation_id": "capafy-marketer-20260801T164641Z-4e195cd6",
        "summary": "Published and owner-verified an Instagram Reel.",
        "status": {"before": "publish_probe_ready", "after": "reach_observing"},
        "money": {
            "currency": "USD",
            "gross_delta": "0.00",
            "pending_delta": "0.00",
            "realized_delta": "0.00",
            "mrr_delta": "0.00",
            "cost_delta": "0.00",
            "contribution_delta": "0.00",
        },
        "metrics": {},
        "public_evidence": {
            "urls": ["https://www.instagram.com/reel/DbgsvEbo5kd/"],
            "labels": ["post-write owner session verified"],
        },
        "technical_evidence_ref": "capafy:content.published:instagram:DbgsvEbo5kd",
        "source": {
            "producer": "capafy-marketing-handoff",
            "source_id": "marketing-published:DbgsvEbo5kd",
            "source_digest": "sha256:" + "a" * 64,
        },
        "next": {"owner": "marketer", "retry_at": None},
    }


def test_validation_accepts_complete_event() -> None:
    assert validate_event(valid_event()) == []


def test_validation_rejects_missing_event_id() -> None:
    event = valid_event()
    event.pop("event_id")

    assert "event_id is required" in validate_event(event)


def test_validation_rejects_unsupported_event_type() -> None:
    event = valid_event()
    event["event_type"] = "revenue.claimed"

    assert "unsupported event_type: 'revenue.claimed'" in validate_event(event)


def test_validation_rejects_event_id_that_can_escape_the_evidence_directory() -> None:
    event = valid_event()
    event["event_id"] = "../private/escape"

    assert "event_id contains unsupported characters" in validate_event(event)


def test_validation_rejects_http_public_evidence_url() -> None:
    event = valid_event()
    event["public_evidence"]["urls"] = ["http://instagram.com/reel/DbgsvEbo5kd/"]

    assert "public_evidence.urls must contain only HTTPS URLs" in validate_event(event)


def test_validation_rejects_absolute_local_path_anywhere_in_public_event() -> None:
    event = valid_event()
    event["summary"] = "Rendered from /Users/anicca/private/evidence.json"

    assert "public event contains a private local path" in validate_event(event)


def test_validation_rejects_money_without_exactly_two_fractional_digits() -> None:
    event = valid_event()
    event["money"]["gross_delta"] = "9.9"

    assert "money.gross_delta must be a two-decimal string" in validate_event(event)


def test_validation_rejects_negative_metric() -> None:
    event = valid_event()
    event["metrics"] = {"clicks": -1}

    assert "metrics.clicks must be a non-negative integer" in validate_event(event)


def test_validation_rejects_invalid_timestamp() -> None:
    event = valid_event()
    event["occurred_at"] = "yesterday"

    assert "occurred_at must be an RFC3339 UTC timestamp" in validate_event(event)


def test_validation_rejects_credential_bearing_key_recursively() -> None:
    event = valid_event()
    event["public_evidence"]["authorization"] = "redacted"

    assert "public event contains a credential-bearing key" in validate_event(event)


def test_validation_does_not_mutate_the_event() -> None:
    event = valid_event()
    before = copy.deepcopy(event)

    validate_event(event)

    assert event == before


def _append_worker(ledger: str, evidence_dir: str, result_queue) -> None:
    event = valid_event()
    event.pop("recorded_at")
    try:
        result = store.append_event(Path(ledger), event, None, Path(evidence_dir))
        result_queue.put(("ok", result.appended))
    except Exception as exc:  # pragma: no cover - asserted in parent process
        result_queue.put(("error", repr(exc)))


def test_identical_retry_is_a_noop_even_when_recorded_at_changes(tmp_path: Path) -> None:
    ledger = tmp_path / "capafy-revenue-events.jsonl"
    evidence_dir = tmp_path / "evidence"
    first = valid_event()
    first.pop("recorded_at")

    initial = store.append_event(ledger, first, None, evidence_dir)
    retry = valid_event()
    retry["recorded_at"] = "2026-08-02T00:00:00Z"
    repeated = store.append_event(ledger, retry, None, evidence_dir)

    assert initial.appended is True
    assert repeated.appended is False
    assert repeated.ledger_count == 1
    assert len(store.read_events(ledger)) == 1


def test_same_id_with_different_semantic_payload_is_a_conflict(tmp_path: Path) -> None:
    ledger = tmp_path / "capafy-revenue-events.jsonl"
    event = valid_event()
    store.append_event(ledger, event, None, tmp_path / "evidence")
    event["summary"] = "A conflicting public claim."

    with pytest.raises(ValueError, match="event_id conflict"):
        store.append_event(ledger, event, None, tmp_path / "evidence")

    assert len(ledger.read_text().splitlines()) == 1


def test_concurrent_writers_append_exactly_one_line(tmp_path: Path) -> None:
    ledger = tmp_path / "capafy-revenue-events.jsonl"
    evidence_dir = tmp_path / "evidence"
    context = multiprocessing.get_context("spawn")
    result_queue = context.Queue()
    workers = [
        context.Process(target=_append_worker, args=(str(ledger), str(evidence_dir), result_queue))
        for _ in range(4)
    ]

    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=10)

    results = [result_queue.get(timeout=2) for _ in workers]
    assert all(worker.exitcode == 0 for worker in workers)
    assert all(kind == "ok" for kind, _ in results)
    assert sorted(appended for _, appended in results) == [False, False, False, True]
    assert len(ledger.read_text().splitlines()) == 1


def test_truncated_tail_refuses_new_append_without_rewriting_it(tmp_path: Path) -> None:
    ledger = tmp_path / "capafy-revenue-events.jsonl"
    broken = '{"event_id":"truncated"'
    ledger.write_text(broken)

    with pytest.raises(ValueError, match="invalid ledger JSON"):
        store.append_event(ledger, valid_event(), None, tmp_path / "evidence")

    assert ledger.read_text() == broken


def test_private_sidecar_is_mode_0600_and_not_embedded_in_public_ledger(tmp_path: Path) -> None:
    ledger = tmp_path / "capafy-revenue-events.jsonl"
    evidence_dir = tmp_path / "evidence"
    evidence = {"browser_profile": "/Users/anicca/private/profile", "cookie": "private"}

    result = store.append_event(ledger, valid_event(), evidence, evidence_dir)

    sidecar = Path(result.evidence_path or "")
    assert sidecar.exists()
    assert os.stat(sidecar).st_mode & 0o777 == 0o600
    assert json.loads(sidecar.read_text()) == evidence
    assert "browser_profile" not in ledger.read_text()
    assert "cookie" not in ledger.read_text()


def test_canonical_event_bytes_are_compact_sorted_and_stable() -> None:
    event = valid_event()
    reordered = dict(reversed(list(event.items())))

    encoded = store.canonical_event_bytes(event)

    assert encoded == store.canonical_event_bytes(reordered)
    assert encoded.startswith(b'{"correlation_id":')
    assert b"\n" not in encoded
    assert b": " not in encoded


def test_append_and_read_cli_round_trip_public_event_and_private_evidence(
    tmp_path: Path,
) -> None:
    script = SCRIPTS / "capafy_event_store.py"
    ledger = tmp_path / "capafy-revenue-events.jsonl"
    evidence_dir = tmp_path / "evidence"
    event = valid_event()
    event.pop("recorded_at")
    environment = os.environ.copy()
    environment["CAPAFY_EVENT_EVIDENCE_JSON"] = json.dumps(
        {"browser_profile": "/Users/anicca/private/profile"}
    )

    appended = subprocess.run(
        [
            sys.executable,
            str(script),
            "append",
            "--ledger",
            str(ledger),
            "--evidence-dir",
            str(evidence_dir),
        ],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    read = subprocess.run(
        [sys.executable, str(script), "read", "--ledger", str(ledger)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert appended.returncode == 0, appended.stderr
    assert json.loads(appended.stdout) == {
        "appended": True,
        "event_id": "capafy:content.published:instagram:DbgsvEbo5kd",
        "evidence_path": str(
            evidence_dir / "capafy:content.published:instagram:DbgsvEbo5kd.json"
        ),
        "ledger_count": 1,
    }
    assert read.returncode == 0, read.stderr
    events = json.loads(read.stdout)["events"]
    assert len(events) == 1
    assert events[0]["event_id"] == event["event_id"]
    assert events[0]["recorded_at"].endswith("Z")
    assert "browser_profile" not in read.stdout
