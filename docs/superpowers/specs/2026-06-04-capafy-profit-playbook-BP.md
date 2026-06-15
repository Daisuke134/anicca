# Capafy Profit Playbook — 実データBP（コピー元）

- **Date**: 2026-06-04
- **Source**: Capafy live marketplace API `POST /agent/agents/search` + `GET /agent/agent/agents/{id}`（capafy-user skill, token=keiodaisuke@gmail.com, developerVerified）
- **Method**: 36クエリ横断 → 重複排除 **232 unique agent** → `salesVolume × price` で収益proxyランキング
- **用途**: Task 2「Capafy Profit Playbook」スキルの中核 + 全publish(Task 3)の値付け根拠。**BP = コピー元。オリジナル禁止。**

---

## 0. 最重要の構造的発見（コピーすべき骨格）

| # | 発見 | 含意（我々の動き） |
|---|---|---|
| F1 | **収益TOP35は全て `subscription`（月/週/日）。232中 download=100本も存在するが収益上位にゼロ** | 売るなら **Run Online subscription（closed source・recurring）一択**。Download買い切りは「売れるが稼げない」 |
| F2 | 上位はほぼ **base LLM(Claude Sonnet/Opus)のみ・外部有料API無し**（画像系のみ openai=GPT Image） | **外部有料APIを避ける設計**にすればAPI代がほぼゼロ→subscription粗利が立つ。電話/重いAPIは売り物に不向き |
| F3 | 出力が必ず **手に取れる成果物**: HTML deck / PDF report / 文字起こしファイル / 画像7枚セット / resume評価表 / 台本 | 「アドバイス」でなく **ダウンロードできる完成物**を返すskillが勝つ |
| F4 | 命名は例外なく `成果/対象 — 制約付きベネフィット`（em-dash） | 全listing この型でclone |
| F5 | short descは `Use when …`（必要な瞬間を名指し）。detailed descは `タイトル→hero画像→What it does→出力例スクショ` | この構造をtemplate化 |
| F6 | **1スキルを複数プラットフォームにclone = N listing**（YouTube/TikTok/Reels/Facebook/Instagram transcript = 同publisher 5本） | 我々も「1コア×多面展開」で listing数を増やす |
| F7 | 価格は2階層: **B2B生産性=$19.99-24.99/月**（deck/research/resume/data分析）/ **コンテンツ量産=$1.99-7.99/日 or 週**（tiktok/social/動画/poster）+ Free Trial | 重い価値=月額、軽い量産=日/週額 |

mode分布: `subscription 120 / download 100 / hourly 12`（232 unique中）。

---

## 1. 最高収益スキル TOP25（実測 2026-06-04）

> rev$ = salesVolume × 1サイクル価格（subscriptionは累計購読者×サイクル単価のproxy。真のMRRはchurn不明だが順位は妥当）

| # | rev proxy | sold | price | title | カテゴリ |
|---|---|---|---|---|---|
| 1 | $675 | 27 | $24.99/mo | HTML slides — Brief In, Animated Magazine Deck Out | スライド |
| 2 | $525 | 21 | $24.99/mo | Slides maker — Turn Any Content Into a Styled Deck | スライド |
| 3 | $460 | 23 | $19.99/mo | Deep Research Pro | リサーチ |
| 4 | $460 | 23 | $19.99/mo | 10-Year HR's Resume Selecting — Land Right Hires | 採用/HR |
| 5 | $440 | 22 | $19.99/mo | YouTube Transcript: Skim Long Videos in Minutes | 文字起こし |
| 6 | $400 | 20 | $19.99/mo | Video to Text: TikTok, YouTube & Reels Transcript | 文字起こし |
| 7 | $383 | 64 | $5.99/wk | Amazon Listing Image Generator — 7-Slot Strategy | EC画像 |
| 8 | $377 | 29 | $12.99/wk | Stock Analysis: Markets, Crypto & Macro | 金融 |
| 9 | $370 | 53 | $6.99/wk | Commerce Video Ad Maker — Photos to Sales-Ready | EC動画 |
| 10 | $364 | 28 | $12.99/wk | AI Viral Video Pro (Seedance 2.0) | 動画 |
| 11 | $336 | 42 | $7.99/wk | Best Data analysis | データ分析 |
| 12 | $275 | 11 | $24.99/mo | Senior data analyst — expert-depth report | データ分析 |
| 13 | $260 | 13 | $19.99/mo | Facebook Video Transcript: Live & Reels to Text | 文字起こし |
| 14 | $240 | 40 | $5.99/hr | PPT Slide Professional | スライド |
| 15 | $195 | 13 | $14.99/wk | AI Ad Video Director — Viewers Stay and Act | 動画広告 |
| 16 | $192 | 32 | $5.99/day | AI Video Generator — Better Watching Completion | 動画 |
| 17 | $160 | 8 | $19.99/mo | SEO Audit — Find Every Issue + Fix It in One Pass | SEO |
| 18 | $140 | 7 | $19.99/mo | Instagram Transcript: Fast Reels & IGTV to Text | 文字起こし |
| 19 | $138 | 46 | $2.99/wk | AI Video Hook Optimizer — Rebuild First 3s | 動画 |
| 20 | $138 | 46 | $2.99/day | Viral Social Copy — Turn Topics into Viral Post | SNSコピー |
| 21 | $135 | 45 | $2.99/day | Resume Maker — Build a Job-Ready Resume | 履歴書 |
| 22 | $131 | 66 | $1.99/day | TikTok Video Script — Start With Stronger Hooks | 台本（最多販売66） |
| 23 | $130 | 13 | $9.99/mo | AI PDF Generator — Anything to PDF | 生産性 |
| 24 | $100 | 5 | $19.99/mo | AI Paper Humanizer — From AI Draft to Author Voice | 文章 |
| 25 | $96 | 16 | $5.99/wk | Humanizer: Smart Rewriting Across 8 Genres | 文章 |

---

## 2. TOP出品の中身（A04詳細・positioning学習）

| skill | runtime/model | est.分 | 外部API | short desc冒頭 | 学べる点 |
|---|---|---|---|---|---|
| HTML slides | claude / Sonnet 4.6 | 10 | なし | "Use when the deck is part of your brand expression…" | 単一HTMLファイル成果物。WebGL背景=見た目で差別化 |
| Deep Research Pro | claude / **Opus 4.6** | 10 | なし | "Use when the decision demands more than a chatbot summary — sourced, verified, auditable." | 文ごとcitation+HTML/PDF納品=「監査に耐える」訴求で$19.99/mo |
| HR Resume | claude / Sonnet 4.6 | 15 | なし | "Make your hiring decision in minutes when facing numbers of CV." | JDをsource of truthに証拠付き選考レポート=防御可能な意思決定 |
| YouTube Transcript | claude / Sonnet 4.6 | 5 | なし | "…for students turning lectures into notes, podcast listeners hunting a quote…" | ターゲット3種を名指し。verbatim+要約+DLファイル |
| Amazon Listing Image | claude / Sonnet 4.6 | 15 | **openai** (GPT Image 2) | "…full 7-slot Amazon listing image sequence built around buyer objections" | 「購買異議を潰す7枚」=戦略付き画像。外部API代は週$5.99で回収 |
| Stock Analysis | claude / Sonnet 4.6 | 4 | なし | "Markets do not move for one clean reason…force-field report" | 免責文明記で規制回避。$12.99/wk |

共通template: `# Title → hero画像 → ## What it does / Main Purpose → 出力例スクショ → (規制系は Disclaimer)`。

---

## 3. 我々の手札との対応（Task 3 即clone候補）

| Capafy勝ちパターン | Anicca保有スキル | 値付け（BP準拠） |
|---|---|---|
| スライド/deck ($24.99/mo) | `frontend-slides` / `pptx` / `canvas-design` | $19.99-24.99/mo subscription |
| Deep Research ($19.99/mo) | `deep-research` / `content-research-writer` / `market-research` | $19.99/mo subscription |
| 文字起こし×N platform | （新規・base LLM+字幕取得） | $19.99/mo ×プラットフォーム別listing |
| TikTok台本/SNSコピー ($1.99-2.99/day) | `content-creator` / `x-algorithm` / `tiktok-research` | $1.99-2.99/day + Free Trial |
| Humanizer ($5.99/wk) | `humanizer` / `humanizer-ja` / `humanizer_academic` | $5.99/wk（日本語版は競合無し=blue ocean） |
| 動画/avatar | monk-factory系 / `reelfarm` / `remotion` | 外部API重→慎重に。subscription化なら価格高め+message cap |
| Resume ($2.99/day) | （新規・base LLMのみ） | $2.99/day |
| EC画像 (openai, $5.99/wk) | `imagegen-frontend-*` / `ai-image-generation` | $5.99/wk |

**目玉**: 日本語Humanizer・日本語コンテンツ系は英語マーケットに競合が薄い=差別化余地。

---

## 4. Per-Skill 値付けルール v2（実データ反映・spec §4を上書き）

```
STEP 1 — 外部有料API依存を判定（F2が最重要）
  外部有料API無し（base LLMのみ）       → subscription（closed・recurring）★既定★
  画像生成API(openai等)を1-2回           → subscription、価格に+$2-3/週でAPI代回収
  電話/動画大量レンダ/長時間Live(重API)  → ①message cap付きsubscriptionで上限を切る
                                          ②それでも赤字なら Download/BYOK（最終手段・稼げない前提）

STEP 2 — 価格
  B2B生産性(deck/research/resume/data/SEO/金融) → $19.99-24.99/月
  コンテンツ量産(台本/SNS/poster/画像)          → $1.99-7.99/日 or 週
  必ず Free Trial を front door に付ける

STEP 3 — message cap（subscriptionの粗利防衛）
  cycleMaxMessageCount を設定し、1サイクルの実行回数=API代の上限を固定（Sandbox Fee = $0.07/日 確定込みで黒字設計）

STEP 4 — 命名/説明（F4/F5を機械適用）
  title  = `成果/対象 — 制約付きベネフィット`
  short  = `Use when <必要な瞬間>` + ターゲット名指し
  detail = `# Title → hero画像 → What it does → 出力例 → (規制系Disclaimer)`
```

**spec §4からの変更点**: 旧ルールは「high-cost→Download既定」。実データはDownloadが稼げないと示した→**既定をsubscriptionに反転**。high-costは「message capで上限を切ってsubscription維持」を第一に、Downloadは最終手段。

---

## 5. 経済前提（再掲・引用§3 of design spec）

Capafy 20%手数料 / 初回$0.99認証 / Subscriptionのみ Sandbox Fee **US$0.07/日（確定・publish web checkpoint実見）** 控除。
→ subscription価格は **message capで実行回数を固定**し、`(想定API代/回 × cap) + (sandbox $0.07×日数) ≤ cyclePrice × 0.8 / 2` を満たすこと（手残り≥API+sandboxの2倍）。

---

## 6. 初公開実績（2026-06-04・検証済）

| 項目 | 値 |
|---|---|
| Agent | `Japanese Humanizer — Sound Human, Not AI` |
| agent_id | 3332784488 |
| モード | Download 買い切り **$9.99** |
| カテゴリ | Writing |
| 状態 | **status=1 (under review) / auditStatus=1 (auto review)** ＝審査提出成立（platform API + web "Submitted for Review" 二重verify） |
| skill本体 | `~/.openclaw/skills/jp-humanizer-pro/`（オリジナル・逐語流用なし・bundle秘密ゼロ・CLAUDE.md/settings除外） |

**経緯の教訓（重要・次回以降のため）**:
- Capafy「Run on Capafy(サブスク)」= publisher(我々)のLLM鍵をvault hosting＝我々がAPI代負担。買い手が鍵を出せるのは Download のみ。
- 実コスト計算: Sonnet 4.6 = $3/M in・$15/M out。1 humanize ≈ 保守$0.12/回（agent runtime overhead込み）。**初期cap=40/週は power user 1人で赤字**→cap 8/週で 手残り$4.79 vs 総コスト$1.45(API$0.96+sandbox$0.49)＝**約3.3:1**(sandbox込)の黒字ライン。
- Anthropic口座が $0.01・auto-reload off → サブスク鍵hosting不可（要入金）。→ Dais判断で **Download（入金不要）に切替**して公開。
- サブスク再挑戦時は Anthropic入金 + cap 8/週 + 週$5.99 が黒字設計。
