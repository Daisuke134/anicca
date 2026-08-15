from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


# P1a-2 (spec §0.1.6). `compose_reply` is the only way text reaches a paid buyer. It takes an
# artifact and interpolates the sentence from that artifact's fields — it cannot be handed a
# string to send.
#
# The concrete failure this closes: 「本日中に完了予定をご連絡します」 was sent four times
# across 2026-08-03/04 with no schedule behind it, the fourth after three misses. Under this
# module that sentence is unconstructible unless a revised_schedule artifact carries the date
# being promised, because the date is read out of the artifact rather than written by a model.
#
# A trap named during adversarial ideation and deliberately not taken: filter outbound text
# for commitment grammar with a regex. It is adversarial to itself — false positives block
# legitimate replies and push the lane back into silence. Rendering from fields sidesteps the
# question entirely: there is no free text to filter.

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "paid_conversation_compose.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "paid_conversation_compose", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCHEDULE = {
    "artifact_class": "revised_schedule",
    "talkroom_id": "90000004",
    "title": "カタログ修正の納品スケジュール",
    "delta": [{"field": "date", "from": "8/4", "to": "8/6"}],
    "due_date": "2026-08-06",
}

WORKSHEET = {
    "artifact_class": "question_worksheet",
    "talkroom_id": "90000004",
    "title": "カタログ修正に必要な確認事項",
    "delta": [{"field": "scope", "from": "未確定", "to": "2点の確認待ち"}],
    "questions": [
        "緑バーの飛び先は73ページで合っていますか",
        "差し替える画像は最新版でよろしいですか",
    ],
}


# --- the promise is read out of the artifact, never written by the caller ---------------


def test_the_promised_date_is_the_artifacts_date() -> None:
    m = load_module()
    text = m.compose_reply(SCHEDULE)
    assert "8月6日" in text


def test_a_schedule_without_its_date_cannot_be_composed_at_all() -> None:
    m = load_module()
    broken = {k: v for k, v in SCHEDULE.items() if k != "due_date"}
    with pytest.raises(m.PromiseWithoutArtifact):
        m.compose_reply(broken)


def test_the_caller_cannot_supply_the_sentence() -> None:
    # There is no parameter through which arbitrary text reaches the buyer. If one is ever
    # added, this test is the thing that notices.
    m = load_module()
    import inspect

    params = set(inspect.signature(m.compose_reply).parameters)
    assert params <= {"artifact"}, f"compose_reply grew a text channel: {params}"


# --- an artifact that would not validate never becomes a message ------------------------


def test_an_invalid_artifact_is_refused_before_any_text_exists() -> None:
    m = load_module()
    with pytest.raises(m.PromiseWithoutArtifact):
        m.compose_reply({**SCHEDULE, "delta": []})


def test_an_unknown_class_has_no_template_and_is_refused() -> None:
    m = load_module()
    with pytest.raises(m.PromiseWithoutArtifact):
        m.compose_reply({**SCHEDULE, "artifact_class": "status_snapshot"})


# --- what the buyer sees is buyer-facing Japanese, not our internals --------------------


def test_internal_identifiers_never_reach_the_buyer() -> None:
    m = load_module()
    for artifact in (SCHEDULE, WORKSHEET):
        text = m.compose_reply(artifact)
        assert artifact["talkroom_id"] not in text
        assert "artifact_class" not in text
        assert "/" not in text.replace("\n", "")  # no paths, no ISO dates leaking through


def test_the_questions_the_buyer_must_answer_are_all_present() -> None:
    m = load_module()
    text = m.compose_reply(WORKSHEET)
    for q in WORKSHEET["questions"]:
        assert q in text


def test_a_worksheet_promises_nothing_because_it_has_no_date() -> None:
    # The bug was promising a completion time while asking what to do. A worksheet carries no
    # due_date, so no delivery date can appear in its text.
    m = load_module()
    text = m.compose_reply(WORKSHEET)
    assert "納品" not in text
    assert "日まで" not in text
