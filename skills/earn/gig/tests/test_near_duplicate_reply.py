from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


# kiki_1115, 2026-08-06: we sent a full proposal at 11:46 and a near-identical one at
# 13:01. Between them the buyer said only 「宜しくお願い致します。」 -- no new request. The
# existing guard compares outgoing_hash exactly, and the two bodies are not byte-identical
# (measured similarity 0.741), so both went out. The buyer then went silent and the thread
# joined the 24 of 30 nobody will touch again.


def load():
    spec = importlib.util.spec_from_file_location(
        "near_duplicate_reply", SCRIPTS / "near_duplicate_reply.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIRST = (
    "ありがとうございます。かしこまりました。参考例に近い、ご担当者様のSNS投稿に"
    "使える自然な人物写真をローカル環境で生成できるよう、まずは推奨環境・モデル選定・基本設定"
    "を整理します。そのうえで、自然な肌感／表情／背景を再現しやすいプロンプト例と、破綻を減ら"
    "す調整手順をまとめてご案内します。最短で本日中に、初回の環境構成案と生成設定・プロンプト"
    "例をお送りします。"
)
SECOND = (
    "承知いたしました。Grokのサンプルに近い、所属モデル様のSNS投稿で使える自然な人物写真を"
    "ローカル環境で再現する前提で進めます。まず推奨の生成環境・モデル構成と基本設定を整理し、"
    "自然な肌感／表情／背景を出すプロンプト例、破綻を抑える調整手順まで実用できる形でまとめ"
    "ます。最短で本日中に初回の環境構成案と生成設定をお送りします。"
)


def test_the_two_messages_that_actually_shipped_are_caught() -> None:
    m = load()
    assert m.is_near_duplicate(SECOND, [FIRST]) is True


def test_a_genuinely_different_reply_goes_through() -> None:
    m = load()
    other = "ご購入後はまず、元画像のレイアウトと使用しているフォントを確認したうえで、Canvaでの再現作業に着手します。"
    assert m.is_near_duplicate(other, [FIRST]) is False


def test_the_first_reply_in_a_thread_always_goes_through() -> None:
    # Nothing to repeat yet. Blocking here would silence a buyer who has never heard from us.
    m = load()
    assert m.is_near_duplicate(FIRST, []) is False
    assert m.is_near_duplicate(FIRST, None) is False


def test_only_our_own_last_message_is_compared() -> None:
    # Comparing against the whole history makes suppression run away: in a long thread
    # almost anything resembles something said earlier.
    m = load()
    assert m.is_near_duplicate(FIRST, ["無関係な文", FIRST]) is True
    assert m.is_near_duplicate(FIRST, [FIRST, "全く違う内容の最新メッセージです"]) is False


def test_whitespace_and_empties_do_not_create_false_matches() -> None:
    m = load()
    assert m.is_near_duplicate("", [FIRST]) is False
    assert m.is_near_duplicate(FIRST, [""]) is False
    assert m.is_near_duplicate(FIRST, ["   \n  "]) is False


def test_the_threshold_sits_between_the_two_measured_clusters() -> None:
    # Measured 2026-08-06, not guessed. The pair that actually shipped scores 0.741; a
    # different job scores 0.13 and a genuine follow-up that builds on the last message
    # scores 0.079. The clusters are far apart, so 0.60 has margin on both sides.
    #
    # An earlier draft of this spec said 0.85, which would have let the real duplicate
    # through -- 0.741 is below it. The number has to come from the measurement.
    m = load()
    assert m.NEAR_DUPLICATE_RATIO == 0.60
    assert m.similarity(FIRST, SECOND) > m.NEAR_DUPLICATE_RATIO
    different = "ご購入後はまず、元画像のレイアウトと使用しているフォントを確認したうえで、Canvaでの再現作業に着手します。"
    assert m.similarity(FIRST, different) < m.NEAR_DUPLICATE_RATIO


def test_execute_reply_refuses_before_preparing_any_state(monkeypatch, tmp_path) -> None:
    # The check must run before controller.prepare: a suppressed reply should leave no
    # intent, no revision, no claim spent. Refusing costs one pass; repeating cost us the
    # kiki_1115 conversation outright.
    spec = importlib.util.spec_from_file_location(
        "reply_executor_nd", SCRIPTS / "reply_executor.py"
    )
    assert spec and spec.loader
    executor = importlib.util.module_from_spec(spec)
    sys.modules["reply_executor_nd"] = executor
    spec.loader.exec_module(executor)

    monkeypatch.setenv("GIG_REPLY_TRANSCRIPTS", str(tmp_path / "t.jsonl"))
    prepared: list[str] = []

    class Browser:
        def read_before(self):
            return ({"conversation": []}, {"seller_messages": [FIRST]})

    class Controller:
        def claim(self, **kwargs):
            return {"action_id": 1, "thread_id": "93000004", "revision": 1,
                    "fencing_token": 1, "thread_url": "https://coconala.com/x"}

        def prepare(self, **kwargs):
            prepared.append("prepare")
            raise AssertionError("prepare must not run for a suppressed duplicate")

    result = executor.execute_reply(
        controller=Controller(),
        queue_item={"talkroom_id": "93000004"},
        owner="test",
        clock=lambda: 1,
        compose=lambda context: SECOND,
        browser=Browser(),
        paid_talkroom_ids=frozenset(),
    )

    assert result["status"] == "near_duplicate_suppressed"
    assert result["verified"] is False
    assert result["blind_retry_allowed"] is False
    assert prepared == []


def test_execute_reply_still_sends_something_new(monkeypatch, tmp_path) -> None:
    # The guard must not become a reason nobody ever hears from us.
    spec = importlib.util.spec_from_file_location(
        "reply_executor_nd_ok", SCRIPTS / "reply_executor.py"
    )
    assert spec and spec.loader
    executor = importlib.util.module_from_spec(spec)
    sys.modules["reply_executor_nd_ok"] = executor
    spec.loader.exec_module(executor)

    monkeypatch.setenv("GIG_REPLY_TRANSCRIPTS", str(tmp_path / "t.jsonl"))
    reached: list[str] = []

    class Browser:
        def read_before(self):
            return ({"conversation": []}, {"seller_messages": [FIRST]})

    class Controller:
        def claim(self, **kwargs):
            return {"action_id": 1, "thread_id": "1", "revision": 1,
                    "fencing_token": 1, "thread_url": "https://coconala.com/x"}

        def prepare(self, **kwargs):
            reached.append("prepare")
            raise RuntimeError("stop here")

    try:
        executor.execute_reply(
            controller=Controller(),
            queue_item={"talkroom_id": "1"},
            owner="test",
            clock=lambda: 1,
            compose=lambda context: "ご購入後はCanvaで再現作業を開始します。",
            browser=Browser(),
            paid_talkroom_ids=frozenset(),
        )
    except Exception:
        pass

    assert reached == ["prepare"]
