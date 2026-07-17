# Capafy marketing — SNS 外部リンク導線 + clip engine 転用調査（2026-07-17）

目的: Capafy skill を毎日 1 post で宣伝し 10k MRR を狙う marketing loop の設計材料。
調査主体: link-probe（web 実測、crwl）+ clip-probe（repo 実測）。

## 1. リンク導線の結論（実測ソース付き）

**Dais 案「link in comment のみ、bio 不要」は IG/TikTok では不成立** — comment 内 URL はクリック不可（プレーンテキスト表示）。有効なのは X の self-reply のみ。

| Platform | リンク置ける場所 | クリック可能 | リーチ影響 | 勝ち手 |
|---|---|---|---|---|
| Instagram Reels | bio Links 欄 / Story Link Sticker / (caption・comment は文字列のみ) | bio・Story のみ | 「link in bio」表記のペナルティ無し（Mosseri: "it will not affect your reach one way or another"） | **link in bio** + Story Link Sticker |
| TikTok | Website 欄（1,000 followers or Registered Business Account 必要）/ caption・comment は文字列のみ | Website 欄のみ | comment URL のリーチ低下は未確認（そもそもクリック不可で導線にならない） | **link in bio** |
| X | 本文 / reply / Profile Website — 全てクリック可 | 全て可 | 本文リンクは激減: Buffer 18.8M posts 分析で link post engagement ≈0%（通常アカ）。Musk "put the link in the reply" | **本文 native + 最初の self-reply に URL** |

引用:
- Social Media Today — https://www.socialmediatoday.com/news/instagram-doesnt-penalize-posts-that-include-link-in-bio/753899/ — "link in bio…will not affect your reach"
- SMK — https://smk.co/instagram-confirms-link-in-bio-wont-hurt-reach/ — "Instagram does not allow clickable links in captions"
- inro — https://www.inro.social/blog/how-to-add-link-to-instagram-post — "URLs in captions (and comments) show as plain text"
- TikTok Help — https://support.tiktok.com/en/getting-started/setting-up-your-profile/linking-another-social-media-account — "add a link…if you have 1000 followers or more, or a Registered Business Account"
- Colorado State Univ — https://social.colostate.edu/best-practices/how-to-add-a-link-to-a-tiktok-post-and-why-its-not-like-other-platforms/ — "Captions and comments = no clickable links…Bio = 1 clickable link"
- Buffer — https://buffer.com/resources/links-on-x/ — "18.8 million posts…links really do hurt performance / Put links in replies instead"
- X Help — https://help.x.com/en/using-x/how-to-post-a-link — "All links…shortened using our t.co service"
- Mashable — https://mashable.com/article/elon-musk-links-x-twitter — Musk: "put the link in the reply"

### 運用形（毎日 1 post × skill 別アカウント）
1. IG/TikTok: Capafy URL を bio に固定。動画は音声+画面+caption の 3 箇所で「プロフィールのリンク」誘導。first comment に URL 置かない。
2. X: URL 無し native post + 投稿直後の self-reply に Capafy URL。Profile Website にも常設。
3. UTM を platform 別（instagram_bio / tiktok_bio / x_reply）に分け views→profile visits→clicks→purchase を計測。self-improve loop の入力にする。

## 2. clip engine 転用（実測、file path 付き）

| 部品 | 場所 |
|---|---|
| clip engine 本体（source→clip→caption→post→earn→daily loop） | `anicca-project/.claude/skills/earn-clip-rewards/SKILL.md:28-59` |
| verify fail-close | `earn-clip-rewards/scripts/daily.sh:53-69` |
| evidence ledger | `earn-clip-rewards/scripts/daily.sh:71-75` |
| 既存の実 marketing 実例（IG+Reddit 投稿 + marketing-actions ledger） | `profitable-claude/skills/life-manager/life-manager-daily.sh:13-24` |
| profitable-claude への clip 移設 plan（copy manifest/gaps） | `docs/earn/profitable-claude-clip-loop-migration-plan.md:16-37` |

- profitable-claude 本体に clip/video skill は未移設（`profitable-claude/skills/README.md:6-8` の canonical 7 skill に無し）。
- 転用可能: launchd orchestration / creative 生成 / verification gate / account-safe poster / evidence ledger / 週次 self-improve。
- 差替え: YouTube source・字幕・ClipAffiliates 部分 → Capafy listing の紹介 creative + CTA + marketplace conversion 計測。

## 3. 未確認（次の実測対象）
- IG first comment vs bio の CTR 実測比較（未確認のまま。bio 採用の根拠は「comment がクリック不可」という仕様事実）
- TikTok 新アカは 1,000 followers 未満で Website 欄が使えない → Business Account 登録で回避できるかは account 作成時に実測
- Capafy 側のアフィリエイト/紹介 URL パラメータ仕様
