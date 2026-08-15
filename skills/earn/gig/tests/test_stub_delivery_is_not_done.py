#!/usr/bin/env python3
"""A delivery the builder said it could not build does not close an order.

2026-08-06T19:04:49Z order 91000002 was formally delivered: a 1879-byte document listing
the things we still needed to confirm, sent as 正式な納品. The order then vanished from the
delivery queue, because "we delivered and the buyer has not replied" reads as finished --
while the builder's own BLOCKED record for the same feedback was still on disk and the
buyer's approval clock was running on an empty deliverable.

The fixtures below are copied from the real files (evidence digest
57b8719d5bd8ff77a7f68614fd9e9e6a4dbc35411094f43fd82891a103bdcfda). Nothing here reads
~/gig at test time.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ask_buyer  # noqa: E402
import ask_buyer_pass  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "delivery_cadence_stub_test", SCRIPTS / "delivery_cadence.py"
)
cadence = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cadence)

# Verbatim from ~/gig/projects/91000002/evidence/acceptance-blocked.json.
FEEDBACK_SHA256 = "57b8719d5bd8ff77a7f68614fd9e9e6a4dbc35411094f43fd82891a103bdcfda"
BLOCKED_RECORD = {
    "version": 1,
    "status": "BLOCKED",
    "feedback_sha256": FEEDBACK_SHA256,
    "checks": [
        {
            "command": "python3 validation/validate_delivery_generic.py artifacts/delivery-v2.md",
            "result": "FAIL。検証対象の実成果物が存在しないため artifact_missing です。",
        },
    ],
    "blocker": (
        "買い手の実質的な制作指示、納品物の種類、仕様、素材、既存ソース、ビルド手順がないため、"
        "内容を推測した成果物を作成できません。"
    ),
}
BUYER_TEXT = "よろしくお願いいたします。"


def _project(tmp_path, *, blocked: bool, requirements: bool = True) -> Path:
    """A project root shaped like the real one: requirements file + BLOCKED record."""
    root = tmp_path / "91000002"
    (root / "evidence").mkdir(parents=True)
    (root / "requirements").mkdir(parents=True)
    requirements_path = root / "requirements" / "live-buyer-reply.json"
    if requirements:
        requirements_path.write_text(json.dumps({
            "feedback_sha256": FEEDBACK_SHA256,
            "feedback_text": BUYER_TEXT,
            "observed_at": "2026-08-06T18:00:00+00:00",
        }, ensure_ascii=False), encoding="utf-8")
    if blocked:
        record = dict(BLOCKED_RECORD, requirements_path=str(requirements_path))
        (root / "evidence" / "acceptance-blocked.json").write_text(
            json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return root


def _delivered_item(root: Path) -> dict:
    """The shape 91000002 had in the queue: formally delivered, buyer silent."""
    return {
        "request_id": "91000002",
        "talkroom_id": "90000002",
        "project_root": str(root),
        "formal_delivery_observed": True,
        "talkroom_state": "納品確認待ち",
    }


def _passing_gates(root: Path, item: dict) -> dict:
    """Add the artifact/acceptance/hash facts the stub delivery actually had.

    The meta-document passed every one of them -- it is a real file with a real version
    token, a real acceptance record and a matching digest. That is what makes the "just
    fall through to the gates below" version of this fix dangerous: the gates say formal.
    """
    artifact = root / "artifacts" / "delivery-v2.md"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"# these are the things we still need to confirm\n")
    acceptance = root / "acceptance" / "acceptance-v2.json"
    acceptance.parent.mkdir(parents=True, exist_ok=True)
    acceptance.write_text('{"status":"PASS"}\n', encoding="utf-8")
    return dict(
        item,
        artifact_path=str(artifact),
        artifact_version="v2",
        acceptance_status="PASS",
        acceptance_evidence_path=str(acceptance),
        package_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
    )


# ---------------------------------------------------------------- spec §5 items 1-4


def test_fresh_block_keeps_a_formally_delivered_order_open(tmp_path):
    """§5.1 -- the builder still says it cannot build, so this is not finished."""
    root = _project(tmp_path, blocked=True)
    assert cadence._blocked_verdict(_delivered_item(root)) == "fresh"
    assert cadence.delivery_decision(_delivered_item(root))["mode"] != "none"


def test_undeterminable_block_is_not_tipped_into_finished(tmp_path):
    """§5.2 -- "I could not tell" must never be recorded as "delivered and done".

    The requirements file the record names is gone, so freshness cannot be measured.
    """
    root = _project(tmp_path, blocked=True, requirements=False)
    assert cadence._blocked_verdict(_delivered_item(root)) == "undeterminable"
    assert cadence.delivery_decision(_delivered_item(root))["mode"] != "none"


def test_a_missing_project_root_is_undeterminable_not_absent(tmp_path):
    """An item that cannot name its project has not been checked, only unchecked."""
    item = _delivered_item(tmp_path / "91000002")
    item.pop("project_root")
    assert cadence._blocked_verdict(item) == "undeterminable"
    assert cadence.delivery_decision(item)["mode"] != "none"


def test_a_genuinely_completed_delivery_is_still_left_alone(tmp_path):
    """§5.3 -- ★the proof that this change does not drag healthy deliveries back★."""
    root = _project(tmp_path, blocked=False)
    assert cadence._blocked_verdict(_delivered_item(root)) == "absent"
    decision = cadence.delivery_decision(_delivered_item(root))
    assert decision["mode"] == "none"
    assert decision["blockers"] == []


def test_a_block_the_buyer_has_already_answered_does_not_reopen(tmp_path):
    """A spent block is not a live one: the buyer answered, so the digest moved on."""
    root = _project(tmp_path, blocked=True)
    requirements = root / "requirements" / "live-buyer-reply.json"
    requirements.write_text(json.dumps({
        "feedback_sha256": "a" * 64,
        "feedback_text": "素材を送ります。ロゴはこちらです。",
    }, ensure_ascii=False), encoding="utf-8")
    assert cadence._blocked_verdict(_delivered_item(root)) == "stale"
    assert cadence.delivery_decision(_delivered_item(root))["mode"] == "none"


def test_a_returned_blocked_order_is_never_re_delivered(tmp_path):
    """§5.4 -- there is nothing deliverable while the diagnosis stands."""
    root = _project(tmp_path, blocked=True)
    item = _passing_gates(root, _delivered_item(root))
    # Sanity: with the block removed these exact facts DO produce a formal delivery,
    # which is what makes the assertion below meaningful rather than vacuous.
    unblocked = dict(item)
    (root / "evidence" / "acceptance-blocked.json").rename(root / "evidence" / "spent.json")
    assert cadence.delivery_decision(dict(unblocked, formal_delivery_observed=False))["mode"] == "formal"
    (root / "evidence" / "spent.json").rename(root / "evidence" / "acceptance-blocked.json")

    decision = cadence.delivery_decision(item)
    assert decision["mode"] != "formal"
    assert decision["mode"] == "work_required"
    assert decision["formal_delivery_checkbox"] is False
    assert decision["buyer_visible"] is False


# ---------------------------------------------------------------- spec §5 item 5


def test_the_question_opens_from_the_file_we_already_sent():
    """§5.5 -- apologise, name what that file really was, and do not ask for approval."""
    prompt = ask_buyer.question_prompt(state=BLOCKED_RECORD, formal_delivery_observed=True)
    assert "完成した制作物ではなく" in prompt
    assert "確認が必要な事項をまとめた資料" in prompt
    assert "最初に謝る" in prompt
    assert "承認を求めるのではなく" in prompt
    assert "言い訳をしない" in prompt
    # Derived from the buyer's own request, not a generic requirements checklist.
    assert "お客様が実際に書かれたご依頼内容から導く" in prompt
    assert "納期に触れ" in prompt
    # Still the same voice and still a real question.
    assert prompt.startswith(ask_buyer.PERSONA)
    assert "既にお支払い済み" in prompt


def test_an_ordinary_blocked_question_does_not_apologise_for_a_delivery():
    """The branch is conditional: an order we never delivered has nothing to retract."""
    prompt = ask_buyer.question_prompt(state=BLOCKED_RECORD)
    assert "完成した制作物ではなく" not in prompt
    assert "既にお支払い済み" in prompt


def test_a_formal_delivery_is_read_from_the_project_ledger(tmp_path):
    root = tmp_path / "91000002"
    root.mkdir(parents=True)
    assert ask_buyer.formal_delivery_recorded(root) is False
    ledger = root / "events.jsonl"
    ledger.write_text("\n".join((
        json.dumps({"event": "queue_selected", "project_id": "91000002"}),
        "not json",
        json.dumps({"event": "FORMAL_DELIVERY_CONFIRMED", "project_id": "91000002"}),
    )) + "\n", encoding="utf-8")
    assert ask_buyer.formal_delivery_recorded(root) is True
    assert ask_buyer.formal_delivery_recorded(None) is False


# ---------------------------------------------------------------- spec §3.4 (dedupe)


def _build(root: Path, tmp_path: Path, ledger: Path) -> dict:
    output = tmp_path / "ask-buyer-queue.json"
    args = ask_buyer_pass.argparse.Namespace(
        project_root=str(root), talkroom_id="90000002",
        ledger=str(ledger), output=str(output),
    )
    assert ask_buyer_pass.build(args) == 0
    return json.loads(output.read_text(encoding="utf-8"))


def test_the_question_queue_carries_the_delivered_fact(tmp_path):
    root = _project(tmp_path, blocked=True)
    (root / "events.jsonl").write_text(
        json.dumps({"event": "FORMAL_DELIVERY_CONFIRMED"}) + "\n", encoding="utf-8")
    queue = _build(root, tmp_path, tmp_path / "ask-buyer.jsonl")
    assert queue["status"] == "ready"
    assert queue["items"][0]["formal_delivery_observed"] is True
    assert queue["items"][0]["blocker_key"] == FEEDBACK_SHA256


def test_one_question_per_blocked_state_still_holds(tmp_path):
    """§3.4 -- an already-asked blocker earns silence, a new one earns a question."""
    root = _project(tmp_path, blocked=True)
    ledger = tmp_path / "ask-buyer.jsonl"
    ledger.write_text(json.dumps({
        "talkroom_id": "90000002", "blocker_key": FEEDBACK_SHA256,
    }) + "\n", encoding="utf-8")
    queue = _build(root, tmp_path, ledger)
    assert queue["status"] == "queue_empty"
    assert queue["already_asked"] == FEEDBACK_SHA256

    # A different order's row in the same ledger does not silence this one: 90000004 was
    # asked at 12:05 today and must not be asked twice, while 91000002 has no row yet and
    # must still get its first question.
    ledger.write_text(json.dumps({
        "talkroom_id": "90000004", "blocker_key": "b" * 64,
    }) + "\n", encoding="utf-8")
    assert _build(root, tmp_path, ledger)["status"] == "ready"
