# Reddit マーケティング BP（実検索・引用付き、2026-07-12）

## なぜ書いたか
Life Manager の Reddit 宣伝が「投稿できたように見えて実は誰にも見えていない」（shadow spam-filter、karma=1）状態だったため、自己流で直さず実際の BP を検索して採用する。

## 出典1: Sprout Social — Reddit Marketing
URL: https://sproutsocial.com/insights/reddit-marketing/

### 核心の引用（そのまま）
> **Follow the 90/10 rule:** Aim for 90% of the content you share to be educational, and 10% promotional.

> **Phase I:** ... You should start commenting or answering questions to build **Karma** (Reddit's proprietary user reputation score), **so long as you're not doing so to plug your product or service.**

> Our primary subreddits (6 total) are where we want to become known as valuable contributors. Our **secondary subreddits (7 total) are solely for Karma building** and monitoring industry conversations. ... **10-15 is the sweet spot**.

> **Relying on AI-generated responses sends another red flag** to users already skeptical of bot-driven posts on the network.

> **Astroturfing** (posting content that appears to be organic but ultimately is self-promotional content) **is also largely discouraged** across Reddit.

### 実例（引用）
> u/GrammarlyOfficial ... The account has earned **over 600 Karma in less than a year**.
> u/Grammarly_Support ... has made **over 1,200 contributions and racked up a 100 Karma score** in just one year.

## 出典2: Foundation Marketing — Reddit Marketing
URL: https://foundationinc.co/lab/reddit-marketing/

> **Focus on building "Karma."** As Reddit's measure of account trustworthiness, Karma operates on a "points" system, and it's tied to factors like consistent use, upvotes, and downvotes. Manage your karma points, and you control your brand's reputation and **even visibility**.

> **Avoid being overly promotional**. Maximize your reach by providing helpful, valuable posts and comments across multiple subreddits.

> **Timing is everything on Reddit.** Study each subreddit's peak activity times... **quality trumps quantity every time.**

## 出典3: Wikipedia — Reddit（old vs new の事実確認）
URL: https://en.wikipedia.org/wiki/Reddit

old.reddit.com と www.reddit.com は **同じ Reddit の別スキン**（2018年4月の redesign で新デザインが本体になり、旧デザインが old.reddit として残った）。同じ投稿は両方の URL で見える。**「old.reddit だから誰も見ない」は誤り** — 我々の投稿が見えなかった真因は URL ではなく **karma=1 のアカウントが shadow spam-filter されていた**こと。URL を new に変えても解決しない。

## 我々の現状（実測 2026-07-11〜12）
- account `anicca_sao`、**karma = 1**
- 過去1週間の全コメント（5件）が **logged-out では1件も見えない** = shadow-filtered
- つまり Reddit 経由の宣伝インプレッションは **実質ゼロ**（成功に見えて効果ゼロ）

## 採用する fix（BP そのまま、自己流にしない）
1. **90/10 ルールを loop に焼く**: 1日1パスのうち、宣伝は10回に1回まで。残り9回は「純粋に役立つコメント/回答」だけを投稿して karma を貯める（Sprout Phase I: "so long as you're not doing so to plug your product or service"）。
2. **karma gate**: karma が一定値（目安 50+、Grammarly の実績値 100 を参考）を超えるまで、宣伝コメントを一切投稿しない。それまでは karma 育成のみ。
3. **secondary subreddit を karma 育成専用に持つ**（Sprout: "secondary subreddits are solely for Karma building"）。primary（宣伝したい先）とは分ける。
4. **AI丸出しの文体を避ける**（Sprout: "AI-generated responses send a red flag"）。
5. **必ず logged-out 検証**を続ける（見えていなければ posted と数えない）。既存の verification ステップは維持。
6. Instagram は karma に依存しないので **並行して毎日投稿を継続**（Reddit の karma 育成中も宣伝チャネルを止めない）。

## Done 条件（このBPが効いたと言える基準）
- `anicca_sao` の karma が実測で上昇していく（Reddit プロフィールを logged-out で読んで確認）
- karma gate 通過後、宣伝コメントが **logged-out で実際に見える**（= shadow-filter を脱した）
- marketing-actions.jsonl に `action: "posted"`（`posted_but_not_publicly_visible` ではない）の Reddit 行が出る
