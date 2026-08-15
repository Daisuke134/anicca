from __future__ import annotations

import importlib.util
import json
from pathlib import Path


# P1b (spec §0.1.4 真因1, §0.1.6). Put what the buyer actually said into the lane's context.
#
# The measured failure: b1-context was 570 bytes of URLs and reasons, so the lane was told to
# go and look. Its evidence contract asked for a screenshot and never for a scroll, so it read
# the top of the thread, called it a purchase acknowledgement, and returned observed_no_action.
# Underneath, unread, the buyer had written that the fix did not match the instructions and
# that they would not force us to continue.
#
# The conversation was already on disk the whole time — projects/<id>/source/talkroom/
# messages.jsonl — so this is not new collection, it is handing the lane what the loop
# already knows. Navigation was never the hard part; being told to navigate instead of being
# given the text is what produced 24 passes of nothing.
#
# Bounded on purpose. Every branch of every lane pays for this context, so buyer messages are
# kept whole (there are few and they are the point) while our own are capped.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "b1_conversation_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("b1_conversation_gate", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def messages_file(root: Path, talkroom_id: str, *rows) -> Path:
    d = root / talkroom_id / "source" / "talkroom"
    d.mkdir(parents=True, exist_ok=True)
    path = d / "messages.jsonl"
    path.write_text(
        "\n".join(
            json.dumps({"side": side, "text": text, "sent_at": sent_at}, ensure_ascii=False)
            for side, text, sent_at in rows
        )
        + "\n",
        encoding="utf-8",
    )
    return path


BUYER_CANCEL = (
    "buyer",
    "指示書のとおりには反映されておりませんでした。無理にご対応いただくつもりはございません。",
    "2026-08-04T10:00:00+00:00",
)
SELLER_PROMISE = ("seller", "確認いたします", "2026-08-04T11:00:00+00:00")


def test_the_buyer_words_reach_the_lane(tmp_path) -> None:
    m = load_module()
    projects = tmp_path / "projects"
    messages_file(projects, "90000004", BUYER_CANCEL, SELLER_PROMISE)
    convo = m.talkroom_conversation("90000004", projects_root=projects)
    assert "無理にご対応いただくつもりはございません" in json.dumps(convo, ensure_ascii=False)


def test_the_last_thing_the_buyer_said_is_called_out(tmp_path) -> None:
    # Buried in a list of twenty, the decisive sentence is easy to skim past. It gets its own
    # field so the lane cannot miss it.
    m = load_module()
    projects = tmp_path / "projects"
    messages_file(projects, "90000004", BUYER_CANCEL, SELLER_PROMISE)
    convo = m.talkroom_conversation("90000004", projects_root=projects)
    assert "指示書のとおりには反映されて" in convo["buyer_last_said"]


def test_who_has_been_talking_is_visible(tmp_path) -> None:
    # 14 from us and 6 from them was a symptom nobody could see. Counting makes it legible.
    m = load_module()
    projects = tmp_path / "projects"
    messages_file(projects, "90000004", BUYER_CANCEL, SELLER_PROMISE, SELLER_PROMISE)
    convo = m.talkroom_conversation("90000004", projects_root=projects)
    assert convo["counts"] == {"buyer": 1, "seller": 2}


def test_our_own_messages_are_capped_but_the_buyer_is_kept_whole(tmp_path) -> None:
    m = load_module()
    projects = tmp_path / "projects"
    long_buyer = ("buyer", "あ" * 3000, "2026-08-04T10:00:00+00:00")
    long_seller = ("seller", "い" * 3000, "2026-08-04T11:00:00+00:00")
    messages_file(projects, "90000004", long_buyer, long_seller)
    convo = m.talkroom_conversation("90000004", projects_root=projects)
    texts = {row["side"]: row["text"] for row in convo["messages"]}
    assert len(texts["buyer"]) == 3000
    assert len(texts["seller"]) < 3000


def test_a_room_with_no_recorded_conversation_says_so(tmp_path) -> None:
    # Absence must be visible. Reading "no messages" as "nothing to answer" is the original
    # bug, so the lane is told the file was missing rather than handed an empty list.
    m = load_module()
    convo = m.talkroom_conversation("90000004", projects_root=tmp_path / "projects")
    assert convo["source_missing"] is True
    assert convo["messages"] == []


def test_a_corrupt_line_does_not_hide_the_rest(tmp_path) -> None:
    m = load_module()
    projects = tmp_path / "projects"
    path = messages_file(projects, "90000004", BUYER_CANCEL)
    path.write_text(path.read_text() + "{not json\n", encoding="utf-8")
    convo = m.talkroom_conversation("90000004", projects_root=projects)
    assert convo["counts"]["buyer"] == 1
    assert convo["unreadable_lines"] == 1


def test_the_built_context_carries_the_conversation(tmp_path) -> None:
    # The end-to-end shape: what build_context writes is what the lane reads.
    m = load_module()
    projects = tmp_path / "projects"
    messages_file(projects, "90000004", BUYER_CANCEL, SELLER_PROMISE)
    # TODO 3c moved paid orders out of this lane's target set, so the room that carries the
    # conversation is now an unbought enquiry. P1b's point is unchanged and still tested:
    # the lane is handed what the buyer said instead of being told to go and look.
    snapshot = {
        "inbox": {"url": "https://coconala.com/message?fromMyPage=true", "not_found": False},
        "orders": [],
        "inquiries": [{
            "talkroom_id": "90000004",
            "talkroom_url": "https://coconala.com/talkrooms/90000004",
            "reply_required": True,
        }],
        "quotes": [],
    }
    context = m.build_context(
        snapshot,
        {"items": []},
        tmp_path / "snap.json",
        tmp_path / "queue.json",
        projects_root=projects,
    )
    room = next(r for r in context["actionable_talkrooms"] if r["talkroom_id"] == "90000004")
    assert "無理にご対応いただくつもりはございません" in json.dumps(room, ensure_ascii=False)
