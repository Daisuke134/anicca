from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import b0_result_gate  # noqa: E402
import lane_productivity  # noqa: E402


def write_runner_result(
    root: Path,
    *,
    context: Path,
    action: str,
    service_id: str | None = None,
    url: str | None = None,
) -> tuple[Path, Path]:
    evidence = root / "agent-B0"
    evidence.mkdir()
    screenshot = evidence / "listing.png"
    live_dom = evidence / "listing.json"
    if action != "verified_noop":
        assert url
        screenshot.write_bytes(b"real screenshot")
        live_dom.write_text(
            json.dumps(
                {
                    "url": url,
                    "not_found": False,
                    "observed": True,
                    "title": "Verified listing",
                }
            ),
            encoding="utf-8",
        )
    result = evidence / "attempt-01.result.json"
    result.write_text(
        json.dumps(
            {
                "status": "ok",
                "summary": f"B0 {action}",
                "evidence": ["fresh storefront evidence"],
                "current_b0": {
                    "context_path": str(context),
                    "context_sha256": hashlib.sha256(context.read_bytes()).hexdigest(),
                    "action": action,
                    "service_id": service_id,
                    "url": url,
                    "title": "Verified listing" if action != "verified_noop" else None,
                    "screenshot_path": (
                        str(screenshot) if action != "verified_noop" else None
                    ),
                    "live_dom_path": (
                        str(live_dom) if action != "verified_noop" else None
                    ),
                    "reason": "No safe storefront change was due.",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    summary = evidence / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "status": "success",
                "task_label": "gig-B0",
                "result_path": str(result),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return summary, evidence


def make_context(
    root: Path,
    ledger: Path,
    pass_id: str = "pass-1",
    decision: dict | None = None,
) -> Path:
    context = root / "b0-context.json"
    context.write_text(
        json.dumps(
            b0_result_gate.build_context(
                decision
                or {"action": "create_listing", "objective": "Create one listing"},
                ledger,
                pass_id,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return context


@pytest.mark.parametrize("action", ["created", "verified_noop"])
def test_capacity_recovery_rejects_create_and_noop(
    tmp_path: Path, action: str
) -> None:
    ledger = tmp_path / "gig" / "shuppin.jsonl"
    ledger.parent.mkdir()
    context = make_context(
        tmp_path,
        ledger,
        decision={
            "action": "recover_existing",
            "objective": "Reuse an existing listing slot",
            "must_reuse_existing": True,
        },
    )
    assert json.loads(context.read_text())["must_reuse_existing"] is True
    summary, evidence = write_runner_result(
        tmp_path,
        context=context,
        action=action,
        service_id="4339999" if action == "created" else None,
        url=(
            "https://coconala.com/services/4339999"
            if action == "created"
            else None
        ),
    )

    with pytest.raises(
        b0_result_gate.ContractError,
        match="capacity_recovery_requires_existing_effect",
    ):
        b0_result_gate.reconcile(
            context_path=context,
            summary_path=summary,
            evidence_dir=evidence,
            ledger_path=ledger,
            min_mtime=0,
            now=1_000,
        )


def test_capacity_failure_builds_one_live_update_retry_context(
    tmp_path: Path,
) -> None:
    context = tmp_path / "b0-context.json"
    context.write_text(json.dumps({
        "version": 1,
        "pass_id": "pass-1",
        "canonical_ledger_path": str(tmp_path / "shuppin.jsonl"),
        "objective_action": "recover_existing",
        "objective": "Recover an existing listing",
        "must_reuse_existing": True,
    }))
    gate_result = tmp_path / "gate-result.json"
    gate_result.write_text(json.dumps({
        "ok": False,
        "error": "capacity_recovery_requires_existing_effect",
    }))

    retry = b0_result_gate.prepare_capacity_retry(
        gate_result_path=gate_result,
        context_path=context,
        attempt=0,
    )

    assert retry["objective_action"] == "improve_existing_after_capacity"
    assert retry["must_reuse_existing"] is True
    assert "Do not publish or resume a draft" in retry["objective"]
    assert "verified_noop" in retry["objective"]
    with pytest.raises(
        b0_result_gate.ContractError,
        match="b0_capacity_retry_exhausted",
    ):
        b0_result_gate.prepare_capacity_retry(
            gate_result_path=gate_result,
            context_path=context,
            attempt=1,
        )


def test_non_capacity_failure_cannot_trigger_listing_retry(tmp_path: Path) -> None:
    context = tmp_path / "b0-context.json"
    context.write_text(json.dumps({
        "must_reuse_existing": True,
    }))
    gate_result = tmp_path / "gate-result.json"
    gate_result.write_text(json.dumps({
        "ok": False,
        "error": "listing_url_invalid",
    }))
    with pytest.raises(
        b0_result_gate.ContractError,
        match="b0_capacity_retry_not_applicable",
    ):
        b0_result_gate.prepare_capacity_retry(
            gate_result_path=gate_result,
            context_path=context,
            attempt=0,
        )


def test_published_result_is_written_once_to_canonical_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = tmp_path / "gig" / "shuppin.jsonl"
    ledger.parent.mkdir()
    monkeypatch.setattr(lane_productivity, "STATE", ledger.parent)
    context = make_context(tmp_path, ledger)
    summary, evidence = write_runner_result(
        tmp_path,
        context=context,
        action="published",
        service_id="4330907",
        url="https://coconala.com/services/4330907",
    )

    first = b0_result_gate.reconcile(
        context_path=context,
        summary_path=summary,
        evidence_dir=evidence,
        ledger_path=ledger,
        min_mtime=0,
        now=1_000,
    )
    second = b0_result_gate.reconcile(
        context_path=context,
        summary_path=summary,
        evidence_dir=evidence,
        ledger_path=ledger,
        min_mtime=0,
        now=1_001,
    )

    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert first == {"action": "published", "appended": 1, "duplicate": 0}
    assert second == {"action": "published", "appended": 0, "duplicate": 1}
    assert rows == [
        {
            "ts": 1000,
            "pass_id": "pass-1",
            "lane": "list",
            "action": "shuppin_published",
            "service_id": "4330907",
            "url": "https://coconala.com/services/4330907",
            "title": "Verified listing",
            "evidence": str(evidence / "listing.json"),
            "recorded_by": "b0_result_gate",
        }
    ]
    closure = lane_productivity.closure_snapshot(999)["listing"]
    assert closure["action_kind"] == "publish"
    assert closure["records"] == 1


def test_updated_result_closes_as_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "gig" / "shuppin.jsonl"
    ledger.parent.mkdir()
    monkeypatch.setattr(lane_productivity, "STATE", ledger.parent)
    context = make_context(tmp_path, ledger)
    summary, evidence = write_runner_result(
        tmp_path,
        context=context,
        action="updated",
        service_id="4330001",
        url="https://coconala.com/services/4330001",
    )

    b0_result_gate.reconcile(
        context_path=context,
        summary_path=summary,
        evidence_dir=evidence,
        ledger_path=ledger,
        min_mtime=0,
        now=1_000,
    )

    closure = lane_productivity.closure_snapshot(999)["listing"]
    assert closure["action_kind"] == "update"
    assert closure["records"] == 1


def test_noop_records_no_listing_effect(tmp_path: Path) -> None:
    ledger = tmp_path / "gig" / "shuppin.jsonl"
    ledger.parent.mkdir()
    context = make_context(tmp_path, ledger)
    summary, evidence = write_runner_result(
        tmp_path, context=context, action="verified_noop"
    )

    result = b0_result_gate.reconcile(
        context_path=context,
        summary_path=summary,
        evidence_dir=evidence,
        ledger_path=ledger,
        min_mtime=0,
        now=1_000,
    )

    assert result == {"action": "verified_noop", "appended": 0, "duplicate": 0}
    assert not ledger.exists()


def test_misrouted_row_is_recovered_only_with_fresh_public_evidence(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    url = "https://coconala.com/services/4330907"
    screenshot = evidence / "public.png"
    screenshot.write_bytes(b"public screenshot")
    live_dom = evidence / "public.json"
    live_dom.write_text(
        json.dumps(
            {
                "url": url,
                "not_found": False,
                "observed": True,
                "title": "Recovered listing",
            }
        )
    )
    misrouted = evidence / "misrouted-shuppin.jsonl"
    misrouted.write_text(
        json.dumps(
            {
                "action": "published",
                "service_id": "4330907",
                "url": url,
                "title": "Recovered listing",
            }
        )
        + "\n"
    )
    ledger = tmp_path / "gig" / "shuppin.jsonl"

    first = b0_result_gate.recover_misrouted(
        row_path=misrouted,
        pass_id="pass-recovery",
        evidence_dir=evidence,
        screenshot_path=screenshot,
        live_dom_path=live_dom,
        ledger_path=ledger,
        min_mtime=0,
        now=1_000,
    )
    second = b0_result_gate.recover_misrouted(
        row_path=misrouted,
        pass_id="pass-recovery",
        evidence_dir=evidence,
        screenshot_path=screenshot,
        live_dom_path=live_dom,
        ledger_path=ledger,
        min_mtime=0,
        now=1_001,
    )

    assert first["appended"] == 1
    assert second["duplicate"] == 1
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["recorded_by"] == "b0_result_gate_recovery"
    assert rows[0]["service_id"] == "4330907"


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("foreign_context", "context_path_mismatch"),
        ("foreign_url", "listing_url_invalid"),
        ("missing_evidence", "screenshot_missing"),
        ("dom_mismatch", "live_dom_url_mismatch"),
    ],
)
def test_action_fails_closed_on_unbound_or_unverified_evidence(
    tmp_path: Path, mutation: str, error: str
) -> None:
    ledger = tmp_path / "gig" / "shuppin.jsonl"
    ledger.parent.mkdir()
    context = make_context(tmp_path, ledger)
    summary, evidence = write_runner_result(
        tmp_path,
        context=context,
        action="published",
        service_id="4330907",
        url="https://coconala.com/services/4330907",
    )
    result_path = evidence / "attempt-01.result.json"
    result = json.loads(result_path.read_text())
    if mutation == "foreign_context":
        result["current_b0"]["context_path"] = str(tmp_path / "other.json")
    elif mutation == "foreign_url":
        result["current_b0"]["url"] = "https://example.com/services/4330907"
    elif mutation == "missing_evidence":
        Path(result["current_b0"]["screenshot_path"]).unlink()
    elif mutation == "dom_mismatch":
        Path(result["current_b0"]["live_dom_path"]).write_text(
            json.dumps(
                {
                    "url": "https://coconala.com/services/9999999",
                    "not_found": False,
                    "observed": True,
                }
            )
        )
    result_path.write_text(json.dumps(result) + "\n")

    with pytest.raises(b0_result_gate.ContractError, match=error):
        b0_result_gate.reconcile(
            context_path=context,
            summary_path=summary,
            evidence_dir=evidence,
            ledger_path=ledger,
            min_mtime=0,
            now=1_000,
        )
    assert not ledger.exists()


def test_b0_schema_is_strict_and_wiring_uses_code_owned_ledger() -> None:
    root = Path(__file__).parents[1]
    schema = json.loads((root / "schemas" / "gig_b0_result.schema.json").read_text())

    def assert_strict(node: object) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
                assert set(node.get("required", [])) == set(node.get("properties", {}))
            for value in node.values():
                assert_strict(value)
        elif isinstance(node, list):
            for value in node:
                assert_strict(value)

    assert_strict(schema)
    source = (root / "gig_pass.sh").read_text()
    assert 'B0_SCHEMA="$G/schemas/gig_b0_result.schema.json"' in source
    assert '[ "$label" = "B0" ] && step_schema="$B0_SCHEMA"' in source
    assert '"$G/scripts/b0_result_gate.py" reconcile' in source
    assert '--ledger "$HOME/gig/shuppin.jsonl"' in source
    assert "Do not write any ledger" in source
