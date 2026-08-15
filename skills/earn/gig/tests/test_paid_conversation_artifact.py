from __future__ import annotations

import importlib.util
from pathlib import Path


# P1a-1 (spec §0.1.6). The paid-buyer lane never composes a message as its first act — it
# materializes an artifact, and the message is rendered from that artifact's fields. These
# tests fix the shape of that artifact so the invariant is enforced by the schema rather than
# by asking the model nicely.
#
# The failure being designed out: on 2026-08-04 the loop sent "確認いたします" and "本日中に
# 完了予定をご連絡します" through 24 consecutive passes with no artifact behind either
# sentence. A promise must be a projection of an artifact, not a claim about one.
#
# The trap being designed out (adversarial ideation, §0.1.6): "let a three-line status
# snapshot count as the artifact" unlocks the lane and legalizes content-free deliverables —
# the artifact check passes while the buyer still gets nothing. Hence the substance
# predicate: an artifact must name which buyer-visible fact it changes.

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "paid_conversation_artifact.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "paid_conversation_artifact", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _worksheet(**overrides):
    base = {
        "artifact_class": "question_worksheet",
        "talkroom_id": "90000004",
        "title": "カタログ修正に必要な確認事項",
        "delta": [{"field": "scope", "from": "未確定", "to": "3点の確認待ち"}],
        "questions": ["緑バーの飛び先は73ページで合っていますか"],
    }
    base.update(overrides)
    return base


# --- the four classes exist and are bound one-to-one to the four actions ----------------


def test_each_action_has_exactly_one_artifact_class() -> None:
    m = load_module()
    assert m.ARTIFACT_CLASS_FOR_ACTION == {
        "ask_buyer": "question_worksheet",
        "request_extension": "revised_schedule",
        "cancel_request": "cancellation_rationale",
        "end_subscription": "final_accounting",
    }


def test_an_action_cannot_be_taken_with_another_actions_artifact() -> None:
    m = load_module()
    ok, errors = m.validate_for_action("request_extension", _worksheet())
    assert ok is False
    assert any("artifact_class" in e for e in errors)


# --- the substance predicate: an artifact must change something the buyer can see -------


def test_an_artifact_that_changes_nothing_is_rejected() -> None:
    m = load_module()
    ok, errors = m.validate(_worksheet(delta=[]))
    assert ok is False
    assert any("delta" in e for e in errors)


def test_a_delta_naming_a_field_the_buyer_cannot_see_is_rejected() -> None:
    m = load_module()
    ok, errors = m.validate(
        _worksheet(delta=[{"field": "internal_retry_count", "from": "0", "to": "1"}])
    )
    assert ok is False
    assert any("field" in e for e in errors)


# --- required fields are required, per class -------------------------------------------


def test_a_worksheet_with_no_questions_is_not_a_worksheet() -> None:
    m = load_module()
    ok, errors = m.validate(_worksheet(questions=[]))
    assert ok is False
    assert any("questions" in e for e in errors)


def test_an_extension_without_a_new_date_cannot_render_a_promise() -> None:
    m = load_module()
    ok, errors = m.validate(
        {
            "artifact_class": "revised_schedule",
            "talkroom_id": "90000004",
            "title": "納品スケジュールの更新",
            "delta": [{"field": "date", "from": "8/4", "to": "8/6"}],
        }
    )
    assert ok is False
    assert any("due_date" in e for e in errors)


def test_a_cancellation_must_state_a_reason_and_a_refund() -> None:
    m = load_module()
    ok, errors = m.validate(
        {
            "artifact_class": "cancellation_rationale",
            "talkroom_id": "90000004",
            "title": "中止のご連絡",
            "delta": [{"field": "deliverable_state", "from": "作業中", "to": "中止"}],
        }
    )
    assert ok is False
    assert any("reason" in e for e in errors)
    assert any("refund_jpy" in e for e in errors)


def test_an_unknown_class_is_rejected_rather_than_ignored() -> None:
    m = load_module()
    ok, errors = m.validate(_worksheet(artifact_class="status_snapshot"))
    assert ok is False
    assert any("artifact_class" in e for e in errors)


# --- the happy path still passes, or the gate is just a wall ----------------------------


def test_a_complete_worksheet_is_accepted() -> None:
    m = load_module()
    ok, errors = m.validate(_worksheet())
    assert ok is True, errors


def test_a_complete_extension_renders_its_promise_from_the_artifact() -> None:
    m = load_module()
    artifact = {
        "artifact_class": "revised_schedule",
        "talkroom_id": "90000004",
        "title": "カタログ修正の納品スケジュール",
        "delta": [{"field": "date", "from": "8/4", "to": "8/6"}],
        "due_date": "2026-08-06",
    }
    ok, errors = m.validate(artifact)
    assert ok is True, errors
    ok, errors = m.validate_for_action("request_extension", artifact)
    assert ok is True, errors
