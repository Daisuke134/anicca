"""Contract tests for the two-lane read model (P1)."""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shared_commerce_snapshot as snapshot  # noqa: E402


SOURCE_NAMES = (
    "strategy.json", "playbook.json", "applied.jsonl", "applied-outcomes.jsonl",
    "earnings.jsonl", "shuppin.jsonl", "gig-funnel.jsonl", "identity_chain.jsonl",
    "pass-report.jsonl", "b2-shortfall.jsonl",
)
NOW = datetime(2026, 8, 10, 5, 0, tzinfo=timezone.utc)


def _state(tmp_path: Path) -> Path:
    gig = tmp_path / "gig"
    gig.mkdir()
    (gig / "strategy.json").write_text(
        json.dumps({"target_live_listings": 20, "priority_categories": ["ソフトウェア開発"]}),
        encoding="utf-8",
    )
    (gig / "playbook.json").write_text('{"general":[],"components":{}}\n', encoding="utf-8")
    for name in SOURCE_NAMES[2:]:
        (gig / name).write_text("", encoding="utf-8")
    (gig / "shuppin.jsonl").write_text(
        '{"service_id":"1","status":"published"}\n', encoding="utf-8"
    )
    (gig / "gig-funnel.jsonl").write_text('{"listings_live":1}\n', encoding="utf-8")
    return gig


def _fingerprints(gig: Path) -> dict[str, tuple[int, int, str]]:
    return {
        name: (p.stat().st_size, p.stat().st_mtime_ns,
               hashlib.sha256(p.read_bytes()).hexdigest())
        for name in SOURCE_NAMES
        for p in [gig / name]
    }


def test_snapshot_contains_bounded_lane_views_and_is_repeatable(tmp_path):
    gig = _state(tmp_path)
    before = _fingerprints(gig)
    first = snapshot.build_snapshot(gig_dir=gig, now=NOW)
    second = snapshot.build_snapshot(gig_dir=gig, now=NOW.replace(minute=17))
    assert first["ready"] is True
    assert first["lanes"]["storefront"]["action"] == "create_listing"
    assert first["lanes"]["apply"]["category_order"] == ["ソフトウェア開発"]
    assert first["lanes"]["apply"]["volume_controller"]["daily_target"] == 100
    assert first["snapshot_id"] == second["snapshot_id"]
    assert first["idempotency"]["task_template"] == "gig:coconala:{lane}:{slot}"
    assert "apply_effect_template" in first["idempotency"]
    assert "storefront_effect_template" in first["idempotency"]
    encoded = json.dumps(first, ensure_ascii=False)
    assert "/" + "Users/" not in encoded and "private_body" not in encoded
    assert _fingerprints(gig) == before
    (gig / "identity_chain.jsonl").write_text(
        '{"request_id":"1","talkroom_id":"2"}\n', encoding="utf-8"
    )
    changed = snapshot.build_snapshot(gig_dir=gig, now=NOW)
    assert changed["snapshot_id"] != first["snapshot_id"]
    (gig / "pass-report.jsonl").write_text('{"pass_id":"p1"}\n', encoding="utf-8")
    assert snapshot.build_snapshot(gig_dir=gig, now=NOW)["snapshot_id"] != changed["snapshot_id"]


def test_snapshot_always_exposes_reply_and_paid_lane_descriptors(tmp_path):
    gig = _state(tmp_path)
    result = snapshot.build_snapshot(gig_dir=gig, now=NOW)
    assert set(result["lanes"]) == {"apply", "storefront", "reply", "paid"}
    assert all(isinstance(result["lanes"][lane], dict) for lane in ("reply", "paid"))

    (gig / "playbook.json").unlink()
    fail_closed = snapshot.build_snapshot(gig_dir=gig, now=NOW)
    assert set(fail_closed["lanes"]) == {"apply", "storefront", "reply", "paid"}
    assert all(isinstance(fail_closed["lanes"][lane], dict) for lane in ("reply", "paid"))


def test_missing_required_source_is_fail_closed_and_atomic(tmp_path):
    gig = _state(tmp_path)
    (gig / "playbook.json").unlink()
    output = tmp_path / "snapshot.json"
    result = snapshot.write_snapshot(gig_dir=gig, output_path=output, now=NOW)
    assert result["ready"] is False
    assert "playbook.json" in result["missing_sources"]
    assert json.loads(output.read_text(encoding="utf-8"))["snapshot_id"] == result["snapshot_id"]
    assert not list(tmp_path.glob(".snapshot.json.*"))
