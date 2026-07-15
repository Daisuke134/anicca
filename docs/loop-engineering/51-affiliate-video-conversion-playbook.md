# 51 — 短尺動画 × Affiliate のコンバージョン実戦略（clip loop 自己改善の燃料）

関連: [[49-affiliate-money-playbook]]（offer 選定の基本）／ この 51 は「短尺動画で実際に売上に変える動線・CTA・metric」に特化。
用途: clip_pass.sh の LEARN / AFF-FIND / REFLECT に組み込む affiliate 特有の self-improve lever。
出典方式: 各 finding に実在ソース1引用。数字は引用元の主張であり我々の実測ではない（検証は自 loop の $/post で行う）。

## 主要 findings（7点）

1. **「link in bio」単体は CVR 低い（1-3%）。keyword-triggered comment → DM automation が 5-15% で圧倒。**
   Amy Porterfield は comment-to-DM 切替で登録率 85%（従来 landing 30-40%）、DM の CTR 28%（email 2-3%）。
   — Manychat: Amy Porterfield success story (manychat.com/blog/success-stories/amy-porterfield/)

2. **link-in-bio ツール間でも差: Stan Store 3.1% > Beacons 2.7% > Linktree 2.3%（2026）。CTA 文言 "Visit"→"Shop Now" で CTR +15-30%。micro-influencer(1-10万) 4.2% 変換 vs mega(100万+) 2.1%。**
   — usearticle.com TikTok Affiliate Marketing 2026 Guide (usearticle.com/affiliate-marketing-on/tiktok)

3. **EPC 基準は commission% でなく「$1 超」。finance/AI-SaaS/investment/business 系は RPM $15-35 で、同じ 10万 views でも他 niche 比 5倍稼ぐ。**
   — nichecalculators.app affiliate metrics guide ／ kineclip.com faceless YouTube 2026

4. **CTR 単体を追う設計は罠。高 CTR でも質の低いトラフィックは EPC が低い。100k views reel でも購買意欲のない層なら $0 の実例。**
   — affiliateguru.net EPC guide ／ medium write-a-catalyst「The Truth About Monetizing Faceless Content 2026」

5. **無断 clip は著作権侵害でアカウント消滅リスク。「30秒ルール」は都市伝説（存在しない）。commentary・facecam・stock 映像挿入等の transformative 要素の付加が唯一の緩和策。**
   — legitpodcastpro.captivate.fm copyright/fair-use guide

6. **faceless affiliate reels の現実的収益は月 $200-5000（$10-20k 超は少数）。finance 系リード単価 $10-200/lead。follower 数より monetize 手法選択が支配的。**
   — brandid.app faceless affiliate marketing 2026

7. **Digistore24 = 15-90% commission・8500 offer・44 niche。ClickBank = 1-75%（一部90%）。Digistore24 自身が短尺×zero-cost organic 向けガイドを出している。**
   — digistore24.com blog
   ※ Hormozi 系クリッパー分配の具体 EPC 数値は今回のソースからは未確認（要追加調査）。

## clip_pass.sh への反映 TODO（実物確認済み）

| step | 現状 | 足す lever |
|---|---|---|
| LEARN(35行) | affiliate 軸が皆無 | winner reel の CTA 配置（動画中盤/最後/caption/pinned comment）、"link in bio" 型か "comment for link"(keyword→DM) 型かの分類、link-in-bio ツール種別と CTA 文言を観察軸に |
| AFF-FIND(39行) | commission% のみで選定 | **EPC > commission%** を prompt に明記、offer.json に `epc_estimate` field 追加、finance/AI-SaaS/investment 等の高 RPM niche を優先明示（[[49-affiliate-money-playbook]]の EPC ルールと統一） |
| REFLECT(54行) | views/likes のみ、dollar metric 皆無 | **revenue_per_post を phase 判定に追加**（= Task #8 MEASURE→$）。「views 伸びても $0」検知時は CTA 形式そのものを変えるレバー（link-in-bio ⇄ comment合言葉→固定コメントに link の A/B）を次パスで試す分岐 |

**新レバー候補**: comment-to-DM 自動化（Instagram DM CTR 28% vs link-in-bio 1-3%）は効果大だが実装難度高（instagrapi 経由 DM 自動応答）。まずは軽量版 = 「link in bio」vs「コメントで合言葉→固定コメントに link」の2パターンを LEARN/REFLECT で交互に A/B から着手。

**著作権ガード**: PRODUCE が生 clip をそのまま流すのは BAN リスク。transformative 要素（caption オーバーレイ・commentary・stock 挿入）を必須にする（既に 1080×1920 caption 付き生成しているので概ね該当だが、元素材の出所を offer/producer 側で明示管理）。
