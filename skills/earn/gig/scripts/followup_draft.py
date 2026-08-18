#!/usr/bin/env python3
"""Write one follow-up to a buyer who went quiet, and refuse the drafts that break rules.

A follow-up goes to a real person on a platform that can suspend the account, so what
Coconala forbids is checked by code rather than hoped for:

  外部サービスへの誘導   https://coconala-support.zendesk.com/hc/ja/articles/218179168
  プラットフォーム外決済 https://coconala-support.zendesk.com/hc/ja/articles/10003485737881

The prompt carries the same purchase gate P3-1 put in the first reply. kiki_1115 was told
the deliverable would arrive 本日中, free, with no gate -- and went silent. A follow-up
that repeats that promise repeats the mistake that created the silence.

check_draft is deterministic: a rule that decides whether a message may reach a stranger
must not depend on a model agreeing with itself twice.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from buyer_voice import PERSONA
except ImportError:  # loaded by path with scripts/ absent from sys.path
    import importlib.util as _importlib_util

    _spec = _importlib_util.spec_from_file_location(
        "buyer_voice", Path(__file__).with_name("buyer_voice.py")
    )
    assert _spec and _spec.loader
    _buyer_voice = _importlib_util.module_from_spec(_spec)
    _spec.loader.exec_module(_buyer_voice)
    PERSONA = _buyer_voice.PERSONA


# Yesware's data allows six touches; the cap here is three (see followup_candidates), so
# the third is the last one that can legally exist and is written as a graceful exit.
LAST_FOLLOWUP_INDEX = 2

_URL = re.compile(r"https?://|www\.", re.IGNORECASE)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE = re.compile(r"0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4}")
_SOCIAL = re.compile(
    r"(LINE|ライン|Twitter|X\s*のDM|Instagram|インスタ|Discord|Slack|Skype|Zoom|"
    r"チャットワーク|Chatwork|Telegram)",
    re.IGNORECASE,
)
_OFF_PLATFORM_PAYMENT = re.compile(
    r"(銀行振込|直接お支払|直接支払|振込先|口座番号|PayPay|現金|外部決済|"
    r"サイト外.{0,6}(決済|支払))"
)

# The sentence that lost kiki_1115: 「最短で本日中に、初回の環境構成案と生成設定・プロンプト
# 例をお送りします」-- a deliverable, free, before any purchase. The prompt already forbids
# it, but a prompt is a request, and the reason this follow-up exists at all is that the
# request was not enough the first time.
_DELIVERY_PROMISE = re.compile(
    r"(お送りします|ご提出します|提出します|お渡しします|納品します|"
    r"作成してお送り|お届けします)"
)
_PURCHASE_GATE = re.compile(r"(ご購入後|購入後|ご購入いただ|ご購入くださ|ご購入当日)")


def followup_prompt(
    *, conversation: Any, followups_sent: int, silent_days: float
) -> str:
    """Instructions for one follow-up, shaped by how many have already gone out."""
    sent = int(followups_sent or 0)
    lines = [
        PERSONA,
        "",
        "相手からの返信が途絶えた会話へ、今すぐ送信できる日本語のフォローアップを1件"
        "作成してください。相手はまだ購入前の見込みのお客様です。",
        "",
        # 「直近」 rather than 「最後」: the closing instruction below is the only place
        # that word may appear, and a status line that borrows it would tell an early
        # follow-up to sign off for good.
        f"状況: 直近にこちらが送ってから {silent_days:.0f} 日、返信がありません。"
        f"これまでのフォローアップ回数: {sent} 回。",
        "",
        "必須:",
        "- 前回までの提案を繰り返さない。相手はそれを見た上で動いていないので、"
        "同じ情報は判断材料にならない。毎回、新しい価値（具体化した提案、想定納期、"
        "判断に必要な情報）を1点だけ加える。",
        "- 着手はご購入後であることを明示する。成果物・サンプル・構成案を購入前に"
        "送ると約束しない。",
        "- 納期は購入を起点に示す。",
        "- 催促の語調にしない。相手が忙しいか、必要でなくなった可能性を前提にする。",
        "- 200文字以内。短いほど返信されやすい。",
    ]
    if sent >= LAST_FOLLOWUP_INDEX:
        lines.append(
            "- ★これが最後の連絡である★。返信を求めず、"
            "「またご入用の際にお声がけください」の形で自然に閉じる。"
            "相手が返信しないことを選べる文にする。"
        )
    lines.extend([
        "",
        "禁止（規約違反。1つでも含めば送信されない）:",
        "- 外部サイトのURL、メールアドレス、電話番号、SNSのID",
        "- ココナラ外での決済・振込の依頼",
        "",
        f"conversation={conversation}",
    ])
    return "\n".join(lines)


def check_draft(body: Any) -> dict[str, Any]:
    """Refuse a draft that would break the platform's rules.

    Deterministic and fail-closed: an empty body is refused too, because sending silence
    dressed as a message spends one of the three chances this buyer will ever get.
    """
    text = str(body or "").strip()
    violations: list[str] = []
    if not text:
        violations.append("empty")
        return {"ok": False, "violations": violations}
    if _URL.search(text):
        violations.append("external_link")
    if _EMAIL.search(text) or _PHONE.search(text) or _SOCIAL.search(text):
        violations.append("external_contact")
    if _OFF_PLATFORM_PAYMENT.search(text):
        violations.append("off_platform_payment")
    # Only messages that actually promise something need a gate. A short nudge that offers
    # nothing is the recommended first follow-up, and demanding a purchase clause there
    # would block precisely the message most likely to earn a reply.
    if _DELIVERY_PROMISE.search(text) and not _PURCHASE_GATE.search(text):
        violations.append("unpaid_delivery_promise")
    return {"ok": not violations, "violations": violations}
