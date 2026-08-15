from __future__ import annotations

import importlib.util
import json
from pathlib import Path


# P1a-6 (spec §0.1.6). The done condition was never "the code runs" but "the code catches the
# failure that already happened", so the replay tool has to be trustworthy about history.
#
# Two things it must not get wrong. Order: evidence directories are touched by later tooling,
# so sorting by mtime would silently reshuffle the past — the epoch in the directory name is
# the only honest clock. And counting: a pass whose snapshot is missing or unreadable is a
# pass we cannot judge, and quietly dropping it would flatter the result.

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "replay_paid_liability_history.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("replay_paid_liability_history", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WAITING = {
    "talkroom_id": "90000004",
    "title": "ウェブ画像の更新と軽微な調整",
    "price_jpy": 2500,
    "buyer_feedback_pending_artifact": True,
    "buyer_feedback_sha256": "9292841a",
    "buyer_visible_artifact_observed": False,
    "formal_delivery_observed": False,
}

DELIVERED = {
    "talkroom_id": "90000005",
    "title": "スクリーンショットのイタリア語化",
    "price_jpy": 4200,
    "buyer_feedback_pending_artifact": False,
    "buyer_visible_artifact_observed": True,
    "formal_delivery_observed": True,
}


def make_pass(root: Path, epoch: int, *orders, filename="marketplace-snapshot.json") -> Path:
    d = root / f"gig-pass-{epoch}-00000"
    d.mkdir(parents=True)
    if orders:
        (d / filename).write_text(
            json.dumps({"captured_at": "2026-08-05T00:00:00+00:00", "orders": list(orders)})
        )
    return d


def test_every_pass_with_an_unanswered_buyer_would_have_failed(tmp_path) -> None:
    m = load_module()
    root = tmp_path / "evidence"
    for epoch in (1785700000, 1785703600, 1785707200):
        make_pass(root, epoch, WAITING, DELIVERED)
    report = m.replay(root, tmp_path / "sl.jsonl")
    assert report["passes_with_snapshot"] == 3
    assert report["passes_gate_would_fail"] == 3
    assert report["owed_jpy"] == 2500


def test_a_history_with_nobody_waiting_does_not_light_up(tmp_path) -> None:
    m = load_module()
    root = tmp_path / "evidence"
    for epoch in (1785700000, 1785703600):
        make_pass(root, epoch, DELIVERED)
    report = m.replay(root, tmp_path / "sl.jsonl")
    assert report["passes_with_snapshot"] == 2
    assert report["passes_gate_would_fail"] == 0


def test_the_silence_ages_across_the_history_in_run_order(tmp_path) -> None:
    m = load_module()
    root = tmp_path / "evidence"
    for epoch in (1785707200, 1785700000, 1785703600):  # created out of order on purpose
        make_pass(root, epoch, WAITING)
    report = m.replay(root, tmp_path / "sl.jsonl")
    assert report["oldest_age_passes"] == 3
    assert report["first_failure"]["pass_id"] == "gig-pass-1785700000-00000"
    assert report["last_failure"]["pass_id"] == "gig-pass-1785707200-00000"


def test_a_pass_without_a_snapshot_is_not_counted_as_healthy(tmp_path) -> None:
    m = load_module()
    root = tmp_path / "evidence"
    make_pass(root, 1785700000, WAITING)
    make_pass(root, 1785703600)  # no snapshot at all
    report = m.replay(root, tmp_path / "sl.jsonl")
    assert report["passes_with_snapshot"] == 1


def test_the_after_reply_snapshot_is_used_when_it_is_the_only_one(tmp_path) -> None:
    m = load_module()
    root = tmp_path / "evidence"
    make_pass(root, 1785700000, WAITING, filename="marketplace-snapshot.after-reply.json")
    report = m.replay(root, tmp_path / "sl.jsonl")
    assert report["passes_with_snapshot"] == 1
    assert report["passes_gate_would_fail"] == 1


def test_the_cli_exits_non_zero_when_history_contains_an_unanswered_buyer(tmp_path, capsys) -> None:
    m = load_module()
    root = tmp_path / "evidence"
    make_pass(root, 1785700000, WAITING)
    rc = m.main(["--evidence-root", str(root), "--store", str(tmp_path / "sl.jsonl"), "--json"])
    assert rc != 0
    assert json.loads(capsys.readouterr().out)["passes_gate_would_fail"] == 1
