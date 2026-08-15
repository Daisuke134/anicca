from __future__ import annotations

import importlib.util
import json
from pathlib import Path


# P1a-9c (spec §0.1.6). Build the readback map from evidence the pass already writes.
#
# The delivery path persists paid-queue-live-dom.json every time it sends into a paid room.
# Adding the ordered messages to that file means the liability lane can prove "our answer
# sits below theirs" without opening the room a second time — no extra browser session, no
# second lease on the shared CDP tab, and no chance of the two observations disagreeing
# because they happened at different moments.
#
# Reading evidence rather than driving the browser also keeps the observer honest: it can
# only see what the loop actually recorded, so it cannot manufacture a readback the loop
# never earned.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "paid_lane_read_threads.py"


def load_module():
    spec = importlib.util.spec_from_file_location("paid_lane_read_threads", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def live_dom(root: Path, talkroom_id: str, *messages, name="paid-queue-live-dom.json") -> Path:
    d = root / f"agent-{talkroom_id}"
    d.mkdir(parents=True, exist_ok=True)
    path = d / name
    path.write_text(
        json.dumps(
            {
                "url": f"https://coconala.com/talkrooms/{talkroom_id}",
                "sent": True,
                "captured_at": "2026-08-05T03:00:00+00:00",
                "messages": [{"side": s, "text": t, "attachments": []} for s, t in messages],
            }
        )
    )
    return path


BUYER = ("buyer", "73ページのリンクが違います")
SELLER = ("seller", "修正しました")


def test_it_finds_the_rooms_the_pass_wrote_evidence_for(tmp_path) -> None:
    m = load_module()
    live_dom(tmp_path, "90000004", BUYER, SELLER)
    live_dom(tmp_path, "90000005", BUYER)
    states = m.read_thread_states(tmp_path)
    assert set(states) == {"90000004", "90000005"}


def test_the_state_says_whether_the_buyer_has_our_answer(tmp_path) -> None:
    m = load_module()
    live_dom(tmp_path, "90000004", BUYER, SELLER)
    live_dom(tmp_path, "90000005", SELLER, BUYER)
    states = m.read_thread_states(tmp_path)
    assert states["90000004"]["seller_after_buyer"] is True
    assert states["90000005"]["seller_after_buyer"] is False


def test_an_evidence_dir_with_no_sends_yields_nothing(tmp_path) -> None:
    # Not an error. Most passes send nothing into a paid room, and an empty map simply means
    # no liability can be closed from evidence this pass.
    m = load_module()
    assert m.read_thread_states(tmp_path) == {}


def test_a_file_without_ordered_messages_is_skipped_not_guessed(tmp_path) -> None:
    # Evidence written before this field existed. Deriving "answered" from its absence would
    # be inventing a readback.
    m = load_module()
    d = tmp_path / "agent-old"
    d.mkdir()
    (d / "paid-queue-live-dom.json").write_text(
        json.dumps({"url": "https://coconala.com/talkrooms/90000004", "latest_seller_message": "x"})
    )
    states = m.read_thread_states(tmp_path)
    assert states["90000004"]["seller_after_buyer"] is False


def test_unreadable_evidence_is_reported_rather_than_dropped(tmp_path) -> None:
    m = load_module()
    d = tmp_path / "agent-broken"
    d.mkdir()
    (d / "paid-queue-live-dom.json").write_text("{not json")
    states, errors = m.read_thread_states(tmp_path, with_errors=True)
    assert states == {}
    assert errors


def test_the_cli_emits_the_map_for_the_shell(tmp_path, capsys) -> None:
    m = load_module()
    live_dom(tmp_path, "90000004", BUYER, SELLER)
    rc = m.main(["--evidence-dir", str(tmp_path)])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["thread_states"]["90000004"]["seller_after_buyer"] is True
    assert payload["rooms_observed"] == 1


# --- what the pass meant to do, also taken from its own evidence ---------------------------


def manifest(root: Path, talkroom_id: str, *, sent=True, mode="answer", formal=False) -> Path:
    d = root / f"agent-{talkroom_id}"
    d.mkdir(parents=True, exist_ok=True)
    path = d / "paid-queue-evidence.json"
    path.write_text(json.dumps({
        "sent": sent, "mode": mode, "talkroom_id": talkroom_id,
        "formal_delivery_checkbox": formal,
    }))
    return path


def test_an_answer_that_was_sent_is_an_intent(tmp_path) -> None:
    m = load_module()
    manifest(tmp_path, "90000004")
    assert m.read_intents(tmp_path) == {"90000004": "answer"}


def test_a_formal_delivery_is_named_as_such(tmp_path) -> None:
    m = load_module()
    manifest(tmp_path, "90000004", mode="delivery", formal=True)
    assert m.read_intents(tmp_path) == {"90000004": "formal_delivery"}


def test_a_manifest_that_did_not_send_is_not_an_intent(tmp_path) -> None:
    # "we prepared a message" is not "we spoke". Treating it as one is how a customer waits
    # while the ledger says they were served.
    m = load_module()
    manifest(tmp_path, "90000004", sent=False)
    assert m.read_intents(tmp_path) == {}
