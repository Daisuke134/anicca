from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "application_ledger_heal.py"
)


def load():
    spec = importlib.util.spec_from_file_location(
        "application_ledger_heal_under_test",
        SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evidence_tree(tmp_path: Path) -> tuple[Path, Path]:
    evidence = tmp_path / "gig-pass-pass-2"
    agent = evidence / "agent-B2"
    agent.mkdir(parents=True)
    (agent / "gig-B2-5183000-submitted.intent.json").write_text(
        json.dumps({"request_id": "5183000"})
    )
    live_dom = agent / "request-5183000.json"
    live_dom.write_text(json.dumps({
        "url": "https://coconala.com/requests/5183000",
        "not_found": False,
        "observed": True,
        "title": "Presentation design | ココナラ",
    }))
    return evidence, live_dom


def test_discovery_requires_pass_bound_intent_and_archived_live_dom(tmp_path):
    module = load()
    evidence, live_dom = evidence_tree(tmp_path)
    candidates = module.discover_candidates(evidence, "pass-2")
    assert candidates == [{
        "request_id": "5183000",
        "bucket": "single",
        "title": "Presentation design",
        "url": "https://coconala.com/requests/5183000",
        "pass_id": "pass-2",
        "source_evidence": str(live_dom.resolve()),
    }]


def test_fresh_canonical_readback_recovers_ledger_idempotently(tmp_path):
    module = load()
    evidence, _ = evidence_tree(tmp_path)
    ledger = tmp_path / "applied.jsonl"
    output = tmp_path / "recovery.json"
    captured = {
        "source": "code_owned_cdp_readback",
        "request_ids": ["5183000"],
        "offers": [{
            "request_id": "5183000",
            "offer_url": "https://coconala.com/mypage/offers/6277000",
            "title": "Presentation design",
        }],
    }

    first = module.reconcile_with_capture(
        evidence_dir=evidence,
        pass_id="pass-2",
        ledger_path=ledger,
        output_path=output,
        captured=captured,
        observed_at=2_000_000,
    )
    second = module.reconcile_with_capture(
        evidence_dir=evidence,
        pass_id="pass-2",
        ledger_path=ledger,
        output_path=output,
        captured=captured,
        observed_at=2_000_001,
    )

    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert first["recovered"] == 1
    assert second["recovered"] == 0
    assert len(rows) == 1
    assert rows[0]["recorded_by"] == "canonical_orphan_reconciliation"
    assert rows[0]["applied_page_verified"] is True


def test_missing_canonical_readback_never_writes_ledger(tmp_path):
    module = load()
    evidence, _ = evidence_tree(tmp_path)
    ledger = tmp_path / "applied.jsonl"
    try:
        module.reconcile_with_capture(
            evidence_dir=evidence,
            pass_id="pass-2",
            ledger_path=ledger,
            output_path=tmp_path / "recovery.json",
            captured={"request_ids": [], "offers": []},
            observed_at=2_000_000,
        )
    except ValueError as error:
        assert str(error) == "canonical_application_missing:5183000"
    else:
        raise AssertionError("missing canonical identity was accepted")
    assert not ledger.exists()
