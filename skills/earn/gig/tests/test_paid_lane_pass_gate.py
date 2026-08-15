from __future__ import annotations

import importlib.util
import json
from pathlib import Path


# P1a-5 (spec §0.1.6). The pass may not end while a paying customer is both unanswered and
# unexplained.
#
# This is the piece that makes the previous four load-bearing. A liability that ages in a
# file nobody reads is the same as no liability, and the loop has already proved it will
# keep exiting zero forever: 24 clean passes, ¥0, one customer waiting the whole time.
#
# The gate is deliberately not "did you reply". Replying is often impossible in a given
# pass. It is "did you either reply with proof, or say why you could not, in a form that can
# be counted later". Silence is the only outcome it refuses.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "paid_lane_pass_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("paid_lane_pass_gate", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def liability_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "silence_liability.py"
    spec = importlib.util.spec_from_file_location("silence_liability", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOM = {
    "talkroom_id": "90000004",
    "order_value_jpy": 2500,
    "liability_open": True,
    "liability_key": "90000004:9292841a",
    "title": "ウェブ画像の更新と軽微な調整",
}


def test_a_pass_with_nothing_open_passes(tmp_path) -> None:
    m = load_module()
    verdict = m.check(tmp_path / "sl.jsonl", pass_id="pass-1")
    assert verdict["ok"] is True
    assert verdict["undisposed"] == []


def test_a_pass_that_left_a_paying_customer_unanswered_fails(tmp_path) -> None:
    m = load_module()
    sl = liability_module()
    store = tmp_path / "sl.jsonl"
    sl.observe(store, [ROOM], pass_id="pass-1")
    verdict = m.check(store, pass_id="pass-1")
    assert verdict["ok"] is False
    assert verdict["undisposed"] == ["90000004:9292841a"]


def test_a_typed_refusal_is_enough_to_end_the_pass(tmp_path) -> None:
    # The gate does not demand a reply. It demands an answer to "why not", which is the
    # thing that was missing for 24 passes.
    m = load_module()
    sl = liability_module()
    store = tmp_path / "sl.jsonl"
    sl.observe(store, [ROOM], pass_id="pass-1")
    sl.refuse(store, "90000004:9292841a", code="no_artifact_yet", blocker_id="requirements/90000004", pass_id="pass-1")
    assert m.check(store, pass_id="pass-1")["ok"] is True


def test_disposing_it_in_an_earlier_pass_does_not_excuse_this_one(tmp_path) -> None:
    # Otherwise one refusal on Monday buys silence for the rest of the week.
    m = load_module()
    sl = liability_module()
    store = tmp_path / "sl.jsonl"
    sl.observe(store, [ROOM], pass_id="pass-1")
    sl.refuse(store, "90000004:9292841a", code="no_artifact_yet", blocker_id="requirements/90000004", pass_id="pass-1")
    sl.observe(store, [ROOM], pass_id="pass-2")
    assert m.check(store, pass_id="pass-2")["ok"] is False


def test_the_verdict_names_the_customer_and_the_money(tmp_path) -> None:
    # A gate that fails with a hash helps nobody at 3am.
    m = load_module()
    sl = liability_module()
    store = tmp_path / "sl.jsonl"
    sl.observe(store, [ROOM], pass_id="pass-1")
    verdict = m.check(store, pass_id="pass-1")
    assert verdict["detail"][0]["talkroom_id"] == "90000004"
    assert verdict["detail"][0]["order_value_jpy"] == 2500
    assert verdict["detail"][0]["age_passes"] == 1


def test_the_cli_exits_non_zero_so_the_pass_cannot_report_success(tmp_path, capsys) -> None:
    m = load_module()
    sl = liability_module()
    store = tmp_path / "sl.jsonl"
    sl.observe(store, [ROOM], pass_id="pass-1")
    rc = m.main(["--store", str(store), "--pass-id", "pass-1"])
    assert rc != 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False


def test_the_cli_exits_zero_when_everything_was_disposed(tmp_path, capsys) -> None:
    m = load_module()
    sl = liability_module()
    store = tmp_path / "sl.jsonl"
    sl.observe(store, [ROOM], pass_id="pass-1")
    sl.close(
        store,
        "90000004:9292841a",
        action="ask_buyer",
        outbound_readback={"posted_at": "2026-08-05T02:00:00+00:00"},
        pass_id="pass-1",
    )
    rc = m.main(["--store", str(store), "--pass-id", "pass-1"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_a_missing_store_is_not_silently_healthy(tmp_path, capsys) -> None:
    # An absent ledger is what a broken enumerator produces. Reading it as "nothing owed"
    # is exactly the confidence that let 24 passes report success.
    m = load_module()
    rc = m.main(["--store", str(tmp_path / "never-written.jsonl"), "--pass-id", "pass-1", "--expect-store"])
    assert rc != 0
    assert json.loads(capsys.readouterr().out)["store_missing"] is True
