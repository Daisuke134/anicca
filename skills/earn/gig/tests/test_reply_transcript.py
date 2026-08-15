from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


# 2026-08-06: two real conversations showed the whole difference between revenue and
# silence -- 買い手B answered "可能です" and gated the work on purchase, and closed;
# kiki_1115 promised to send the deliverable "本日中" for free, and the buyer went quiet.
# Neither is readable by the loop: connector_intents keeps only outgoing_hash,
# reply-lane-result.json has no body, and pre-purchase DMs are persisted nowhere. The
# comparison was only possible because Dais sent screenshots.


def load():
    spec = importlib.util.spec_from_file_location(
        "reply_transcript", SCRIPTS / "reply_transcript.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTEXT = {
    "conversation": [
        {"side": "buyer", "body": "Canvaデータに直して仕上げてほしいです"},
        {"side": "seller", "body": "承知しました"},
        {"side": "buyer", "body": "可能でしょうか？"},
    ]
}


def test_the_row_keeps_both_sides_of_the_exchange() -> None:
    m = load()
    row = m.transcript_row(
        talkroom_id="90000004",
        context=CONTEXT,
        outgoing_body="ご購入後、まず元画像の構成を確認し作業を開始します。",
        outgoing_hash="a" * 64,
        sent_at=1786000000,
        status="replied",
    )
    assert row["talkroom_id"] == "90000004"
    assert row["outgoing_body"] == "ご購入後、まず元画像の構成を確認し作業を開始します。"
    assert row["buyer_last_said"] == "可能でしょうか？"
    assert row["outgoing_hash"] == "a" * 64
    assert row["sent_at"] == 1786000000
    assert row["status"] == "replied"
    # The outcome is unknown at send time; a later pass labels it. Writing a guess here
    # would poison the very dataset this exists to build.
    assert row["outcome"] is None


def test_the_whole_exchange_is_kept_not_just_the_last_line() -> None:
    # "Why did this convert" is rarely answerable from one message.
    m = load()
    row = m.transcript_row(
        talkroom_id="1", context=CONTEXT, outgoing_body="x",
        outgoing_hash="b" * 64, sent_at=1, status="replied",
    )
    assert len(row["conversation"]) == 3
    assert row["conversation"][0]["side"] == "buyer"


def test_a_context_without_a_conversation_still_records_our_words() -> None:
    # Our own body is the half we control and the half we are trying to improve. Losing it
    # because the buyer side was unreadable would defeat the purpose.
    m = load()
    row = m.transcript_row(
        talkroom_id="1", context={}, outgoing_body="送信本文",
        outgoing_hash="c" * 64, sent_at=1, status="replied",
    )
    assert row["outgoing_body"] == "送信本文"
    assert row["conversation"] == []
    assert row["buyer_last_said"] == ""


def test_a_malformed_conversation_does_not_raise() -> None:
    m = load()
    row = m.transcript_row(
        talkroom_id="1", context={"conversation": "not a list"},
        outgoing_body="x", outgoing_hash="d" * 64, sent_at=1, status="replied",
    )
    assert row["conversation"] == []


import json as json_module
import stat


def test_the_row_lands_on_disk_as_one_json_line(tmp_path) -> None:
    m = load()
    path = tmp_path / "reply-transcripts.jsonl"
    row = m.transcript_row(
        talkroom_id="90000004", context=CONTEXT, outgoing_body="ご購入後に着手します",
        outgoing_hash="a" * 64, sent_at=1786000000, status="replied",
    )
    assert m.append_transcript(path, row) is True
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json_module.loads(lines[0])["outgoing_body"] == "ご購入後に着手します"


def test_appending_twice_keeps_both(tmp_path) -> None:
    m = load()
    path = tmp_path / "reply-transcripts.jsonl"
    for n in range(2):
        m.append_transcript(path, m.transcript_row(
            talkroom_id=str(n), context=CONTEXT, outgoing_body=f"body {n}",
            outgoing_hash="a" * 64, sent_at=n, status="replied",
        ))
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_the_file_is_not_world_readable(tmp_path) -> None:
    # These are real buyers' words. They stay on this machine at the same permission the
    # rest of the evidence tree uses.
    m = load()
    path = tmp_path / "reply-transcripts.jsonl"
    m.append_transcript(path, m.transcript_row(
        talkroom_id="1", context=CONTEXT, outgoing_body="x",
        outgoing_hash="a" * 64, sent_at=1, status="replied",
    ))
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_an_unwritable_path_returns_false_instead_of_raising(tmp_path) -> None:
    # This runs on the send path. A recorder that raises would cost a real reply to a real
    # buyer -- the observation must never outrank the revenue it observes.
    m = load()
    blocked = tmp_path / "not-a-dir"
    blocked.write_text("i am a file", encoding="utf-8")
    assert m.append_transcript(blocked / "inner" / "t.jsonl", {"a": 1}) is False


def test_an_unserialisable_row_returns_false_instead_of_raising(tmp_path) -> None:
    m = load()
    path = tmp_path / "reply-transcripts.jsonl"
    assert m.append_transcript(path, {"bad": object()}) is False


def test_execute_reply_records_the_exchange(tmp_path, monkeypatch) -> None:
    # The recorder has to sit where context and outgoing_body are both in scope. Before
    # reply_executor.py:59 there is no reply; after :60 the context is dropped.
    spec = importlib.util.spec_from_file_location(
        "reply_executor_p3", SCRIPTS / "reply_executor.py"
    )
    assert spec and spec.loader
    executor = importlib.util.module_from_spec(spec)
    sys.modules["reply_executor_p3"] = executor
    spec.loader.exec_module(executor)

    path = tmp_path / "reply-transcripts.jsonl"
    monkeypatch.setenv("GIG_REPLY_TRANSCRIPTS", str(path))

    recorded: list[dict] = []

    class Browser:
        def read_before(self):
            return CONTEXT, {"messages": []}

        def fill(self, body):
            return None

        def click(self):
            return None

        def read_after(self):
            return {"messages": []}

    class Controller:
        def claim(self, **kwargs):
            return {"action_id": 1, "thread_id": "90000004", "revision": 1,
                    "fencing_token": 1, "thread_url": "https://coconala.com/x"}

        def prepare(self, **kwargs):
            recorded.append(kwargs)
            raise RuntimeError("stop after compose")

    try:
        executor.execute_reply(
            controller=Controller(),
            queue_item={"talkroom_id": "90000004"},
            owner="test",
            clock=lambda: 1786000000,
            compose=lambda context: "ご購入後、作業を開始します。",
            browser=Browser(),
            paid_talkroom_ids=frozenset(),
        )
    except Exception:
        pass

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    written = json_module.loads(lines[0])
    assert written["outgoing_body"] == "ご購入後、作業を開始します。"
    assert written["buyer_last_said"] == "可能でしょうか？"


def test_a_failing_recorder_never_costs_the_reply(tmp_path, monkeypatch) -> None:
    # Point the transcript at an impossible path and confirm compose/prepare still ran.
    spec = importlib.util.spec_from_file_location(
        "reply_executor_p3_fail", SCRIPTS / "reply_executor.py"
    )
    assert spec and spec.loader
    executor = importlib.util.module_from_spec(spec)
    sys.modules["reply_executor_p3_fail"] = executor
    spec.loader.exec_module(executor)

    blocked = tmp_path / "blocked"
    blocked.write_text("file", encoding="utf-8")
    monkeypatch.setenv("GIG_REPLY_TRANSCRIPTS", str(blocked / "inner" / "t.jsonl"))

    reached: list[str] = []

    class Browser:
        def read_before(self):
            return CONTEXT, {"messages": []}

    class Controller:
        def claim(self, **kwargs):
            return {"action_id": 1, "thread_id": "1", "revision": 1,
                    "fencing_token": 1, "thread_url": "https://coconala.com/x"}

        def prepare(self, **kwargs):
            reached.append("prepare")
            raise RuntimeError("stop after compose")

    try:
        executor.execute_reply(
            controller=Controller(),
            queue_item={"talkroom_id": "1"},
            owner="test",
            clock=lambda: 1,
            compose=lambda context: "本文",
            browser=Browser(),
            paid_talkroom_ids=frozenset(),
        )
    except Exception:
        pass

    assert reached == ["prepare"]


def test_the_recorder_refuses_the_production_ledger_under_pytest(monkeypatch, tmp_path) -> None:
    # 2026-08-06: running this suite wrote 94 fixture rows -- talkroom_id "43",
    # outgoing_body "reply-2" -- straight into ~/gig/reply-transcripts.jsonl, the ledger
    # that P3-3 will mine to learn which wording converts. Teaching data poisoned by test
    # fixtures is worse than no data: it looks real and it is not.
    #
    # test_reply_executor.py does not set GIG_REPLY_TRANSCRIPTS, and it never should have to
    # remember. The recorder itself refuses the production path while pytest is loaded.
    spec = importlib.util.spec_from_file_location(
        "reply_executor_p3_guard", SCRIPTS / "reply_executor.py"
    )
    assert spec and spec.loader
    executor = importlib.util.module_from_spec(spec)
    sys.modules["reply_executor_p3_guard"] = executor
    spec.loader.exec_module(executor)

    monkeypatch.delenv("GIG_REPLY_TRANSCRIPTS", raising=False)
    home_ledger = Path(os.path.expanduser("~/gig/reply-transcripts.jsonl"))
    before = home_ledger.stat().st_size if home_ledger.exists() else 0

    executor._record_transcript(
        talkroom_id="43", context=CONTEXT, outgoing_body="reply-2", sent_at=1
    )

    after = home_ledger.stat().st_size if home_ledger.exists() else 0
    assert after == before, "a test must never append to the production transcript ledger"


def test_the_recorder_still_writes_when_a_path_is_given(monkeypatch, tmp_path) -> None:
    # The guard must not silence real production writes -- only the unset-path default.
    spec = importlib.util.spec_from_file_location(
        "reply_executor_p3_guard_ok", SCRIPTS / "reply_executor.py"
    )
    assert spec and spec.loader
    executor = importlib.util.module_from_spec(spec)
    sys.modules["reply_executor_p3_guard_ok"] = executor
    spec.loader.exec_module(executor)

    path = tmp_path / "explicit.jsonl"
    monkeypatch.setenv("GIG_REPLY_TRANSCRIPTS", str(path))
    executor._record_transcript(
        talkroom_id="1", context=CONTEXT, outgoing_body="body", sent_at=1
    )
    assert path.exists() and path.read_text(encoding="utf-8").strip()


def test_the_real_conversation_key_is_text_not_body() -> None:
    # Measured 2026-08-06 against a live b1-context: the conversation rows this loop
    # actually produces carry the message under "text". Reading only "body" stored 27 rows
    # whose every body was empty and a buyer_last_said of "" -- a transcript that proves a
    # reply happened while hiding everything anyone would want to learn from it.
    m = load()
    row = m.transcript_row(
        talkroom_id="90000004",
        context={"conversation": [
            {"side": "system", "text": ""},
            {"side": "buyer", "text": "挙動につきましてはブラウザ上で"},
            {"side": "seller", "text": "承知しました"},
        ]},
        outgoing_body="ご購入後に着手します",
        outgoing_hash="a" * 64,
        sent_at=1,
        status="composed",
    )
    assert row["buyer_last_said"] == "挙動につきましてはブラウザ上で"
    assert [r["body"] for r in row["conversation"]] == [
        "挙動につきましてはブラウザ上で", "承知しました"
    ]


def test_body_still_works_for_callers_that_use_it() -> None:
    m = load()
    row = m.transcript_row(
        talkroom_id="1",
        context={"conversation": [{"side": "buyer", "body": "旧キー"}]},
        outgoing_body="x", outgoing_hash="a" * 64, sent_at=1, status="composed",
    )
    assert row["buyer_last_said"] == "旧キー"
