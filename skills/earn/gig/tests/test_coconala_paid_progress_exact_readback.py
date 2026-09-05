from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import coconala_paid_progress_browser as browser  # noqa: E402


def test_same_session_readback_requires_the_complete_normalized_message():
    message = "確認済みです。" * 30 + "今回の修正を反映しました。"
    prefix_collision = "確認済みです。" * 30 + "以前の別メッセージです。"
    state = {
        "seller_messages": [
            {"text": prefix_collision, "attachments": ["result.zip"]},
        ]
    }

    assert browser.matching_seller_text(state, message) is None
    assert browser.matching_seller_message(state, "result.zip", message) is None

    state["seller_messages"].append(
        {"text": " \n" + message.replace("。", "。\n"), "attachments": ["result.zip"]}
    )
    assert browser.matching_seller_text(state, message) == state["seller_messages"][-1]
    assert browser.matching_seller_message(state, "result.zip", message) == state["seller_messages"][-1]
    assert browser.matching_seller_message(state, "other.zip", message) is None

    expression = browser.browser_state_expression("result.zip")
    assert "==='続きを読む'" in expression
    assert "x.click()" in expression
    assert "requestAnimationFrame(()=>requestAnimationFrame(resolve))" in expression
