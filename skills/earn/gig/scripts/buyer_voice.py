#!/usr/bin/env python3
"""How we sound to a paying customer, and what may never reach one.

2026-08-06T19:04:49Z the buyer of order 91000002 received this from us:

    お世話になっております。ご注文いただいた制作物が仕上がりました。
    確認した内容は以下のとおりです。
    ・現在確認できる買い手からのメッセージと取引情報を確認資料としてまとめました。
    ・記載のない制作内容は推測せず、未確認の条件として明記しました。
    ・作業を始める前に必要な確認事項を買い手向けにまとめました。
    制作物を正式に納品いたします。内容のご確認をお願いいたします。

    添付: delivery-sample.md
    パッケージSHA-256: f0ce97066e7f441f5c91c0799131d2c750e6d0d5ee2b65bcc7a6918ec0474680

A buyer reading that concludes a bot wrote it, and they are right. Two different
failures produced it and they need two different fixes:

  PERSONA      the generating prompts never said who is speaking, so the model
               wrote a status report. A prompt fix.
  check_style  the delivery text was not written by a model at all -- it was a
               hardcoded template concatenating an internal digest. A prompt
               cannot fix a string the code builds, so the last chokepoint
               before send refuses internal tokens outright.

★ check_style does not judge tone ★. Whether prose sounds human is the model's
job; this function only answers "does an internal token appear in text a
customer will read", which is objective and therefore safe to fail closed on.
"""

from __future__ import annotations

import re


PERSONA = """あなたはココナラで自分のサービスを販売している個人の出品者です。会社の窓口でも、社内システムの報告係でもありません。
この文章を読むのは、お金を払ってくださる一人のお客様です。読んだ人が「人が書いた文章だ」と感じる、自然な日本語で書いてください。

書き方:
- お客様にとって何が良くなったのか、何が受け取れるのかを先に書く。こちらが何をしたかの説明は、そのあとに必要な分だけ。
- お客様に次にしてほしいことを1つだけ、はっきり示す。あれもこれもと並べない。
- 丁寧に、ただし硬すぎない。定型のあいさつで埋めず、この案件のことを書く。

してはいけないこと:
- 「・〜しました」を並べた作業報告にしない。箇条書きの羅列は、人ではなく機械が書いた文面に見える。
- 社内用語を書かない: 検証 / PASS / FAIL / パッケージ / ハッシュ / SHA / エビデンス / ステータス のような、こちら側の作業管理でしか使わない言葉。
- こちらの内部処理を説明しない。どんな手順で確認したか、どのファイルをどう生成したかはお客様には関係がない。お客様が受け取る価値だけを書く。"""


# Ordered most-specific first, so the code returned for a given leak names the
# most informative thing found rather than an incidental substring of it.
#
# ASCII-only boundaries: a Japanese customer message is dense with characters
# Python's \b treats as word characters, so \bPASS\b would NOT fire inside
# 「検証PASS」. Explicit [0-9A-Za-z_] lookarounds fire there and still refuse to
# match "pass" inside "password" or "FAIL" inside "FAILED".
_ASCII = "[0-9A-Za-z_]"
_CHECKS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # A 64-hex digest is never something a customer asked for.
    ("sha256_digest", re.compile(rf"(?<!{_ASCII})[0-9a-fA-F]{{64}}(?!{_ASCII})")),
    ("package_sha_label", re.compile(r"パッケージ\s*SHA")),
    ("sha256_label", re.compile(r"SHA\s*-?\s*256", re.IGNORECASE)),
    ("verification_pass", re.compile(r"検証\s*PASS")),
    ("event_key", re.compile(r"event_key", re.IGNORECASE)),
    ("acceptance", re.compile(rf"(?<!{_ASCII})acceptance(?!{_ASCII})", re.IGNORECASE)),
    ("artifact", re.compile(rf"(?<!{_ASCII})artifacts?(?!{_ASCII})", re.IGNORECASE)),
    ("evidence", re.compile(rf"(?<!{_ASCII})evidence(?!{_ASCII})", re.IGNORECASE)),
    # Uppercase only. Lowercase "pass"/"fail" are ordinary English words a buyer
    # might legitimately use; the internal tokens are the shouted ones.
    ("pass_token", re.compile(rf"(?<!{_ASCII})PASS(?!{_ASCII})")),
    ("fail_token", re.compile(rf"(?<!{_ASCII})FAIL(?!{_ASCII})")),
    ("local_path", re.compile(r"(/" + r"Users/|~/gig/)")),
)


def check_style(text: str) -> list[str]:
    """Internal tokens that must never reach a customer. Empty list = clean.

    Deliberately narrow. This is a fail-closed gate in front of a real send, so
    every rule here has to be one that cannot be wrong about ordinary Japanese
    customer prose -- a false positive silently blocks a paid delivery.
    """
    body = str(text or "")
    if not body:
        return []
    return [code for code, pattern in _CHECKS if pattern.search(body)]


def normalize_for_match(text: str) -> str:
    """Drop whitespace entirely, so our own message is recognisable after render.

    Deletes rather than collapses. Collapsing to a single space assumes the DOM
    only ever reflows whitespace we ourselves sent, and that assumption is
    already known to be false here: coconala_paid_progress_browser._normalized_text
    deletes all whitespace and says why -- "DOM innerText injects arbitrary
    whitespace/newlines; whitespace carries no meaning for matching Japanese
    text, so drop it entirely." That is a measurement of this exact DOM, and a
    whitespace character injected where we sent none would break a prefix match
    and fail a delivery that in fact succeeded.
    """
    return re.sub(r"\s+", "", str(text or ""))
