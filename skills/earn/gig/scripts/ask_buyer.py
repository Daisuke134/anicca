#!/usr/bin/env python3
"""When a paid order cannot be built, ask the buyer instead of inventing a deliverable.

Order 91000002 is the reason this exists. The buyer paid, said よろしくお願いいたします, and
the entire talkroom is two acknowledgements we sent:

    「ご不明な点や追加でお送りいただきたい資料がございましたら、こちらのトークルームよりご一報いたします」
    「ご確認いただきたい点がございましたら、こちらより追ってご一報いたします」

We needed something. We never asked. Every hour the build agent correctly wrote
``evidence/acceptance-blocked.json`` -- status BLOCKED, 「成果物の種類、内容、素材、仕様の
指定なし」 -- and then declared PASS in its manifest anyway, the validator refused the
fabricated package, the pass rolled back and failed, and an hour later it happened again.
Delivery is due 2026-08-11.

The validator is right and is left alone. What was missing is the branch where being stuck
produces a question rather than a lie.

Asking is bounded the same way follow-ups are, for a different reason: a buyer who has
already paid and is asked the same question every hour is a buyer who refunds. One question
per blocked state -- keyed by the blocker itself, so a *new* blocker earns a new question
and an unchanged one does not.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from buyer_voice import PERSONA  # noqa: E402

BLOCKED = "BLOCKED"
# Where the build agent leaves its diagnosis. Survives the parent's rollback, which
# discards the fabricated manifest but not this file -- measured on 91000002.
BLOCKED_EVIDENCE = Path("evidence") / "acceptance-blocked.json"
# The project ledger the delivery browser appends to after its own site readback.
PROJECT_LEDGER = Path("events.jsonl")
FORMAL_DELIVERY_EVENT = "FORMAL_DELIVERY_CONFIRMED"


def formal_delivery_recorded(project_root: Any) -> bool:
    """True when something has already gone out to this buyer as a formal delivery.

    Read from the project's own event ledger rather than from the live queue: by the time
    the question is composed the order may have left the queue entirely -- that is exactly
    what happened to 91000002 -- while the ledger row survives.
    """
    try:
        path = Path(str(project_root)) / PROJECT_LEDGER
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, TypeError, ValueError):
        return False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("event") == FORMAL_DELIVERY_EVENT:
            return True
    return False


def blocked_state(project_root: Any) -> dict[str, Any] | None:
    """The agent's diagnosis when it could not build, or None.

    Returns the evidence rather than a bool so the question can quote what was actually
    checked. A question that cannot say what is missing is another 「ご連絡いたします」.
    """
    try:
        path = Path(str(project_root)) / BLOCKED_EVIDENCE
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("status") != BLOCKED:
        return None
    return payload


def blocker_key(state: Any) -> str:
    """Identity of one blocked state.

    Built from the buyer feedback the agent read, so the same unanswered question is asked
    once and not hourly -- and so a buyer who *does* answer produces a new key, which earns
    a new question if their answer still leaves us stuck.
    """
    data = state if isinstance(state, dict) else {}
    digest = str(data.get("feedback_sha256") or "").strip()
    return digest or "unknown"


def missing_items(state: Any) -> list[str]:
    """What the agent looked for and did not find, in its own words."""
    data = state if isinstance(state, dict) else {}
    found: list[str] = []
    for check in data.get("checks") or []:
        if not isinstance(check, dict):
            continue
        result = str(check.get("result") or "").strip()
        if result:
            found.append(result)
    return found


def question_prompt(
    *, state: Any, conversation: Any = None, formal_delivery_observed: bool = False
) -> str:
    """Instructions for one message asking the buyer to unblock the order.

    ``formal_delivery_observed`` changes where the question starts. When something has
    already been sent to this buyer as the finished work and it was not the finished work
    -- 91000002 received a 1879-byte list of open questions marked 正式な納品 -- the buyer is
    now sitting in front of a file they believe is their order, with an approval clock
    running. Asking them for materials without mentioning that file reads as if we forgot
    what we sent them. This is the general rule for the situation, not that one order: it
    can recur, and it is already true of past orders delivered before the gate existed.
    """
    lines = [
        PERSONA,
        "",
        "この案件はすでにご購入いただいています。着手できない状態が続いているため、"
        "お客様に必要な情報を尋ねる日本語のメッセージを1件作成してください。",
        "",
        "★重要★: この方は既にお支払い済みです。営業ではありません。"
        "こちらが着手できていない状態なので、まず短く詫び、次に何が必要かを具体的に聞いてください。",
    ]
    # What was actually bought. Absent from every record the builder writes, and absent
    # from the compiled context too -- measured on the live 23:30 pass of 2026-08-07,
    # ``grep -c 企画 PAID_WORK.prompt.txt`` returned 0 for an order titled
    # 「ポケモン動画の企画・台本作成ができる方を募集します」. A question written without it asks
    # about a 題材 rather than about the job, which is what a form sounds like. Optional on
    # purpose: a record written by the builder carries no title and behaves as before.
    order_title = str((state if isinstance(state, dict) else {}).get("order_title") or "").strip()
    if order_title:
        lines += [
            "",
            f"★このお客様が購入されたのは「{order_title}」です。★"
            "質問は、この仕事そのものについて書いてください。"
            "題材や素材の確認だけで終わらせず、何をどれだけ、どういう形でお作りするかを聞いてください。",
        ]
    if formal_delivery_observed:
        lines += [
            "",
            "★この案件では、すでに1度「納品」としてファイルをお送りしてしまっています。"
            "そしてそれは完成した制作物ではなく、こちらがまだ確認できていない事項をまとめた資料でした。"
            "お客様は今、それをご注文の品だと思って見ています。★",
            "",
            "この状況で書くべき内容:",
            "- 最初に謝る。言い訳より先に謝罪を置く。",
            "- 先にお送りしたファイルが完成した制作物ではなく、"
            "確認が必要な事項をまとめた資料だったことを、こちらから正直に伝える。",
            "- ★そのファイルの承認・確認をお願いしない★。承認を求めるのではなく、"
            "制作を始めるために足りない情報をいただきたい、と伝える。",
            "- 何が必要かは、お客様が実際に書かれたご依頼内容から導く。"
            "この案件で本当に必要な項目だけを挙げる（一般論の要件リストにしない）。",
            "- 納期に触れ、情報をいただき次第そこに間に合わせる意思を書く。",
            "- 言い訳をしない。こちら側の事情・手順・システムの説明は一切書かない。",
            "  なぜそうなったかではなく、これからどうするかだけを書く。",
        ]
    lines += [
        "",
        "必須:",
        "- 「ご連絡いたします」で終わらせない。★このメッセージ自体が、その連絡★。",
        "- 必要な物を箇条書きで具体的に挙げる（3〜5点）。相手が1回の返信で全部渡せる形にする。",
        "- 分からない事を分かっているふりをしない。仕様が未定なら、こちらから案を1つ提示して"
        "「この方向で進めてよいか」を聞く形にすると、相手の負担が小さい。",
        "- 納期に触れる。必要なら延長の相談を切り出してよい。",
        "- 400文字以内。" if formal_delivery_observed else "- 300文字以内。",
        "",
        "禁止:",
        "- 外部サイトのURL、メールアドレス、電話番号、SNSのID",
        "- ココナラ外での決済・振込の依頼",
        "- 「対応を進めます」だけで何も聞かない定型文（★これを2回送って詰まったのが今の状態★）",
        "",
        f"着手できない理由（自動診断）: {json.dumps(missing_items(state), ensure_ascii=False)}",
    ]
    if conversation:
        lines.append(f"これまでの会話: {conversation}")
    return "\n".join(lines)


# The two messages already sent. A third of the same shape is worse than silence: it tells
# the buyer we are not reading our own thread.
_EMPTY_ACKNOWLEDGEMENT = (
    "ご連絡いたします",
    "対応を進めます",
    "確認のうえ",
)


def check_question(body: Any) -> dict[str, Any]:
    """Refuse a question that does not actually ask anything."""
    text = str(body or "").strip()
    violations: list[str] = []
    if not text:
        return {"ok": False, "violations": ["empty"]}
    if "?" not in text and "？" not in text and "ください" not in text and "でしょうか" not in text:
        # No question mark and no request form: this is another acknowledgement.
        violations.append("asks_nothing")
    stripped = text
    for phrase in _EMPTY_ACKNOWLEDGEMENT:
        stripped = stripped.replace(phrase, "")
    if len(stripped.strip()) < 30:
        violations.append("boilerplate_only")
    return {"ok": not violations, "violations": violations}
