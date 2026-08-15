#!/usr/bin/env python3
"""Being stuck has to produce a question, not another acknowledgement."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import ask_buyer  # noqa: E402

# Copied from the real file the build agent wrote for order 91000002.
REAL_BLOCKED = {
    "version": 1,
    "status": "BLOCKED",
    "feedback_sha256": "57b8719d5bd8ff77a7f68614d9fe9e6a4dbc35411094f43fd82891a103bdcfda",
    "checks": [
        {"command": "find ...", "result": "制作入力、既存成果物、ビルドスクリプト、テストスクリプトは存在しない。"},
        {"command": "python3 ...", "result": "成果物の種類、内容、素材、仕様の指定なし。"},
    ],
}


def write_project(tmp_path, payload):
    root = tmp_path / "91000002"
    (root / "evidence").mkdir(parents=True)
    if payload is not None:
        (root / "evidence" / "acceptance-blocked.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return root


def test_the_agents_diagnosis_is_read(tmp_path):
    root = write_project(tmp_path, REAL_BLOCKED)
    state = ask_buyer.blocked_state(root)
    assert state["status"] == "BLOCKED"


def test_a_project_that_built_fine_is_not_blocked(tmp_path):
    root = write_project(tmp_path, {"status": "PASS"})
    assert ask_buyer.blocked_state(root) is None


def test_a_missing_or_broken_file_reads_as_not_blocked(tmp_path):
    assert ask_buyer.blocked_state(write_project(tmp_path, None)) is None
    root = tmp_path / "broken"
    (root / "evidence").mkdir(parents=True)
    (root / "evidence" / "acceptance-blocked.json").write_text("{", encoding="utf-8")
    assert ask_buyer.blocked_state(root) is None
    assert ask_buyer.blocked_state(None) is None


def test_the_same_blocker_has_one_identity():
    """A paid buyer asked the same question hourly is a buyer who refunds."""
    assert ask_buyer.blocker_key(REAL_BLOCKED) == REAL_BLOCKED["feedback_sha256"]


def test_a_buyers_answer_produces_a_new_identity():
    answered = dict(REAL_BLOCKED, feedback_sha256="a" * 64)
    assert ask_buyer.blocker_key(answered) != ask_buyer.blocker_key(REAL_BLOCKED)


def test_the_question_quotes_what_is_missing():
    prompt = ask_buyer.question_prompt(state=REAL_BLOCKED)
    assert "成果物の種類、内容、素材、仕様の指定なし" in prompt
    # Already paid: this is not a sales message.
    assert "既にお支払い済み" in prompt


def test_a_real_question_passes():
    body = (
        "着手が遅れており申し訳ございません。仕様を確定したく、"
        "①ご希望の成果物の形式 ②参考にされたい既存サイト ③素材データ の3点をお送りいただけますでしょうか。"
    )
    assert ask_buyer.check_question(body)["ok"] is True


def test_the_message_that_created_this_situation_is_refused():
    # Verbatim from the talkroom. Sent twice, asked nothing, order stalled.
    body = "ご購入いただき誠にありがとうございます。ご依頼の内容を拝見のうえ、対応を進めてまいります。ご確認いただきたい点がございましたら、こちらより追ってご一報いたします。"
    decision = ask_buyer.check_question(body)
    assert decision["ok"] is False
    assert "asks_nothing" in decision["violations"]


def test_an_empty_body_is_refused():
    assert ask_buyer.check_question("")["ok"] is False
    assert ask_buyer.check_question(None)["violations"] == ["empty"]


def test_politeness_alone_is_not_a_question():
    assert ask_buyer.check_question("よろしくお願いいたします。")["ok"] is False
