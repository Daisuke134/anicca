from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


# P1a-4 (spec §0.1.6). A paying buyer who is waiting becomes a row that ages, and the row can
# only be closed by an action whose readback shows we actually spoke after they did.
#
# The failure being converted from an absence into a presence: 24 consecutive passes wrote
# `queue_selected` and nothing else while 買い手C waited. Nothing was wrong in any log, because
# "did nothing" produced no row. Here it produces a row that gets older every pass.
#
# Closing conditions are deliberately narrow. `observed`, `no work required` and `not my lane`
# were all true statements the loop made while the customer waited, and all three are refused
# as close conditions. If the lane cannot act it must say why, from a closed enum, with the
# concrete blocker — an untyped silent skip is the bug itself.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "silence_liability.py"


def load_module():
    spec = importlib.util.spec_from_file_location("silence_liability", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


KITTY_ROOM = {
    "talkroom_id": "90000004",
    "order_value_jpy": 2500,
    "liability_open": True,
    "liability_key": "90000004:9292841a",
    "title": "ウェブ画像の更新と軽微な調整",
}


def store(tmp_path) -> Path:
    return tmp_path / "silence-liability.jsonl"


# --- a waiting buyer becomes a row that ages ---------------------------------------------


def test_an_open_room_opens_a_liability(tmp_path) -> None:
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    rows = m.open_liabilities(path)
    assert [r["liability_key"] for r in rows] == ["90000004:9292841a"]
    assert rows[0]["order_value_jpy"] == 2500


def test_the_same_silence_ages_instead_of_duplicating(tmp_path) -> None:
    m = load_module()
    path = store(tmp_path)
    for i in range(1, 25):  # the 24 dead passes, plus the one that noticed
        m.observe(path, [KITTY_ROOM], pass_id=f"pass-{i}")
    rows = m.open_liabilities(path)
    assert len(rows) == 1
    assert rows[0]["age_passes"] == 24


def test_a_new_buyer_message_opens_its_own_liability(tmp_path) -> None:
    # Keyed on the buyer message, so a fresh question is not absorbed by a closed one.
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    later = {**KITTY_ROOM, "liability_key": "90000004:bbbbbbbb"}
    m.observe(path, [later], pass_id="pass-2")
    assert len(m.open_liabilities(path)) == 2


def test_a_room_that_stops_being_open_is_not_reopened(tmp_path) -> None:
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    m.observe(path, [{**KITTY_ROOM, "liability_open": False}], pass_id="pass-2")
    assert m.open_liabilities(path)[0]["age_passes"] == 1


# --- closing requires evidence that we spoke, not that we looked --------------------------


def test_an_action_with_readback_closes_it(tmp_path) -> None:
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    m.close(
        path,
        "90000004:9292841a",
        action="ask_buyer",
        outbound_readback={"posted_at": "2026-08-05T02:00:00+00:00", "message_id": "m-1"},
        pass_id="pass-1",
    )
    assert m.open_liabilities(path) == []


def test_observing_the_room_does_not_close_it(tmp_path) -> None:
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    with pytest.raises(m.NotACloseCondition):
        m.close(path, "90000004:9292841a", action="observed", outbound_readback=None, pass_id="pass-1")
    assert len(m.open_liabilities(path)) == 1


def test_an_action_without_a_readback_does_not_close_it(tmp_path) -> None:
    # The send may have failed. Only the readback proves the buyer can see it.
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    with pytest.raises(m.NotACloseCondition):
        m.close(path, "90000004:9292841a", action="ask_buyer", outbound_readback=None, pass_id="pass-1")
    assert len(m.open_liabilities(path)) == 1


def test_no_work_required_is_not_a_close_condition(tmp_path) -> None:
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    for excuse in ("no_work_required", "not_my_lane", "observed_no_action"):
        with pytest.raises(m.NotACloseCondition):
            m.close(path, "90000004:9292841a", action=excuse, outbound_readback={"posted_at": "x"}, pass_id="pass-1")


# --- if it cannot act it must say why, in a way a machine can read ------------------------


def test_a_refusal_must_come_from_the_closed_enum(tmp_path) -> None:
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    with pytest.raises(m.UntypedRefusal):
        m.refuse(path, "90000004:9292841a", code="busy", blocker_id="x", pass_id="pass-1")


def test_a_refusal_must_name_a_concrete_blocker(tmp_path) -> None:
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    with pytest.raises(m.UntypedRefusal):
        m.refuse(path, "90000004:9292841a", code="no_artifact_yet", blocker_id="", pass_id="pass-1")


def test_a_typed_refusal_is_recorded_and_the_liability_stays_open(tmp_path) -> None:
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    m.refuse(path, "90000004:9292841a", code="no_artifact_yet", blocker_id="requirements/90000004", pass_id="pass-1")
    rows = m.open_liabilities(path)
    assert len(rows) == 1
    assert rows[0]["last_refusal"]["code"] == "no_artifact_yet"


def test_a_pass_that_left_a_liability_untouched_is_reported(tmp_path) -> None:
    # This is what step 5 turns into a non-zero exit. Here it only has to be answerable.
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    assert m.undisposed(path, pass_id="pass-1") == ["90000004:9292841a"]
    m.refuse(path, "90000004:9292841a", code="quota_exhausted", blocker_id="codex:pro", pass_id="pass-1")
    assert m.undisposed(path, pass_id="pass-1") == []


# --- the four proactive actions are not the only ways to answer someone --------------------


def test_answering_the_buyer_closes_the_liability(tmp_path) -> None:
    # The four actions came from ideation about moves the lane initiates. The two most common
    # ways a silence actually ends are absent from that list: we answered their question, or
    # we delivered the work. Refusing to close on those would leave a genuinely answered
    # customer marked as waiting forever.
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    m.close(path, "90000004:9292841a", action="answer",
            outbound_readback={"posted_at": "x"}, pass_id="pass-1")
    assert m.open_liabilities(path) == []


def test_formal_delivery_closes_the_liability(tmp_path) -> None:
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    m.close(path, "90000004:9292841a", action="formal_delivery",
            outbound_readback={"posted_at": "x"}, pass_id="pass-1")
    assert m.open_liabilities(path) == []


def test_the_excuses_are_still_not_actions(tmp_path) -> None:
    # Widening the set must not quietly readmit the statements that were true while the
    # customer waited.
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    for excuse in ("observed", "no_work_required", "not_my_lane", "observed_no_action"):
        with pytest.raises(m.NotACloseCondition):
            m.close(path, "90000004:9292841a", action=excuse,
                    outbound_readback={"posted_at": "x"}, pass_id="pass-1")


def test_composing_a_message_still_only_knows_the_four(tmp_path) -> None:
    # answer and formal_delivery close a liability but have no artifact class: their text is
    # produced by the delivery path, not by compose_reply.
    artifact = load_artifact_module()
    assert set(artifact.ARTIFACT_CLASS_FOR_ACTION) == {
        "ask_buyer", "request_extension", "cancel_request", "end_subscription"
    }


def load_artifact_module():
    import importlib.util
    from pathlib import Path as _P
    p = _P(__file__).resolve().parents[1] / "scripts" / "paid_conversation_artifact.py"
    spec = importlib.util.spec_from_file_location("paid_conversation_artifact", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_nothing_new_to_build_is_a_typed_refusal_not_a_silent_skip(tmp_path) -> None:
    # Measured 2026-08-05: paid_work_validation_failed 44 times, and running the validator on
    # the real ledger gives one reason — artifact_version_not_newer_than_project_state. The
    # project holds exactly one artifact, catalog-page-10756-v12.html, and the manifest
    # re-declares v12. The work was delivered by hand the day before; there is nothing new to
    # build, yet the pass architecture insists PAID_WORK produce a newer version and dies
    # when it cannot.
    #
    # The validator is right — weakening it would let the same artifact be re-delivered as
    # new. The lane needs a way to say "there is nothing to build here", and it must not
    # become a way to say nothing: the liability stays open, so the conversation still owes
    # the buyer an answer.
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    m.refuse(path, "90000004:9292841a", code="no_new_work_required",
             blocker_id="artifact_version_not_newer_than_project_state:v12", pass_id="pass-1")
    rows = m.open_liabilities(path)
    assert len(rows) == 1, "a finished build must not close the buyer's question"
    assert rows[0]["last_refusal"]["code"] == "no_new_work_required"


def test_it_cannot_close_a_liability_by_itself(tmp_path) -> None:
    # If this ever becomes a close condition it turns into the excuse the four rejected ones
    # were: a true statement about our side, made while the customer waits.
    m = load_module()
    path = store(tmp_path)
    m.observe(path, [KITTY_ROOM], pass_id="pass-1")
    with pytest.raises(m.NotACloseCondition):
        m.close(path, "90000004:9292841a", action="no_new_work_required",
                outbound_readback={"posted_at": "x"}, pass_id="pass-1")
