"""Real `document.body.innerText` from coconala 募集 detail pages.

Provenance, so a later reader can re-derive rather than trust: these strings were
lifted verbatim out of this loop's own B2 agent stdout logs under
`~/gig/evidence/gig-pass-*/agent-B2/attempt-01.stdout.log`, which record the text of
pages the browser actually rendered while logged in. The literal `\\n` escapes in
those logs are restored to real newlines here, because
`cdp_nav_snapshot._load_opportunity_brief` returns real `innerText`.

Two shapes in this file are the whole reason the parser exists:

1. The 募集者情報 stat card is VALUE-ABOVE-LABEL. `発注実績` is the card's heading, not
   a labelled field, and the three numbers under it belong to the labels that FOLLOW
   them:

       発注実績        <- heading
       36              <- 発注件数
       発注件数
       57%             <- 発注率
       発注率
       100%            <- 取引完了率
       取引完了率
       認証状況        <- next section

   Reading label-then-value looks plausible and is silently wrong: it returns
   取引完了率 (100%) where 発注率 (57%) was asked for, which is the number the A5-③
   gate is thresholding on. The proof that value-above-label is the true shape is
   the tail: label-then-value would have to assign 取引完了率 the value 「認証状況」.
   Measured over the logs, both regexes match 163 times, so a wrong reading is not
   detectable by match counts -- only by this structure.

2. A brand-new client is NOT missing. Coconala prints `0 / 0% / 0%`. Absence of the
   whole card is a different animal: it belongs to the two-name (会社名 + 担当者名)
   client card, which is the 継続 side A3 already refuses.
"""

from __future__ import annotations


# 募集 91000062. Range budget, closed, nobody hired, brand-new client at 0%.
RANGE_BUDGET_NEW_CLIENT = """ ホーム
仕事を探す
単発の仕事を探す（すべて）
IT相談・システム開発
プログラミング・ソフト開発
自動化ツール作成
自動化ツール作成
プログラミング・ソフト開発
予算
1万円
〜
3万円
納品希望日
2026年8月22日
募集期限
募集終了 締切日 2026年8月7日 / 掲載日 2026年7月28日
応募状況
応募人数 26
契約人数 0
閲覧数 348
用途・種類
Webシステム開発・サイト構築
募集内容

【 募集詳細 】
自動化ツールのプログラミングをお願いします。
チケプラのサイトで自動購入botの開発をお願いしたいです。

添付ファイル
ー
参考URL
https://tixplus.jp/
求めるスキル
ー
特記事項
経験者優遇継続依頼ありスピード重視品質重視
応募者一覧
応募者
応募日時
Buno K
2026/07/28 15:52
阿修羅ワークス
2026/07/28 15:52
もっと見る
募集内容についての質問
質問と回答の履歴
質問はまだありません。不明なことがあれば質問してみましょう。
募集終了
ブックマーク
募集者情報
tyogvii
 5.0 （2）
発注実績
0
発注件数
0%
発注率
0%
取引完了率
認証状況
本人確認

機密保持契約(NDA)

この募集を通報する
この募集内容に似ている仕事
プログラミング・ソフト開発
マウス機能開発の企画・設計・試作を担当する方を募集します
予算
見積り希望
応募者数
16
募集期限
あと 3 日 （8月1日まで）
tkcmy
投稿日時：3日前
詳細を見る
"""


# 募集 91000060. Range budget, one contract, an experienced client whose 発注率 (37%)
# sits BELOW the threshold while its 取引完了率 (50%) sits above it -- the exact pair
# that makes a label-then-value parser pass a job the gate is supposed to refuse.
RANGE_BUDGET_ESTABLISHED_CLIENT = """ ホーム
仕事を探す
単発の仕事を探す（すべて）
Web制作・HP作成・EC構築
Webサイト修正・カスタマイズ
企業ホームページのUI/UX改善と機能改修ができる方を募集します
Webサイト修正・カスタマイズ
予算
8万円
〜
10万円
納品希望日
2026年8月31日
募集期限
募集終了 締切日 2026年7月30日 / 掲載日 2026年7月28日
応募状況
応募人数 44
契約人数 1
閲覧数 332
業種
その他
募集内容

## ホームページ見直し・改善をお手伝いいただける方を募集します

現在、当社ホームページの内容やデザインを見直したいと考えております。

添付ファイル
ー
求めるスキル
ー
応募者一覧
応募者
応募日時
Buno K
2026/07/28 13:33
もっと見る
募集内容についての質問
質問と回答の履歴
質問はまだありません。不明なことがあれば質問してみましょう。
募集終了
ブックマーク
募集者情報
trotter
 5.0 （31）
発注実績
10
発注件数
37%
発注率
50%
取引完了率
認証状況
本人確認

機密保持契約(NDA)

この募集を通報する
この募集内容に似ている仕事
Webサイト修正・カスタマイズ
サイトの不具合の修正
予算
3,000円
応募者数
21
募集期限
あと 11 日 （8月9日まで）
시마카제
投稿日時：2日前
詳細を見る
"""


# 募集 91000056. 見積り希望 (no number), open, a client well above the threshold.
QUOTE_REQUEST_HIGH_RATE_CLIENT = """ ホーム
仕事を探す
単発の仕事を探す（すべて）
集客・マーケティング相談
SEO対策・上位表示
AIツール活用系メディア向け｜レビュー記事制作のご依頼
SEO対策・上位表示
予算
見積り希望
納品希望日
2026年8月4日
募集期限
あと 6 日 と 23時間 締切日 2026年8月4日 / 掲載日 2026年7月28日
応募状況
応募人数 12
契約人数 0
閲覧数 96
募集内容

公式LINEの構築をお願いできる方を募集します。
連絡はすべてチャットで完結します。

添付ファイル
ー
求めるスキル
ー
応募者一覧
応募者
応募日時
貴重品
2026/07/28 13:37
もっと見る
募集内容についての質問
0 / 2000
公開質問を送る
質問と回答の履歴
質問はまだありません。不明なことがあれば質問してみましょう。
応募する
ブックマーク
募集者へ質問する
募集者情報
hondajimusho
 4.9 （202）
発注実績
162
発注件数
69%
発注率
77%
取引完了率
認証状況
本人確認

機密保持契約(NDA)

この募集を通報する
この募集内容に似ている仕事
似ている仕事はまだありません。
同じカテゴリからも探してみましょう。
"""


# 予算 5千円未満: an open upper bound with no stated floor.
UNDER_BUDGET_OPEN_LISTING = """ ホーム
仕事を探す
単発の仕事を探す（すべて）
ライティング・翻訳
記事作成・ブログ執筆
記事のリライトをお願いします
予算
5千円未満
納品希望日
2026年8月10日
募集期限
あと 12 日 締切日 2026年8月10日 / 掲載日 2026年7月29日
応募状況
応募人数 3
契約人数 0
閲覧数 41
募集内容

既存記事のリライトをチャットでお願いします。

応募者一覧
応募者
応募日時
募集内容についての質問
応募する
ブックマーク
募集者情報
orutorosu
 5.0 （8）
発注実績
4
発注件数
80%
発注率
100%
取引完了率
認証状況
本人確認

この募集を通報する
この募集内容に似ている仕事
ライティング・翻訳
別の仕事
予算
40万円
〜
50万円
応募者数
1
募集期限
あと 11 日 （8月9日まで）
"""


# 予算 3,000円: a single exact figure.
EXACT_BUDGET_LISTING = """ ホーム
仕事を探す
単発の仕事を探す（すべて）
Web制作・HP作成・EC構築
Webサイト修正・カスタマイズ
サイトの不具合の修正
予算
3,000円
納品希望日
2026年8月9日
募集期限
あと 11 日 締切日 2026年8月9日 / 掲載日 2026年7月29日
応募状況
応募人数 21
契約人数 0
閲覧数 155
募集内容

サイトの不具合をチャットで直していただきたいです。

応募者一覧
応募者
応募日時
募集内容についての質問
応募する
ブックマーク
募集者情報
시마카제
 5.0 （3）
発注実績
2
発注件数
50%
発注率
100%
取引完了率
認証状況
本人確認

この募集を通報する
この募集内容に似ている仕事
似ている仕事はまだありません。
"""


# The 継続 client card: two names, no 発注実績 stat block at all. This is the ONLY
# observed shape (34/310 complete cards in the logs) where 発注率 is genuinely absent,
# and it is the bucket A3 already refuses.
RETAINER_CLIENT_CARD_NO_STATS = """ ホーム
仕事を探す
継続的な仕事を探す
事務・カンタン作業
【長期・在宅】SNS投稿・更新サポートスタッフ募集
募集内容

連絡はココナラのチャット形式で、隙間時間に非同期で対応いただけます。

募集者情報

株式会社BESW

beswjinji
認証状況
本人確認
機密保持契約(NDA)
"""
