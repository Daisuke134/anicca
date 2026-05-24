---
name: anicca-comedy-factory
description: End-to-end comedy skill. Anicca が funny になる grand challenge. Ogiri AI で humor 学習 → daily skit (JP+EN) → Slack DM Dais → Dais ライブ演じる → TikTok @anicca.comedy → ライブショー {{profile.lateness.stakeholders.channel}} 自動応募/開催 → Stripe Checkout で ticket 販売. Theme=Impermanence is funny. Triggered by 9 cron grid (4 JST Ogiri, 7 JST skit, 月初 09 JST live discover, etc.). Single skill end-to-end for any AI entity.
metadata:
  tags: comedy, ogiri, impermanence, live-show, stripe, postiz, {{profile.lateness.stakeholders.channel}}-harness
  requires:
    bins: [bash, python3, jq, curl, claude, {{profile.lateness.stakeholders.channel}}-harness]
    env: [SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, POSTIZ_API_KEY, POSTIZ_TIKTOK_INTEGRATION_ID, GOG_ACCOUNT, GOG_KEYRING_PASSWORD]
---

# anicca-comedy-factory

Anicca が funny になる **grand challenge**。Ogiri AI (gyu-don/ogiri-ai) で humor 学習 → daily skit 脚本 (JP+EN) → Dais ライブ演じる → TikTok 投稿 → ライブショー応募/開催 → Stripe Checkout で ticket 販売 → **「AI comedian で生計立つ」end-to-end 証明**。

## YOUR ENTIRE TASK (cron に応じて 1 つ実行)

| cron | やる事 |
|----|----|
| `comedy-skit-deliver-daily` (7 JST) | Ogiri 10 + Skit JP + Skit EN を **お前自身が書く** → ファイル保存 → stdout 最終行で報告 (詳細: 下の "Skit deliver の手順") |
| `comedy-ogiri-practice-daily` (4 JST) | Ogiri 30 本を **お前自身が書く** → ファイル保存 → stdout 最終行で報告 (詳細: 下の "Ogiri practice の手順") |
| `comedy-live-discover-monthly` (月初 09 JST) | `bash ~/.openclaw/skills/anicca-comedy-factory/scripts/live-discover-monthly.sh` | Tokyo 週次 + SF/LA 月1 同日 alignment lock |
| `comedy-live-apply-event` (event) | `bash ~/.openclaw/skills/anicca-comedy-factory/scripts/live-apply-event.sh <city>` | open mic 自動応募 |
| `comedy-live-schedule-publish` (月 10 JST) | `bash ~/.openclaw/skills/anicca-comedy-factory/scripts/live-schedule-publish.sh` | aniccaai.com/comedy 更新 |
| `comedy-post-live-process` (event) | `bash ~/.openclaw/skills/anicca-comedy-factory/scripts/post-live-process.sh <recording>` | Remotion 編集 + Postiz TikTok |
| `comedy-tiktok-cross-post-daily` (16 JST) | `bash ~/.openclaw/skills/anicca-comedy-factory/scripts/tiktok-cross-post-daily.sh` | TikTok → IG/X cross-post |
| `comedy-ticket-fulfillment` (event) | `bash ~/.openclaw/skills/anicca-comedy-factory/scripts/ticket-fulfillment-event.sh` | Stripe webhook → ticket 配信 |
| `comedy-recruit-event` (Phase 3+) | `bash ~/.openclaw/skills/anicca-comedy-factory/scripts/recruit-comedian-event.sh` | クラウドワークス で共演者リクルート |

各 script は **完全自律**: stdout 最終行をそのまま Slack に流す。

## Theme

**Impermanence is funny.** 監督 persona。Flip videos: 「全ては変わる」と言って変わらない物 (slow change) or 超高速で変わる物を見せる → 諸行無常の funny ギャップ。JP + EN 両方 (Tokyo + SF + LA)。

## Ogiri AI (upstream skill, NOT embedded)

公式 skill `gyu-don/ogiri-ai` を直接呼ぶ。`npx skills add gyu-don/ogiri-ai -g` で install 済。

| 場所 | 用途 |
|------|----|
| `~/.agents/skills/ogiri-ai/SKILL.md` | 原本 (universal install) |
| `~/.openclaw/skills/ogiri-ai/SKILL.md` | symlink (OpenClaw / 俺が読む経路) |
| (削除済) `data/ogiri/ogiri-skill.md` | 旧 embedded copy。**もう使うな**。upstream が source of truth |

大喜利を書く時は **必ず** `~/.openclaw/skills/ogiri-ai/SKILL.md` を Read してその指示通りに従う。鉄則 (短く / 絵が浮かぶ / そう来たか)・クラスタ表 (C0〜C6)・内部思考プロセス・出力フォーマット (`【回答N】` 形式) は全部公式に従う。自前のローカル鉄則を書き換えない。

License: CC BY-NC-SA 4.0 (upstream)。

## 価格 + Trip alignment

| 都市 | チケット | 訪問頻度 |
|-----|--------|--------|
| Tokyo | $10 (¥1,500) | 週次 |
| SF | $20 | 月1 (AI meetup と同日異時刻) |
| LA | $15 | 月1 |

`data/trip-calendar.json` に Dais SF/LA 月1制約 hard-code → 月初 AI meetup 確定 → 同日 evening の open mic に応募 → 失敗時は meetup を別日に shift。

## Phase

| Phase | 期間 | 動作 |
|-------|----|----|
| 1 (5月-7月) | open mic 参加 | Anicca 検索+応募 → Dais 出演 → 録画 投稿 |
| 2 (8月-10月) | 自前ホスト | Anicca 会場予約 + Stripe Checkout で ticket 販売 |
| 3 (11月-) | 共演者リクルート | クラウドワークス で funny 役者を雇う |

## Ogiri practice の手順 (`comedy-ogiri-practice-daily`, 4 JST)

お前 (Anicca) が直接やる。外部 LLM API は絶対叩かない。お前自身がモデル。

1. `data/ogiri/prompts.json` を読んで `odai` を取る (固定: 「これは無常すぎる、と感じるものは?」)。
2. **`~/.openclaw/skills/ogiri-ai/SKILL.md` を Read して内化する** (upstream `gyu-don/ogiri-ai`、CC BY-NC-SA)。鉄則・クラスタ表・内部思考プロセス・出力フォーマット (`【回答N】`) は全部公式準拠。
3. 公式 SKILL.md の指示通り、固定 odai で **大喜利 30 本** を書く。
   - 公式出力は 5 本/バッチ → 30 本 = **6 バッチ実行**。各バッチで内部思考プロセス (連想 20+, 最初 10 個捨てる, 自己批判, 「そう来たか」チェック) を毎回やり直す。
   - クラスタ狙い: 全体として C5 (スラング+誇張) と C6 (シュール) を中心に分散。
4. 出力した 30 本 (6 バッチ × 5 = 30) を `answers` 配列 (改行 join した string でも JSON array でも可、既存 history 互換で) で `data/ogiri/history/<YYYY-MM-DD>.json` に `{date, odai, answers: [...30]}` で保存。
5. `data/ogiri/prompts.json` の `history` 配列に `{date, odai}` を append して書き戻す。
6. stdout 最終行: `✅ ogiri practice: 30 answers on "<odai>" → data/ogiri/history/<date>.json`
7. 失敗時の最終行: `❌ ogiri FAILED: <理由>`

## Skit deliver の手順 (`comedy-skit-deliver-daily`, 7 JST)

お前 (Anicca) が直接やる。外部 LLM API は絶対叩かない。

1. `data/ogiri/prompts.json` を読んで `odai` を取る (固定)。
2. **`~/.openclaw/skills/ogiri-ai/SKILL.md` を Read** (upstream `gyu-don/ogiri-ai`、CC BY-NC-SA)。鉄則 + クラスタ表 + 出力フォーマット遵守。
3. 公式 SKILL.md の指示通り大喜利を **10 本** 書く (calibration 用) = **2 バッチ × 5 本**。各バッチで内部思考プロセス完走。クラスタ C5/C6 中心。
4. その 10 本を「humor calibration」として参照しながら、**Skit JP 60 秒** を書く:
   - 僧侶 (お坊さん) persona
   - テーマ: Impermanence is funny
   - 「全ては変わる」と言いつつ変わらない物 (slow change) or 超高速で変わる物を出す → gap が funny の core
   - スタンドアップ形式、60 秒 (約 300 字)
5. 同じテーマ・persona で **Skit EN 60 秒** を書く (英語、約 150 words)。
6. ファイル保存:
   - `data/skit-scripts/<YYYY-MM-DD>-jp.json` に `{date, odai, ogiri: [...10], skit_jp: "..."}`
   - `data/skit-scripts/<YYYY-MM-DD>-en.json` に `{date, odai_en, skit_en: "..."}`
7. `data/ogiri/prompts.json` の `history` 配列に `{date, odai}` を append。
8. stdout 最終行: `✅ skit delivered: <date> | お題=「<odai>」 | ogiri=10 + skit JP/EN saved`
9. 失敗時: `❌ skit FAILED: <理由>`

### Step 6.5: フリップ画像 5 枚を焼く (本物のフリップ芸仕様)

`flip_jp` のテキスト脚本だけでは芸として使えない。**白い厚紙 + 手書き黒マジック** の PNG にする。

1. **`FLIP_DESIGN_RULES.md` を必ず Read** (`~/.openclaw/skills/anicca-comedy-factory/FLIP_DESIGN_RULES.md`)。お経の紙風 / 朱印 / 縦罫線 / 蓮 / 墓石絵 / 「↓ めくる」テロップ → 全部禁止。本物 IPPON は白紙手書き 1〜3 行のみ。
2. レンダラ: `python3 ~/.openclaw/skills/anicca-comedy-factory/scripts/flip/render-flips.py`。出力先は中の `OUT` を編集 (`~/Desktop/anicca-flip-<date>/` 推奨)、文言は `flip_slide(...)` の引数を `flip_jp` から writes-back する。
3. 構成 (5 枚):
   - `01_odai.png` — 黄色背景 + 黒太字でお題 + 「ANICCA GRAND PRIX」黒帯 (IPPON テロップ風)
   - `02_flip_xxx.png` 〜 `04_flip_xxx.png` — 白背景 + Klee One SemiBold で答え 1〜3 行。各行 ±3〜5° 斜め、左右オフセット ±20px。最後の 1 行だけ赤 #C72525 強調 OK
   - `05_shime.png` — 黒背景 + 黄色 Yuji Mai 巨大「南無」+ `@aniccaai`
4. フォント: `~/.openclaw/skills/anicca-comedy-factory/fonts/{KleeOne-SemiBold,YujiMai-Regular,ReggaeOne-Regular}.ttf` (Google Fonts、OFL)
5. 観察ソース: `~/anicca-project/flip-research/` (268 枚、IPPON 王道 + 永野 + バカリズム + コウメ太夫 等)
6. Slack #metrics に 5 枚アップロード (`files.upload_v2`)。stdout 最終行: `✅ flip images: 5 PNGs at <path>`

## Reporting

各 script は最終行で:

成功:
```
✅ <action>: <url or id>
```

失敗:
```
❌ <action> FAILED: <reason>
```

cron delivery が #metrics に流す。Slack tool は呼ばない。

## Timeout 回避

`comedy-skit-deliver-daily` は LLM 生成が長引くことがあるため、最終出力は短く保つ。冗長な説明や複数案の併記はしない。

## Files

```
skills/anicca-comedy-factory/
├── SKILL.md
├── crons.json                       # 9 cron grid
├── data/
│   ├── config.json
│   ├── ogiri/
│   │   └── prompts.json             # お題 stock + 既使用 flag
│   │                                # ※ 鉄則は ~/.openclaw/skills/ogiri-ai/SKILL.md (upstream) を参照
│   ├── ogiri/history/<date>.json    # 練習履歴 + Dais 評価
│   ├── skit-scripts/<date>-{jp,en}.json
│   ├── live-events/<city>-<date>.json
│   ├── trip-calendar.json
│   ├── tickets-sold.json
│   └── recruited-comedians.json     # Phase 3+
└── scripts/
    ├── lib/
    │   ├── slack_helper.py          # Slack post helper (tool)
    │   ├── tokyo-openmic.sh         # {{profile.lateness.stakeholders.channel}}-harness 応募
    │   ├── sf-openmic.sh            # lu.ma + sfstandup.com
    │   ├── lax-openmic.sh
    │   ├── stripe-checkout.sh
    │   ├── crowdworks-recruit.sh    # Phase 3+
    │   ├── remotion-edit.sh
    │   ├── postiz-tiktok.sh
    │   └── slack-dais.py
    ├── live-discover-monthly.sh
    ├── live-apply-event.sh
    ├── live-schedule-publish.sh
    ├── post-live-process.sh
    ├── tiktok-cross-post-daily.sh
    ├── ticket-fulfillment-event.sh
    ├── recruit-comedian-event.sh
    └── status.sh
```

(ogiri-practice-daily / skit-deliver-daily は Anicca が SKILL.md の指示で直接実行するため、Python script を廃止した。)

## End-to-end completion criteria (5-step workflow)

| Step | Status |
|------|--------|
| 1. 手動フル実行 | ✅ 2026-05-06 23:38 JST — Ogiri 10 + Skit JP/EN + Slack #metrics 投稿 (ts=1778078322.695029) |
| 2. skill 化 | ✅ initial commit (embedded ogiri rules) |
| 2b. ogiri-ai upstream 化 | ✅ 2026-05-14 — `npx skills add gyu-don/ogiri-ai -g` → `~/.openclaw/skills/ogiri-ai/SKILL.md` symlink。embedded `data/ogiri/ogiri-skill.md` 削除。SKILL.md は upstream を Read する手順に書き換え済 |
| 3. skill 経由再実行 | ⏳ TODO (next ogiri-practice / skit-deliver 走行で upstream SKILL.md 読み込みを実証) |
| 4. today cron で gateway 経由 | ⏳ TODO |
| 5. daily cron 13 個 register | ✅ registered (`~/.openclaw/cron/jobs.json` enabled:true)。実 produce 残り |
