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

## 3. 部品在庫の詳細実測（clip-probe 第2報、file path 付き）

### そのまま使える
| 部品 | 場所 |
|---|---|
| ナレーション+b-roll から 1080x1920 動画組立 | `~/anicca/skills/faceless-money-factory/scripts/assemble.sh:13-47`、caption burn `scripts/burn-captions.sh:10-59` |
| 投稿前品質 gate（9:16/audio/8-90s/nonblack/2.5Mbps） | `~/anicca/skills/earn/clip/scripts/verify_clip.sh:8-15,25-80` |
| IG Reel upload + 公開確認 poster | `~/anicca/skills/earn/clip/scripts/instagrapi_post.py:330-380`、3分岐+ledger `run.sh:161-175,189-249` |
| views/likes/comments 計測 + self-improve summary | `~/anicca/skills/earn/video/selfimprove.py:78-125`、metric reader `metrics.py:50-81` |
| atomic state + backup restore | `~/anicca/skills/earn/video/state_io.py:20-54` |
| Capafy public URL（agent_id で構成、redirect 実証） | `docs/superpowers/evidence/L2-capafy.md:17`、online(status=4) ledger 例 `capafy-autopublish/state/published.jsonl:14-20` |

### 薄い adapter で使える
- closed marketing loop 骨格（LEARN→AFF-FIND→PRODUCE→POST→BIO→MEASURE→REFLECT）: `~/anicca/skills/earn/clip/clip_pass.sh:53-95`（account/niche が @aiclipsvault 固定 → Capafy 設定 adapter 要）
- content adapter: faceless factory は finance 固定 topic（`faceless-money-factory/SKILL.md:13-24`、`scripts/run-daily.sh:24-38`）→「online Capafy listing 1件選択 → hook/problem/demo/CTA 生成」に差替え
- instance 分離は ANICCA_INSTANCE で既に可能: `~/anicca/skills/earn/clip/_instance_paths.sh:10-21`
- daily gate state-machine: `~/anicca/skills/earn/video/decide.py:33-46`
- scheduling 実例: clip loop 6h 間隔 `ai.anicca.clip-loop-aiclipsvault.plist:7-22`、capafy daily 08:10 `ai.anicca.capafy-loop-daily.plist:4-9` → marketing 用は別 launchd job

### 新規必須
1. **comment poster**（既存 IG poster に comment API 呼出ゼロ: `instagrapi_post.py:362-380`）— media_comment、dedup、retry/ledger
2. comment link は clickable 保証不能。repo 内証拠は caption について「BIO だけ clickable」（`earn/clip/producer.sh:121-126`）で comment は未検証だが、外部ソース（inro.social、§1）が「captions and comments show as plain text」を裏取り → bio 主導線に切替
3. Capafy promotion selector: remote status=4 確認 + agent_id rotation/dedup（published.jsonl は mixed status: `capafy-autopublish/state/published.jsonl:1-27`）
4. post→comment を 1 transaction で管理する state/ledger（reconcile）
5. Capafy conversion attribution（post_url↔agent_id↔revenue join。既存 selfimprove に無し: `selfimprove.py:103-125`）
6. IG 以外の platform poster は新規

### 実稼働観測（2026-07-17）
- `ai.anicca.clip-loop-aiclipsvault` = loaded、6h、last exit 0、07-17 も full pass ログあり（`~/.openclaw/logs/clip-loop-aiclipsvault.err.log:89-127`）。ただし run.sh stdout 破棄設計のためログ単独では投稿成功を証明しない
- 実投稿 ledger に published Reel URL 多数: `~/.openclaw/state/clip-earn-ledger.jsonl:6-112`
- `ai.anicca.capafy-loop-daily` = loaded、08:10、runs=2 exit 0。実ログ `~/.openclaw/skills/capafy-autopublish/state/daily_loop.log`（mtime 07-17 20:10）
- **Capafy 売上 = 0。bottleneck = discoverability/quality**: `~/anicca/skills/self/capafy-loop/state/STATE.md:5-10`

## 3b. loop 稼働実態の全数調査（clip-probe 第3報）

| loop | コード | OS 稼働 | self-improve |
|---|---|---|---|
| clip (aiclipsvault) | 完動: LEARN→AFF-FIND→producer→post→bio→MEASURE→REFLECT（`clip_pass.sh:53-95`） | **稼働中だが実投稿停滞**（launchd 6h、runs=4 exit=0。cadence stamp 07-14、ledger 最終更新 07-12 = 直近 pass は新規投稿を生んでいない） | あり（3x own avg gate、imitate/optimize） |
| video (earn/video) | 完成（`decide.py:23-46`、`run.sh:55-265`、metrics 実読 `metrics.py:50-81`） | **supervisor 無し**（tmux/healthcheck 現存せず） | あり（metrics summary を Agent が読み script 改善） |
| faceless-money-factory | 生成のみ。**投稿ブランチは echo のみで未実装**（`run-daily.sh:51-52`） | draft email のみ | topic 重複回避のみ、views feedback 無し |
| affiliate slideshow | scripts のみ、orchestration/launchd 無し | 無し | 'amplify winners' は prose のみ未実装 |
| mau-tiktok | poster は YouTube-only（`post-to-postiz.js:252-266`）。SKILL の 3 platform/12post 記述は乖離 | cron enabled=false + 参照 script 不存在 | 空 |
| marketing-self-improve | record→measure→growth matrix→advisory JSON（`earn/marketing-self-improve/run.sh:12-74`… 実装あり） | cron 未登録 | advisory のみ、自動 action 無し |
| capafy daily | `ai.anicca.capafy-loop-daily.plist` 08:10 | **稼働中**（runs=2 exit=0） | 売上$0、discoverability bottleneck |

- credential 参照パス（値は不可侵）: `~/.cloak/ig-<handle>.json`、`~/.cloak/instagrapi-<handle>.json`、`~/.cloak/clip-accounts*.json`、`~/.openclaw/.env`、profile `~/.cloak/profiles/clip-en`
- **⚠ 要対処: `~/.openclaw/skills/reelfarm/SKILL.md:554-559,609-614` に hardcoded key 存在。rotate + file から除去が必要（別タスク）**
- 確定した欠如: active marketing cron 無し / Mau runner 不存在 / video healthcheck service 無し
- scheduling 追補: gateway 稼働中（PID603、314 jobs、store `~/.openclaw/cron/jobs.json`）。既存 X marketing job `anicca-x-marketing-daily-info`（08:20 JST）は **disabled**（`jobs.json:1350-1375`、skill = `~/.openclaw/skills/anicca-x-marketing-skill/SKILL.md`）。video state は warmup_day7 で last_post_date 無し、直近 audit 全て failed/skipped（`~/.cloak/earn-video-money_blueprintdaily.json`）

## 4. 未確認（次の実測対象）
- IG first comment vs bio の CTR 実測比較（未確認のまま。bio 採用の根拠は「comment がクリック不可」という仕様事実）
- TikTok 新アカは 1,000 followers 未満で Website 欄が使えない → Business Account 登録で回避できるかは account 作成時に実測
- Capafy 側のアフィリエイト/紹介 URL パラメータ仕様
