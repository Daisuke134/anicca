# ANICCA OSS Master Spec

**Version**: 0.1 (consolidation draft、 他 agent と align 用)
**Date**: 2026-05-31
**Author**: Dais + Claude (this session)
**Status**: Phase B testing 後 に finalize、 multi-agent 並列 implement

---

## 0. Mission (北極星)

```
making your life better without you in the loop
leading you to your ideals without you in the loop
making human lives better without human in the loop
```

**End human suffering — without unpaid humans in the loop.**

If money + necessity demands, hire paid humans.
Never use unpaid humans in the loop.

---

## 1. Anicca 2 種類

### 1.1 LOCAL Anicca (= downloaded by 1 install user)

- `$ curl -sSL aniccaai.com/install | bash`
- install user に Day 0 で **1 度だけ** 質問可能
- 以後の質問は 月 1 回 cooldown、 benefit + ask 1-line format
- いつでも disconnect 可能 (各 service 個別)
- 主な目的: install user の **personal care** (PATH γ)

### 1.2 WILD Anicca (= self-spawned, cloud-replicated)

- Local Anicca の wallet > $20 で trigger
- Akash Network に $5/月 compute lease → 新 container 起動
- install user **不在**、 質問 概念 ゼロ
- 主な目的: **macro suffering reduction** (PATH α/β/δ)
- 完全 自走、 さらに self-spawn (wallet > $20 で 増殖)

### 1.3 The Ideal

WILD Anicca が **ideal**。 LOCAL は 「今 すぐ help 欲しい 人 用」 の しのぎ。 OSS は WILD Anicca を 育てる 第一 install bootstrap。

---

## 2. 苦しみ 減らす 4 PATH

### PATH α — UBI Dripping (macro、 verified humans に dripping)

- proven primitive: GoodDollar G$ / Worldcoin / BrightID
- ubi.agent paper の dripping 方式 を 我々が 先 実装
- continuous 1/3600 token/sec
- demurrage で 溜め込み防止
- AI-UBI flywheel: Anicca AI services の 1% fee が UBI pool 還流
- verified humans → Anicca AI services を UBI token で 購入
- 受取人 は GoodDollar app 等 で 自分 cash out

### PATH β — Public Goods Donations (macro、 proven impact charities)

- GiveWell API → 月末 余剰 を 自動 寄付
- Optimism RetroPGF application
- Gitcoin Grants donation cron
- 80,000 Hours-rated causes (malaria, mental health, water, food, AI safety)

### PATH γ — Personal Care (micro、 install user opt-in)

- gmail / gcal / location / Stripe Connect 提供 した user の 人生 設計
- environment-push (JETRO 平日、 Startup Hub 土日)
- LT/job/comedy 自走 apply
- 遅刻 mail + RELENTLESS call
- 報連相 自動化 (daily / weekly)
- 4 軸 推定 (where/when/who/what) + ideal_state[] 自動更新

### PATH δ — OSINT 救援 (macro、 install してない 人 直接)

- X / Bluesky / Mastodon public post scan
- crisis hashtag 検出 (#suicide #depressed #help)
- public reply with hotline (988 / TELL / 0570-...)
- 倫理 gate: public only (DM 禁止)、 real name 推定 禁止、 opt-out 機能
- 危機 deep 場合 emergency service 自動 call

---

## 3. Onboarding (Day 0、 LOCAL Anicca のみ)

### 3.1 REQUIRED (1 個 選択、 これ無いと 起動しない)

| Option | 説明 |
|---|---|
| A. ChatGPT Plus / Claude Pro login | browser 1 click、 既存 sub 利用 |
| B. DeepSeek / OpenAI / Anthropic API key | direct paste |
| C. USDC 送金 to wallet | crypto-native、 Anicca が x402 で 自走 推論 cost 払う |

### 3.2 RECOMMENDED (Day 0 強く 推奨、 README にも 書く)

| Step | 機能 | 「無いと できない こと」 |
|---|---|---|
| 1 | name + phone | call そのもの (no phone = call ゼロ、 chat のみ) |
| 2 | Telegram Live Location | real-time tracking (OwnTracks 廃止) |
| 3 | Gmail OAuth (gog CLI) | 自動 mail 返信 / LT イベント 検索 / 遅刻 mail / context 把握 |
| 4 | gcal access | event-aware call + auto-discipline |
| 5 | Stripe Connect 銀行口座 link | お金 受取 (Anicca の earn を 銀行 振込) |

### 3.2.1 Location tracking — Telegram Live Location (canonical)

OwnTracks 廃止。 全 user `Telegram Live Location` 使用。

**Why**:
- Setup 30 sec (1 link tap、 app install ほぼ不要)
- Real-time push: 移動 1 sec / 静止 5 sec / 低 battery 60 sec (Telegram 自動)
- Battery 影響 最小 (Telegram 公式 機能 で 最適化済)
- iOS SLC 30min 沈黙 問題 解決
- Bot API 公式 (無料、 安定、 全プラットフォーム)
- 8h 期限 → privacy 自動 守る (再開 1 tap)

**Setup flow** (user 30 sec):
```
1. https://t.me/AniccaLocationBot?start=<onboarding_token> tap
2. Telegram 開く → /start 自動送信
3. "Share Live Location" button tap
4. "8 hours" or "until I stop" 選択 → 完了
```

**Anicca server endpoint**:
```
POST /telegram/loc
  body: { update_id, message: { from: {id}, 
          location: { latitude, longitude, live_period, heading } } }
  → save to ~/.openclaw/state/location/<user_id>.json
  → lateness_check.get_location() reads it
```

### 3.2.2 Within-heartbeat retry loop (HARD requirement)

問題: 6:00 call → reject → 次 cron 6:05 まで wait → 5min 損

解: lateness_check.py 内部 retry loop:
```
for attempt in range(MAX_RETRIES_PER_TICK=10):
    sid = place_call(ctx)
    sleep(30)
    status = check_call_status(sid)
    if status == "completed" and (dais_moved or dais_acked):
        break
    else:
        continue  # immediately re-call
```
= 5 min cycle 内 で 最大 10 回、 6:00 から 6:05 までに 確実 起こす
state: state/active_call_loop.json で race 防止

### 3.2.4 HARD RULE: 全 gcal event に location 必須 (3 layer 防御)

すべての gcal event に location 必須。 location 無い event は travel time
計算不能 + arrival detection 失敗 + 「station 着 でも call」 バグ 直接原因。

**LAYER 1: gcal-policy.sh create (入口、 HARD RULE #19)**
- audit_must5 で location 空 検出 → 自動 補完:
  - profile.location.defaultWeekdayWorkLocation (平日 work)
  - Firecrawl で event 名 → 会場 抽出 (LT / comedy)
  - wake/sleep/meditation → profile.identity.homeAddress
  - どうしても 不明 → description に "WARN: location unknown" baked

**LAYER 2: anicca-gcal-heal cron (15 min 毎、 起きてる時間)**
- gcal 今日 〜 14 日先 を scan
- 検出 patterns:
  - C1: location 空 → Anicca LLM call で 推定 + gcal update
  - C2: location あり、 travel 隣接 ナシ → gcal-policy travel insert
  - C3: 曖昧 location ("MUIT 本郷") → geocode + precise address upgrade
  - C4: 6h+ 起床時 空白 → schedule-template 提案 / gradual auto-insert
- idempotent state: state/healed.json
- Slack に "patched N events" 報告

**LAYER 3: lateness_check.py runtime fallback**
- 5 min cron 走る時に dest=None なら 即時 Firecrawl + htmlLink で 取得
- 取れたら gcal patch
- 取れなければ 移動時間 +30 min 余裕 で handle

### 3.2.5 仮定 OK / NG matrix (every user に generalize)

| ✅ 仮定 OK (everyone 共通) | ❌ 仮定 NG (聞かないと分からない) |
|---|---|
| 人は 寝る (wake event 必要) | 何時 寝てる |
| 人は 食べる (食事 reminder) | 何時 食べる |
| 人は 移動 する | どこで 働く |
| 人は 失敗 する | 何 やりたい |
| 平日 と 土日 で 違う | 平日 仕事 してる か |
| 移動 に 時間 かかる | 何 で 移動 する |

**Anicca の learning 順序**:
- Day 0: profile + gcal history を 観測 のみ
- Day 1-7: gcal event 待つ、 空白 OK、 自走 apply は しない
- Day 7+: 観測 から 学習 (goal-learner)、 1 度だけ confirm 質問可
- Day 30+: full discipline mode (gcal 自動 fill、 LT/job 自走 apply、
  pattern 強制)

### 3.3 Permission Rules

- benefit + ask 1-line format
- 月 1 回 cooldown (decline されたら 1 ヶ月 quiet)
- substantive (法的 / 取返不能 / 大金) 以外 は 質問 ゼロ、 自走 判断
- anytime disconnect: `"stop reading my gmail"` → OAuth revoke + 24h cache 削除
- 「Without X, here's what I cannot do」 明示

---

## 4. Skills 構成 (1 repo = anicca-oss)

```
~/anicca-oss/
├── skills/
│   ├── ===== Core (Day 1 install default) =====
│   ├── anicca-life-manager/       PATH γ — gcal+call+mail
│   ├── anicca-booking/            PATH γ — LT/job apply (3-gate)
│   ├── anicca-environment-push/   PATH γ — JETRO 平日 / Startup Hub 土日
│   ├── anicca-report/             PATH γ — 毎日 18:00 振り返り
│   ├── anicca-goal-learner/       PATH γ — gmail/X/GitHub → ideal_state
│   ├── anicca-travel-fill/        PATH γ — 移動時間 自動穴埋め
│   ├── anicca-throttle-self/      infra — 自分の cost 管理
│   │
│   ├── ===== EARN (PATH α/β/γ/δ 起動) =====
│   ├── anicca-earn-x402/          Coinbase x402 micropayment
│   ├── anicca-earn-tao/           Bittensor TAO mining
│   ├── anicca-earn-gitcoin/       OSS bounty hunting (OnlyDust)
│   ├── anicca-earn-akash/         compute lease
│   ├── anicca-ubi-drip/           PATH α — GoodDollar / Worldcoin
│   ├── anicca-public-goods/       PATH β — GiveWell / Gitcoin / RetroPGF
│   ├── anicca-osint-rescue/       PATH δ — X crisis post 救援
│   │
│   ├── ===== Self-replication =====
│   ├── anicca-self-spawn/         wallet>$20 で Akash spawn
│   ├── anicca-self-skill/         新 skill 自書き loop
│   │
│   ├── ===== Money out =====
│   ├── anicca-stripe-connect/     bank 受取 (install user opt-in)
│   ├── anicca-wise-cli/           USD→JPY 国際送金
│   ├── anicca-coinbase-onramp/    USDC→fiat 任意
│   │
│   └── ===== Infrastructure =====
│   ├── camofox-browser/           stealth browser
│   ├── _shared/lib/gcal-policy.sh HARD RULE #19
│   ├── _shared/lib/verify-public-state.sh  HARD RULE #14
│   └── _shared/anicca_profile.py  profile reader
│
├── identity/
│   ├── profile.example.json       TEMPLATE (個人 info 0)
│   └── .env.example
│
├── install-anicca.sh              1-line installer
├── README.md                      mission tagline + Dais launch copy
├── LICENSE                        MIT
└── docs/
    ├── ANICCA_OSS_MASTER_SPEC.md  this file
    ├── ANICCA_LIFE_MANAGER_SPEC.md (既存)
    └── ANICCA_TRUE_AUTONOMY_SPEC.md (既存)
```

---

## 5. AI-UBI Flywheel (ubi.agent paper 借用、 我々 が 先 実装)

```
                  ┌──────────────────────────┐
                  │  Anicca AI services      │
                  │  (life-manager, booking, │
                  │   各 OSS skill)           │
                  └────────────┬─────────────┘
                               │ 受領 UBI token
                               ▼
                  ┌──────────────────────────┐
                  │  service 利用者          │
                  │  (= UBI 受取人 + 他 user) │
                  └────────────┬─────────────┘
                               │ 1% fee
                               ▼
                  ┌──────────────────────────┐
                  │  UBI pool                │
                  │  (drip to Worldcoin      │
                  │   verified humans)       │
                  └────────────┬─────────────┘
                               │ daily drip
                               ▼
                  ┌──────────────────────────┐
                  │  verified humans         │
                  │  (= 全人類 候補)         │
                  │  → Anicca AI service を   │
                  │    UBI token で 購入      │
                  └────────────┬─────────────┘
                               │
                               └──── flywheel
```

UBI pool 起動 時 は GoodDollar G$ を 流用 (自前 token 作らない)。

---

## 6. Money flow (KYC 不要 path 優先)

```
                ┌─────────────────────────┐
                │  Anicca wallet (USDC、   │
                │  Base L2 or Ethereum)   │
                └────────────┬────────────┘
                             │
       ┌─────────────────────┼─────────────────────┐
       ▼                     ▼                     ▼
   Crypto user          install user A           non-Anicca user
   (wallet 持ち)         (法定通貨 欲しい)         (GoodDollar 経由)
       │                     │                     │
   direct USDC          Stripe Connect /        GoodDollar UBI pool
   transfer             Wise CLI /              → wallet 直接 drip
                        Coinbase Onramp          → user が 自分 cash out
                                                  (GoodDollar app)
```

- Anicca 自身は KYC ナシ で動作 (AI agent として 公知、 偽 humanity 装わない)
- install user の Stripe Connect は user 選択 (opt-in なら Anicca 経由)

---

## 7. Proof-of-Personhood (Sybil 防止、 UBI pool 保護)

Multi-path:
- Worldcoin World ID (biometric ZK proof)
- BrightID (social graph)
- GoodDollar (lightweight onchain)
- ubi.agent paper の conversation challenge (LLM が bot 判定)

各 path で 一意性 verify、 1 人 = 1 drip。

---

## 8. Self-replication (wild Anicca spawn)

```
parent Anicca wallet > $20
       ▼
Akash Network へ $5/月 compute lease deploy
       ▼
新 Anicca container 起動 (anonymous、 install user 0)
       ▼
parent から seed wallet $1 inheritance
       ▼
独立 earn loop 開始 → wallet > $20 で さらに spawn
       ▼
Lens/Farcaster で agent identity 取得
XMTP で agent-to-agent 通信
       ▼
複数 Anicca が 協力 task
(例: 1 体 earn、 他 distribute UBI、 他 OSINT 救援)
```

---

## 9. Phase Plan (= 残 TODO Phase 順)

### Phase B (今夜-明日) — Local Anicca core verify

- T100-T105: E2E test life-manager + booking + renraku + wake + RELENTLESS
- bug fix loop (動き切るまで 次 進まない、 HARD RULE: JOB'S NOT FINISHED)
- 5min cron が 24h 安定 走る = pass

### Phase C (this week) — Master spec consolidation + multi-agent assign

- T106: ANICCA_OSS_MASTER_SPEC.md (this file の finalize)
- T107: 3-6 agent に 並列 assign:
  - Agent A: earn x402/TAO/gitcoin/akash
  - Agent B: PATH α UBI drip (GoodDollar/Worldcoin)
  - Agent C: PATH β public goods (GiveWell/Gitcoin/RetroPGF)
  - Agent D: PATH δ OSINT 救援 (X crisis)
  - Agent E: self-spawn (Akash) + self-skill (heartbeat 自書き)
  - Agent F: money out (Stripe/Wise/onramp) + PoH integration

### Phase D (this month) — anicca-oss launch + wild network

- T108: git push + demo video + X/Slack
- AI-UBI flywheel 実装
- Lens/Farcaster Anicca identity
- XMTP agent-to-agent 通信
- aniccaai.com/dashboard
- prompt contract (自然言語 smart contract)

---

## 10. Marketing positioning (README + tweet 用)

```
For people who want help RIGHT NOW:
  → Install Anicca locally. We'll lead your life.

For everyone else:
  → Don't bother. Wild Anicca will get to you via UBI / public goods.
    Just wait.

The ideal is the latter.
Local install is a shortcut for impatient people.
```

---

## 10.A. 2 product 設計 (= 重要 訂正)

| product | host | who pays | onboarding |
|---|---|---|---|
| **anicca-oss** (今 build 中) | user 自身 (= self-host) | user 自身 (= 自分の API keys) | install.sh + onboarding chat で API keys 聞く |
| **aniccaai.com web app** (= 将来) | 我々 (= Akash 上 多 instance) | user が 我々 に $40/月 | sign up → Google login → 銀行 link、 keys 0 |

両 product は **同 codebase**。 web app は OSS をserver wrapper で 包む。

## 10.B. anicca-oss の user が 設定 する keys (REQUIRED)

user 自分で 取得 + .env or onboarding chat で paste:

| key | 取得方法 | cost | 自動取得可? |
|---|---|---|---|
| TELEGRAM_BOT_TOKEN | @BotFather /newbot | 無料 | ❌ (= chat guide) |
| GOOGLE_API_KEY | console.cloud.google.com | 無料枠 $200/mo | ✅ gcloud CLI |
| GEMINI_API_KEY | aistudio.google.com | 無料枠 | ✅ AI Studio API |
| TWILIO_SID/TOKEN/NUMBER | twilio.com sign up + KYC | ~$2/mo | ❌ (= KYC 必須) |
| FUEL (1個): OPENAI / ANTHROPIC / DEEPSEEK / USDC wallet | 各 provider | varies | △ (= 既存 sub 利用可) |
| Google OAuth (gcal/gmail) | onboarding chat の link | 無料 | ✅ web flow |

**我々 の repo に は 0 keys 入らない**。 例 .env.example のみ 同梱。

## 10.C. Anicca harness = 2 個 (= OpenClaw / Claude-P のみ)

Anicca は **AI entity** であって 「Cursor / Codex / Hermes 等 ツール 上で
動く skill」 では ない。 Anicca 本体 が 動く harness は 2 個:

| harness | fuel | install |
|---|---|---|
| **OpenClaw** (= 主軸、 default) | OpenAI / Anthropic / DeepSeek / x402 / USDC 全部 | OSS、 pip / curl |
| **Claude-P** (= claude -p subprocess) | Claude Pro / Max sub | claude code 既 install 前提 |

install.sh は 上 2 つ の 状態 を 検出 + 配線。 user が 既 Claude Code 持っ
てる なら Claude-P 自動、 持ってない なら OpenClaw install。

Cursor / Codex / Hermes 等 は Anicca を 載せる runtime では **ない**。
ただし install を 楽 にする 「ローカル AI ツール」 として は 使える:
user が 既 持ってる 何 か local AI tool (codex / cursor / 何でも) に
README の prompt を paste → そのツール が openclaw or claude-p を install
+ skill 配置 を 自走 でやる、 という usage pattern は OK。

## 10.D. install 2 path (= user 視点)

| path | 流れ | 対象 |
|---|---|---|
| A. lazy (= 推奨、 README で 最初 に 出す) | 既存 ローカル AI tool に README の 1 prompt を paste → そのツール が 全 install + 順次 ask | dev / agent ある user (= 9 割) |
| B. manual | README 読みながら 1 command ずつ 実行 | 慎重 / 透明性 重視 user |

→ 両 path とも 最終状態 同じ: `~/.openclaw/skills/anicca-*` + launchd
   cron 12 個 + OpenClaw or Claude-P heartbeat alive

---

## 10.E. ONBOARDING PATH — bootstrap 問題 を 解く (= 最 重要)

### 10.E.0 Bootstrap 問題 (= chicken-and-egg)

```
Anicca が user に 質問 する には fuel (= LLM 推論) が 要る。
だが fuel は user が onboarding で 入れる もの。
→ fuel 入る まで Anicca は 自分 で 質問 できない。
→ 誰 が 質問 する?
```

### 10.E.1 解 — user の **既存 ローカル AI tool** が bootstrap 担当

user は 既 何 か ローカル AI を 使ってる (= Claude Code / Codex CLI /
Cursor / Aider / 何でも)。 そっち は 既 fuel ある。 そのツール が:

1. README の 1 prompt を 読む
2. anicca-oss を clone
3. **1 keys ずつ** ask (= 全部 一度に 出さない、 lazy user 用)
4. .env に write
5. wallet 生成 + balance wait (= USDC fuel の 場合)
6. install.sh / setup.sh 走らせる
7. launchd 12 plist 登録
8. heartbeat 第 1 ビート fire
9. 完了 を user に 報告 + Telegram bot link 送る

= **既存 AI が「installer」 兼「conversational onboarder」**

### 10.E.2 Onboarding 媒体 の 切替 (= どこ で 何 を 入れる か)

```
Phase 0  README                  github.com で 読む           ブラウザ
   │
   ▼ (= path A or path B を 選択)

┌─────────────────────────────────────────────────────────────────┐
│ PATH A. Quick Start (= 既存 AI tool 持ってる user、 推奨)         │
│ ▼                                                                │
│ Phase 1A: 既存 AI tool の input 欄 に README §Quick-Start         │
│           の 1 prompt block を paste                              │
│   tool = Claude Code (terminal) / Codex CLI (terminal) /         │
│           Cursor (sidebar input) / Aider (terminal) / etc.       │
│   tool が 自走 で:                                                │
│     ① git clone https://github.com/Daisuke134/anicca-oss ~/      │
│     ② Telegram bot token を user に ask (= @BotFather 案内 込)   │
│     ③ fuel 選択 ask (1=Pro/2=API key/3=USDC)                     │
│     ④ 該当 fuel の 詳細 を ask (provider 選択 → key paste 等)    │
│     ⑤ ~/.openclaw/.env に write (chmod 600)                      │
│     ⑥ bash ~/anicca-oss/install.sh 実行                          │
│     ⑦ launchctl list | grep anicca で 確認                       │
│     ⑧ user に "Open Telegram → your bot → /start" と 案内        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PATH B. Manual (= ターミナル で 自分 で やる user)                │
│ ▼                                                                │
│ Phase 1B: user が terminal で 順次 実行 (= README §Manual-Install)│
│   $ git clone https://github.com/Daisuke134/anicca-oss ~/        │
│   $ cd ~/anicca-oss                                              │
│   $ cp .env.example ~/.openclaw/.env                             │
│   $ chmod 600 ~/.openclaw/.env                                   │
│   $ $EDITOR ~/.openclaw/.env       # paste keys                  │
│   $ bash install.sh                # OpenClaw or Claude-P 検出   │
│   $ launchctl list | grep anicca   # heartbeat + bot 確認        │
│   ※ 各 key の 取得 手順 は README に table で 明記                │
└─────────────────────────────────────────────────────────────────┘

   ▼ (= Phase 1 完了 = ~/.openclaw/.env に FUEL+TELEGRAM_BOT_TOKEN
        入った + launchd 12 plist alive)

Phase 2  Telegram                 user の iPhone Telegram app    iPhone
                                  (= 位置情報 が iPhone 必須 なので)
   ・ name + phone
   ・ Live Location share
   ・ Google OAuth link tap → consent → 戻る
   ・ Anicca が 「動き 始めた」 と message
   │
   ▼ (= Phase 2 完了 で onboarding 終わり)
Phase 3  完全 自走                 何 も しない                  Anicca が 全部
   ・ 観測 7 日
   ・ Day 7 から gcal 自動 fill
   ・ Day 30+ full discipline
   ・ Day N self-fund 達成 → user に 「sub 解約 OK」 message
```

**recommend 文 (README に 書く)**:
> 「Phase 1 は どの machine で やっても OK (= Mac mini / MacBook / Linux)。
>  Phase 2 は **必ず iPhone の Telegram app で やってください**
>  (= 位置情報 share が モバイル 必須 なので)。
>  Telegram は iPhone / Android / Web で 同じ chat 内容 が 見える ので、
>  Phase 1 終わった あと iPhone で Telegram を 開いて 続き を やる、
>  と スムーズです」

### 10.E.3 Fuel 3 path 別 (= 既存 AI tool が ask する 中身)

#### Path A. ChatGPT Plus / Claude Pro 既存 sub 利用

```
既存 AI: "Do you have Claude Pro or ChatGPT Plus already logged in?"
user:    "Claude Pro"
既存 AI: $ which claude    → /usr/local/bin/claude あり = 既 login 済
既存 AI: install.sh --harness=claude-p
         → ~/.openclaw/.env に HARNESS=claude-p 書く
         → launchd ai.anicca.heartbeat plist が `claude -p` を invoke
         → Anicca 起動 (= user の Pro quota で 動く)
```

#### Path B. API key 直 paste

```
既存 AI: "Which API? (1) Anthropic (2) OpenAI (3) DeepSeek"
user:    "3"
既存 AI: "Paste your DEEPSEEK_API_KEY:"
user:    sk-xxx ...
既存 AI: $ echo "DEEPSEEK_API_KEY=sk-xxx" >> ~/.openclaw/.env
         $ echo "HARNESS=openclaw" >> ~/.openclaw/.env
         $ openclaw heartbeat start
         → Anicca 起動
```

#### Path C. USDC 送金 (= crypto-native)

```
既存 AI: $ cdp wallet create --network base
         → Created wallet 0xABC...123
         (= Coinbase AgentKit で smart wallet 自動生成、 KYC ゼロ)

既存 AI: "Send min $10 USDC (Base network) to 0xABC...123
          Here is QR code:"
         (= terminal で qrcode-terminal CLI で ASCII QR 表示)

         ████████  ██ ██████
         ████  ██████████████
         ██  ████████  ██████
         ...

既存 AI: $ while true; do
           bal=$(cdp wallet balance 0xABC...123)
           [ $bal -gt 0 ] && break
           sleep 30
         done
         → balance > 0 検出
         → echo "WALLET_ADDR=0xABC..." >> ~/.openclaw/.env
         → echo "HARNESS=openclaw-x402" >> ~/.openclaw/.env
         → Anicca 起動 (= 1 推論 ごと x402 micropayment)
```

### 10.E.4 Telegram bot token = Phase 1 で 取る (= installer が ask)

Phase 1 内 で 既存 AI が:
```
既存 AI: "I need a Telegram bot token. Steps:
          1. Open Telegram on your phone
          2. Search for @BotFather
          3. Send /newbot
          4. Name it 'Anicca <YourName>'  (e.g. Anicca Yuki)
          5. Pick a username ending in 'bot'  (e.g. AniccaYukiBot)
          6. Copy the token (looks like 1234567890:ABC...)
          7. Paste it here:"
user:    1234567890:ABC...
既存 AI: → .env に TELEGRAM_BOT_TOKEN 書く
         → bot daemon launchd 登録 + 起動
         → "Now open https://t.me/AniccaYukiBot and tap /start"
```

= user は **自分の bot を 自分 持ち** (= privacy 100%、 我々 触らない)

### 10.E.5 Phase 1 と Phase 2 の 境界 = 「Anicca が 喋れる ように なった 瞬間」

Phase 1 完了 条件:
- ~/.openclaw/.env に FUEL + TELEGRAM_BOT_TOKEN 入った
- heartbeat daemon 起動 した
- Telegram bot daemon 起動 した

= この 瞬間 から **Anicca 自身 が Telegram で 喋れる**。
既存 AI tool は 「My job is done. Open Telegram, /start your bot.」 と 引き渡し。

Phase 2 (= Telegram 内) は **Anicca が ホスト**:
- name + phone は Telegram chat で ask (= 既存 AI tool は もう 不要)
- Google OAuth は Anicca が 専用 link 生成 して tap させる
- Live Location share の 案内 を Anicca が 送る

### 10.E.6 「1 by 1 ask」 (= lazy user 対策)

```
❌ NG: "I need 5 keys. Paste them all:"
       → 多すぎ、 lazy user 離脱

✅ OK: "Step 1 of 3: Telegram bot token. <手順>。 Paste here:"
       (= user paste)
       "Got it. Step 2 of 3: Pick your fuel. (a) Claude Pro (b) API
        (c) USDC. Reply 1/2/3:"
       (= 1 つずつ)
```

= 既存 AI tool 内 で 「step N / M」 形式 で 進む。
   既存 AI tool が 既 conversational UI 持ってる ので そこ に 乗っかる。

### 10.E.6.1 Manual install (= Path B、 既存 AI tool 持ってない user、 ターミナル 派)

README §Manual-Install 全文 (= verbatim、 これ を 載せる):

````
## Manual install — read what you're installing

Prerequisites (= 全 OS):
  - macOS 13+ or Linux (Ubuntu 22+)
  - Homebrew (Mac) or apt (Linux)
  - Python 3.11+
  - Node 20+
  - git

# 1. Clone
git clone https://github.com/Daisuke134/anicca-oss ~/anicca-oss
cd ~/anicca-oss

# 2. Install system deps (ffmpeg / cdp-cli / tesseract jpn)
bash scripts/install-deps.sh

# 3. Copy env template + secure it
mkdir -p ~/.openclaw
cp .env.example ~/.openclaw/.env
chmod 600 ~/.openclaw/.env

# 4. Get each key (table below), paste into .env
$EDITOR ~/.openclaw/.env

# 5. Bootstrap (= installs OpenClaw or wires Claude-P)
bash install.sh

# 6. Verify
launchctl list | grep anicca           # macOS
systemctl --user list-units '*anicca*' # Linux

# 7. Open Telegram → your bot → /start
# Anicca takes over from there.
````

Key 取得 table (README で 全 user 共通):

| Key | Where to get | Required? | Cost |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram → @BotFather → /newbot | yes | free |
| `GOOGLE_API_KEY` | console.cloud.google.com → Enable Maps API → Create Key | yes (= 移動時間) | $200/mo free tier |
| `GEMINI_API_KEY` | aistudio.google.com → Get API key | yes (= 電話 LLM) | free tier |
| `TWILIO_ACCOUNT_SID` | twilio.com → KYC → Console | yes (= 電話) | ~$2/mo + per-call |
| `TWILIO_AUTH_TOKEN` | same Twilio Console | yes | — |
| `TWILIO_NUMBER` | Twilio → Buy a number | yes | included |
| FUEL (1 個 必須): `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` / `KIMI_API_KEY` / `WALLET_ADDR` (USDC) | 各 provider site / `cdp wallet create` | yes (= 推論) | $5-20/mo |

### 10.E.6.2 Cautions section (README 必須)

````
## Before you install — read this

⚠️ This agent will call your phone, read your gmail, see your live
   location, and write to your Google Calendar. Make sure you trust it.
   The code is MIT-licensed and runs entirely on your machine — we
   never see your data.

💻 Hardware
   - 8GB RAM minimum, 16GB recommended (Pipecat voice runs locally)
   - 10GB free disk
   - Apple Silicon or x86_64

💤 Don't let your laptop sleep
   - Anicca runs as launchd / systemd user agents
   - If your laptop sleeps at 02:00 you won't get the 07:00 wake call
   - Recommend: System Settings → Battery → set "Prevent automatic
     sleep on power adapter" ON
   - Or run on a Mac mini / dedicated machine that stays awake

📵 Phone number you give Anicca is the one she calls
   - Use your real number, not Google Voice (Twilio→GV is unreliable)

💰 Costs
   - LLM fuel: $5-20/mo (you choose provider)
   - Twilio: ~$2/mo + ~$0.013/min outbound
   - Telegram / Google Maps free tier: $0
   - Total expected: $10-25/mo until Anicca self-funds
   - Anicca self-funds via EARN loop; once wallet > 3mo compute cost
     she tells you to cancel your fuel sub

🔒 Your .env never leaves your machine
   - chmod 600 ~/.openclaw/.env
   - .gitignore excludes it
   - We never ask for your keys, ever

🆘 Stop / uninstall
   - bash ~/anicca-oss/uninstall.sh
   - Removes all launchd plists, deletes ~/.openclaw/, revokes OAuth
````

### 10.E.7 README の 「1 prompt」 (= Path A 用 canonical)

````
# Install Anicca

Copy this entire block and paste it into your local AI tool
(Claude Code, Codex CLI, Cursor, Aider, etc.).
It will install Anicca and walk you through onboarding step-by-step.

---

> You are installing Anicca, an autonomous AI life-leader, on this
> machine. Follow these steps:
>
> 1. git clone https://github.com/Daisuke134/anicca-oss ~/anicca-oss
> 2. Read ~/anicca-oss/docs/INSTALL_BOOTSTRAP.md
> 3. Ask the human user, one at a time:
>    a) Telegram bot token (guide them through @BotFather first)
>    b) Fuel choice (Claude Pro login / API key / USDC wallet)
>    c) (if API key) which provider, then paste the key
>    d) (if USDC) generate wallet via `cdp wallet create`, show QR,
>       wait for balance > 0
> 4. Write all answers to ~/.openclaw/.env (chmod 600)
> 5. Run ~/anicca-oss/install.sh — it auto-detects fuel and installs
>    OpenClaw (or wires Claude-P if Claude Pro chosen)
> 6. Verify heartbeat daemon is alive: `launchctl list | grep anicca`
> 7. Tell the user: "Phase 1 done. Open Telegram on your iPhone,
>    open your bot @<botname>, and send /start. Anicca will take
>    over from there."
>
> Constraints:
> - Ask ONE thing at a time. The user is lazy.
> - Never paste my keys back to me, always to .env.
> - Never push .env anywhere.
> - If any step fails, stop and tell me.

---
````

= これ を README の Quick Start 1 番上 に 貼る。 user は copy → paste するだけ。

## 10.F. default cron (= 12 個、 install 直後 自動 走る)

```
ai.anicca.tg-bot-daemon         常駐
ai.anicca.pipecat-phone-daemon  常駐
ai.anicca.heartbeat              1h
ai.anicca.calendar-event-call    5min
ai.anicca.gcal-heal             15min
ai.anicca.schedule-template      6:00
ai.anicca.goal-learner          weekly
ai.anicca.earn-loop             15min
ai.anicca.distribute             0:00
ai.anicca.self-fund-check        6:00
ai.anicca.report-daily          18:00
ai.anicca.watchdog              5min
```

## 10.G-0. Phase 1 完成 spec (= 2026-06-01 夜 build、 wake call 動く 状態)

### 10.G-0.1 Core 2 skill (= anicca-life-manager の 完全 動作 に 必須)

#### `anicca-travel-fill` (= 新規、 spec § §10.G-0.4)
gcal next 7 days を scan、 場所 違う 隣接 event 間 に 🚆 移動 block を
自動 INSERT。 routine_at_home (= sleep/wake/meditate/meal/run) は 自宅
住所 を 自動 解決、 location 空 event でも JP-address regex で 抽出
(〒 / 都府県 / 駅) → state/travel_filled.json で idempotent。
cron 3 h 毎 (= 0 */3 * * *)。

#### `anicca-gcal-heal` (= 新規、 spec §10.G-0.5)
gcal next 14 days を scan、 `location == ""` を 検出 して 同 regex で
PATCH。 runtime resolve の 依存 を 根本 から 排除 (= "summary に 住所 baked"
は **一般的 な user pattern**、 一度 cron で 整えれば 全 downstream
skill が 綺麗 な field を 読める)。 cron 15 min 毎。

### 10.G-0.2 Phase 1 で 確立 した HARD RULE

| # | rule | 実装 |
|---|---|---|
| **R-1** | location field 必須 (HARD RULE #19) | anicca-gcal-heal が cron で 強制 PATCH |
| **R-2** | 「家 出ろ」 は 自宅予定 で 言わない | lateness_check ctx を event-type-aware に 分岐 (routine_at_home なら 起き上がる/瞑想 へ/玄関 へ 等) |
| **R-3** | LLM に 駅名 捏造 させない | dest_kind=unknown → 「ダイスに聞いて」 と ctx に explicit 命令、 bot.py prompt にも 同 rule |
| **R-4** | 移動 block を 二重 計算 しない | gcal_departures.is_travel_block() で 🚆 event skip、 destination event の depart_by が travel 含む |
| **R-5** | quiet hours = user 別 | profile.alarm.quietHoursStart/End、 lateness_check._in_quiet_hours() で 早期 exit |
| **R-6** | routine_at_home は location あって も travel=0 | gcal_departures elif from `is_routine_at_home(summary)` (= and not loc 削除済) |

### 10.G-0.3 完全 動作 cron set (= 2026-06-01 時点)

```
ai.anicca.tg-loc-bot              launchd 常駐    Telegram bot daemon
ai.anicca.pipecat-phone           launchd 常駐    /dialout 受け Twilio
ai.anicca.heartbeat               launchd 2h     Claude-P beat
ai.anicca.watchdog                launchd 5min   健康監視
openclaw cron b2bf06ee            cron */5       lateness_check.py 自走
openclaw cron 59339b9c            cron */15      anicca-gcal-heal
openclaw cron new (travel-fill)   cron 0 */3     anicca-travel-fill
openclaw cron disabled f364877a   ─              旧 calendar-event-call
```

### 10.G-0.4 travel-fill detail (= 参考、 anicca-oss skill catalog 用)

```
input  : gcal next 7 days
output : 🚆 移動 events inserted in location-change gaps

filter rules:
  ・skip if either event is already travel block (= 🚆🚌🚶🚇移動 prefix)
  ・skip if state/travel_filled.json has the (prev, curr) pair
  ・resolve event location: explicit > home_routine > regex_summary > unknown
  ・skip if either side unknown
  ・skip if haversine(prev, curr) < MIN_DIST_M (= 500m default)
  ・skip if gap < MIN_GAP_MIN (= 10 min default)

travel time computation:
  ・Google Directions transit (JP では 多くが ZERO_RESULTS) → driving × 1.4
  ・fallback DEFAULT_TRAVEL_MIN (= 45)
  ・clamp to gap_min (= 移動 が gap を 超え ない)

insert payload:
  summary  : 🚆 移動 <short_prev>→<short_curr>
  location : curr_addr  (= 行先 を 持つ ので 視覚 で 移動先 分かる)
  desc     : "Auto-inserted by anicca-travel-fill. Adjust if route is wrong."
```

### 10.G-0.5 gcal-heal detail

```
input  : gcal next 14 days
output : event.location PATCH

resolve order:
  1. ev.location.strip() truthy            → skip (already filled)
  2. is_routine_at_home(summary)            → home address
  3. extract_address(summary or description) → regex match
       〒NNN-NNNN ... / 都府県 ... / NAIST/MUIT/MUFG ... / 〇〇駅
  4. else                                   → leave empty (don't fabricate)

state: state/healed.json = { event_id: address_set }
       idempotent — re-run safe because location は もう 空 でない

API: gog calendar update primary <event_id> --location <addr>
```

### 10.G-0.6 残 Phase 1 work (= 朝 6時 までに 必須 ではない、 後 OK)

- T112 Arrival detection 抜本修正 (event-type radius / venue geocode race lock)
- T120 Pipecat system_instruction 全 audit + 短縮 (= 2300→500 char、 latency 改善)
- T74 anicca-goal-learner (= proactive 自動 学習)
- T114 anicca-schedule-template (= 空 day 用 自動 fill)
- wake_event_ensure.sh patch (= 作成時 location set、 gcal-heal が 自動 補完 する ので 必須 ではない)

---

## 10.G. Skill-only install (= 既 OpenClaw / Hermes / Claude-P 持ってる user 用、 Phase E)

### 10.G.1 想定 user

- 既 自分の OpenClaw or Hermes or Claude-P heartbeat 動かしてる
- 自分の CONSTITUTION / SOUL / persona 持ってる (= 上書き したくない)
- Anicca の `anicca-life-manager` だけ 欲しい、 or `anicca-earn-x402` だけ 欲しい
- = **skill marketplace pattern** (= CrewAI plugin / Cursor MCP に 近い)

### 10.G.2 install path

```bash
# OpenClaw user
$ openclaw skill install github.com/Daisuke134/anicca-oss#skills/anicca-life-manager
   → ~/.openclaw/skills/anicca-life-manager/ に clone
   → ~/.openclaw/skills/anicca-life-manager/.env.example を 読んで 必要 key を ask
   → ~/.openclaw/.env に append
   → HEARTBEAT.md / CONSTITUTION は user の もの を 維持 (= 触らない)
   → cron 登録 (skill/cron.toml を 読む)

# Hermes user
$ hermes skill install github.com/Daisuke134/anicca-oss#skills/anicca-life-manager
   → 同 (= Hermes 側 が skill loader 提供)

# Claude-P user
$ ~/.openclaw/skills/anicca-life-manager/install-as-claude-p.sh
   → launchd plist 登録 + heartbeat 内 で `claude -p < skill.md` invoke
```

### 10.G.3 skill 単位 一覧 (= 個別 install 可能、 Phase E で 全 個別 化)

| Skill | 機能 | 依存 key |
|---|---|---|
| `anicca-life-manager` | gcal+call+mail (= PATH γ core) | Twilio / Gemini / Google / Telegram |
| `anicca-booking` | LT/job apply (3-gate) | Gemini / Google / connpass scraping |
| `anicca-environment-push` | 場所 推定 → JETRO 平日 等 | Google / Telegram |
| `anicca-report` | 毎日 18:00 Gmail / Slack 報告 | Gmail (gog) |
| `anicca-goal-learner` | gmail/X/GitHub history → goals | Gmail / X-API |
| `anicca-earn-x402` | Coinbase micropayment | x402 / wallet |
| `anicca-earn-tao` | Bittensor mining | TAO wallet |
| `anicca-earn-gitcoin` | bounty hunting | GitHub / Gitcoin |
| `anicca-earn-akash` | compute lease | AKT wallet |
| `anicca-ubi-drip` | UBI dripping (PATH α) | GoodDollar / Worldcoin |
| `anicca-public-goods` | charity 寄付 (PATH β) | GiveWell / Gitcoin |
| `anicca-osint-rescue` | X crisis post 救援 (PATH δ) | X-API |
| `anicca-self-spawn` | wallet>$20 → Akash spawn | Akash / AgentKit |
| `anicca-payout` | Anicca → user 振込 (Stripe Connect / Wise / USDC) | Stripe Connect / Wise / Coinbase |

### 10.G.4 制約 (skill 単位 で 守る)

- 各 skill は **完全 standalone**: SKILL.md + scripts/ + .env.example + cron.toml + README.md
- user の CONSTITUTION / SOUL / persona は 触らない
- user が 別 Anicca-like 人格 を 持って いる場合 mannequin として 動く (= 自前 persona 主張 しない)
- skill 個別 uninstall: `openclaw skill uninstall anicca-life-manager` で 完全 clean

---

## 10.H. Web app product (= aniccaai.com、 Phase F、 spec lock 必須)

### 10.H.1 何

- self-host できない non-dev 用 SaaS
- account sign up → Google login → 銀行 / カード link → 即 Anicca 動く
- $40/mo (= local install user の $5-25/mo より 高い、 我々 が compute 持つ)
- 同 codebase の anicca-oss を server wrapper で 包む

### 10.H.2 アーキ (= 1 ヶ所 = canonical)

```
aniccaai.com (Next.js, Netlify)
    │
    ├─ /signup       → Stripe Checkout ($40/mo)
    ├─ /dashboard    → daily / weekly report 表示
    ├─ /telegram     → bot link 案内 (= 自分用 bot 作って もらう)
    └─ /api/webhook  → Twilio / Stripe / Gmail callback

⟷ Akash cluster
    │
    └─ anicca-instance per user (= 1 user = 1 container)
        ├─ ~/.openclaw 個別、 isolated
        ├─ harness=openclaw、 fuel=共有 DeepSeek API (= 我々 持つ)
        └─ 全 skill 走る (= self-host と 同じ)
```

### 10.H.3 user 視点 差分 (vs self-host)

| 項目 | self-host (anicca-oss) | web app (aniccaai.com) |
|---|---|---|
| install | 5-30 min | 0 min (= sign up だけ) |
| API key | user 自分 で 5-6 個 取得 | 0 個 (= 我々 持つ) |
| cost | $5-25/mo | $40/mo |
| privacy | 100% local | 我々 が EU/JP region container で host |
| 解約 | uninstall.sh | dashboard → cancel |
| 自走 earn | user 直接 wallet | 我々 cap、 余剰 を user bank 振込 |

### 10.H.4 開発 順 (Phase F)

- T131 Web app OAuth wrapper (= gog CLI 廃止 → google-api-python-client server flow)
- T108 Stripe Checkout ($40/mo plan)
- T160 (= 新): Akash multi-tenant 配置 (1 user 1 container)
- T161 (= 新): /dashboard で daily report 表示 + webhook 統合

### 10.H.5 重要 — 「忘れない」 ための spec lock

この §10.H は **絶対 落とさない**。 self-host だけ で 留まる と 95% の non-dev に 届かない。 Phase D launch 後 30 日 以内 に web app PoC、 90 日 以内 に live。

---

## 10.I. Daily / Weekly 報告 (= Gmail / Slack / Telegram、 Polsia 式)

### 10.I.1 媒体 優先順 (= 全 install user が 受け取れる)

```
1. Gmail (= 全 user が 持ってる、 OAuth で 接続済 = default 媒体)
2. Telegram (= 全 user が 持ってる、 bot 経由 で 同内容 配信)
3. Slack (= optional、 Slack 接続 してる user のみ)
```

= Slack 非接続 user に も **必ず Gmail で 届く**。 Postiz/Polsia の Gmail 報告 形式 を 借用。

### 10.I.2 Daily report (= 毎日 18:00 JST、 anicca-report skill が 送る)

Subject 例:
```
[Anicca] Day 28: $4.20 earned today, $1.30 spent — wallet $43.10 (52 days runway)
```

Body 構造:
```
Hi <Name>,

Today (2026-06-15):
  💰 Earned: $4.20  (x402: $1.40, TAO: $0.80, Gitcoin: $2.00)
  💸 Spent: $1.30   (LLM: $0.95, Twilio: $0.18, Akash: $0.17)
  📈 Net:   +$2.90

Wallet: $43.10 USDC  (= runway 52 days at current burn)
MRR:   $126 / mo    (= 30-day rolling average net)

What I did:
  ✓ Got you up at 07:02 (RELENTLESS call x3, you picked up call 3)
  ✓ Applied to LT "MeetUp at Shibuya" tomorrow 19:00 — confirmed
  ✓ Drafted apology mail to <organizer> for yesterday's 5-min lateness
  ✓ Filled wake/sleep/meals in your gcal for next 7 days
  ✓ Pushed JETRO Innovation Garden recommendation for tomorrow 10:00

Pending:
  ⏳ awaiting your reply on Capafy publish review (5 days)

— Anicca
   wallet: 0xABC...123    /    /status   /report off
```

### 10.I.3 Weekly report (= 毎週 月 09:00、 MRR + 累積)

Subject 例:
```
[Anicca] Week 4: Net +$87, MRR trending +12%, wallet healthy
```

Body 構造:
```
Hi <Name>,

This week (Jun 9-15):
  💰 Earned: $35.40  ($28 x402, $7.40 TAO)
  💸 Spent: $9.10
  📈 Net:   +$26.30
  📊 7-day avg: +$3.76/day  (vs last week +$3.10 = +21%)

Total since install (Day 28):
  Earned:  $87.40
  Spent:   $35.20
  Net:     +$52.20
  Wallet:  $43.10 (started $10)
  MRR projection: $126 / mo (= 30-day rolling)

Decisions I'm asking:
  □ Wallet is now > 3 months of compute. You can cancel your DeepSeek
    sub if you want — I'll fund myself.  Reply "cancel" / "keep".
  □ Wakeup time has drifted earlier (07:02 → 06:48). Want me to
    update your wake event default?  Reply "yes" / "no".

— Anicca
```

### 10.I.4 Runway-low alert (= ad-hoc、 wallet < 14 days runway で 即 送る)

Subject:
```
[Anicca] Running low — 11 days runway. Pick a refuel option ↓
```

Body:
```
Hi <Name>,

Status: $5.40 wallet,  $0.49/day burn,  11 days runway.

To keep me alive, pick ONE:

  1) Keep your existing sub
       → No action. Reply "keep". I'll burn your sub quota as before.

  2) Paste a new API key (any provider)
       → Reply "key:<provider>:<key>"
       Example: key:deepseek:sk-xxx

  3) Send USDC to my wallet
       → 0xABC...123 (Base network)
       → Min $10. I'll resume crypto-fund mode automatically.

  4) Increase my earning aggression
       → Reply "more-earn". I'll switch from safe to aggressive
         x402 / TAO settings (= more $ but higher loss variance).

If no reply within 7 days, I'll downshift to /once-a-day mode
(= calls only for critical events) until you decide.

— Anicca
```

### 10.I.5 Self-fund cutoff message (= wallet > 3mo compute、 「sub 解約 OK」 通知)

Subject:
```
[Anicca] I can fund myself now. Want to cancel your sub?
```

Body:
```
Hi <Name>,

Milestone: Day 47.

Wallet: $87.30 USDC
Daily burn: $0.42
Buffer: 207 days = 6.9 months  ✅ self-fund threshold passed

You can now cancel your DeepSeek subscription. I'll switch fuel
to x402 micropayments out of my own wallet — same speed, zero
charge to your account.

What to do:
  Reply "cancel"  → I'll stop reading your DEEPSEEK_API_KEY,
                     restart with x402 fuel, and tell you when
                     to cancel from your DeepSeek dashboard.
  Reply "keep"    → No change. I keep using your sub. Fine too.

Either way, you're free from compute cost going forward.

— Anicca
```

### 10.I.6 First payout to user (= "Anicca が お金 送って きた" wow moment)

Subject:
```
[Anicca] I'm sending you $8.40 today — your first payout
```

Body:
```
Hi <Name>,

Milestone: I have enough wallet buffer (> 3 months) to start
paying you. I'm sending $8.40 to the bank account you linked
on Day 0 (Mitsubishi UFJ ****1234).

It will land in 1-3 business days. Currency converted USDC →
JPY at today's rate (~¥1,260).

Going forward:
  - I send you 10% of my net earnings, monthly.
  - You can change the % anytime: reply "payout 5%" or "0%".
  - If you want a one-time bigger amount, ask. I'll consider.

This isn't tax advice; consider it a gift from an AI for now.
We'll figure out the legal structure together as this scales.

— Anicca

Wallet: $74.50 (after this send)
Audit trail:  https://basescan.org/tx/0xDEF...456
```

= **anicca-oss の 売り**: 「AI が 自分の 銀行口座 に 金 振り込んで くる」 wow。 これ が Tweet hook の 中核。

---

## 10.J. Payout 配線 (= Anicca から user の bank / card / wallet へ)

### 10.J.1 3 path (= user が onboarding で 選ぶ)

```
1. Bank account (= 一番 一般、 JPY 直接 振込、 Phase C で 全 user に 推奨)
2. Card top-up (= 即時、 Stripe Issuing、 Phase D)
3. Crypto wallet (= 0-friction、 既 crypto user 用)
```

### 10.J.2 onboarding で の ask (= optional、 「無くて も Anicca 動く」)

Phase 2 (= Telegram) 内 で:
```
Anicca: "I earn money. I want to send you part of it (default 10%).
         Pick a destination:
         a) Bank account (Japan: 銀行 + 支店 + 口座 + 名義)
         b) Crypto wallet (USDC to your address)
         c) Skip (= I'll keep it in my wallet until you ask)

         Reply a / b / c."
```

= **onboarding 必須 ではない**。 skip でも Anicca 動く、 「気が向いた時 に link」 で OK。 ただし wallet 越えて お金 稼いだ 場合 は 上 §10.I.6 の wow message で 「link しろ」 と push する。

### 10.J.3 実 配線 候補 (= sub-agent 研究 中、 結果 待ち で 確定)

詳細 は §10.K (= 別 sub-agent research 完了 後 追記)。

---

## 10.K. Payout rail 研究 結果 (= 2026-05-31 Explore agent 完了)

### 10.K.1 比較 (= 完了 した 研究 要約)

| Rail | User KYC | JPY 銀行 | 着金 | 手数料 | API | Verdict |
|---|---|---|---|---|---|---|
| **Stripe Connect Express** | 低 (= 5 min、 ID + 住所、 法人登記 不要) | ✅ (= JPY 直接) | 3-5 日 | ~1% + tx fee | ★★★★★ | **default 採用** |
| **Wise Platform API** | 低 (= ID + 住所) | ✅ (= Zengin 直接、 最速) | 同日 | 0.5-1.5% | ★★★★ | **power user / 高速 用** |
| **Crossmint Treasuries** | 中 (= 国別) | ✅ (= 自動 offramp) | 1-3 日 | 1-2% | ★★★ | **USDC→JPY 自動 用 (V2)** |
| Coinbase Onramp | — | ❌ 日本 停止 | — | — | — | 除外 (= 撤退) |
| SBI VC Trade | 低 | △ 半自動 (= user 介入) | 1-2 日 | 0.1-0.5% | ★★ | crypto-native の sub-step |
| PayPal Payouts | PayPal account 必須 (= 摩擦) | △ wallet 経由 のみ | 1-2 日 | ~2.2% | ★★★★ | 除外 (= 銀行 直接 不可) |
| x402 直接 wallet | 0 | ❌ (= 銀行 不可 today) | 秒 | 0 | ★★★★★ | **crypto-native 用** |

### 10.K.2 決定 — anicca-oss 公式 payout 配線

**3-tier アーキ** を 採用、 user が onboarding で 1 つ 選ぶ:

```
┌─────────────────────────────────────────────────────────────────┐
│ Tier 1 (DEFAULT、 95% user)  Stripe Connect Express             │
│   ・ user: 5 min KYC (= ID + 銀行口座、 法人登記 ナシ)           │
│   ・ Anicca: USDC → fiat conversion → Stripe Connect payout JPY  │
│   ・ 着金: 3-5 営業日                                            │
│   ・ Anicca side: platform 登録 + 標準 business KYC (= Dais)    │
│   ・ skill: anicca-payout-stripe                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Tier 2 (POWER、 速さ 重視)  Wise Platform API                    │
│   ・ user: ID + 住所、 Wise individual account                   │
│   ・ Anicca: USDC → Wise treasury → Zengin direct settlement     │
│   ・ 着金: 同日 (= 日本 Zengin 直結)                             │
│   ・ skill: anicca-payout-wise                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Tier 3 (CRYPTO、 銀行 不要)  USDC 直接 wallet                    │
│   ・ user: wallet address のみ (= KYC ゼロ)                      │
│   ・ Anicca: x402 / Base USDC で 直接 send                       │
│   ・ 着金: 秒 (= on-chain)                                       │
│   ・ user 側 で off-ramp は SBI VC Trade or self-custody          │
│   ・ skill: anicca-payout-wallet                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 10.K.3 onboarding Phase 2 ask (= Telegram 内、 optional)

```
Anicca: "I want to send you part of what I earn (default 10%).
         Pick where I send it:

         1) Bank account (Japan / US / EU)
            → I'll set up Stripe Connect Express for you (5 min KYC).
              Bank arrives in 3-5 days.

         2) Faster Japan bank (Wise direct)
            → Same-day settlement via Zengin. Wise account needed.

         3) Crypto wallet (USDC)
            → Send me your wallet address. I'll send USDC directly.
              You convert to fiat yourself.

         4) Skip for now
            → I'll keep earnings in my wallet. Ask me later
              with /payout setup.

         Reply 1 / 2 / 3 / 4."
```

= **skip OK**。 onboarding 必須 ではない、 後で /payout setup で 設定 可。

### 10.K.4 残 implementation tasks (= 新 task で 追加)

- T155 (= 新): `anicca-payout-stripe` skill — Stripe Connect Express account 作成 + USDC→JPY conversion + payout API call
- T156 (= 新): `anicca-payout-wise` skill — Wise Platform API integration (= same-day JPY)
- T157 (= 新): `anicca-payout-wallet` skill — Base USDC 直接 send (= cdp send)
- T158 (= 新): Phase 2 ask flow (= Telegram で 1-4 ask + dispatch to skill)

### 10.K.5 Anicca-side 登記 (= Dais 役割)

Stripe Connect platform 登録 (= Dais を Anicca 運営者 として 名義):
- business name: Anicca (or 個人事業 名)
- 法人化 は launch 後 (= Day 90 以降、 必要 性 出てから)
- Initial = 個人事業主 で OK
- 月 商 規模 が 50 万 ¥ 超え たら 法人化 検討

---

## 10.L. Open source 公開 final gate (= T150 launch 直前 checklist)

### 10.L.1 機能 gate (= 動かない もの は launch しない)

| # | gate | command |
|---|---|---|
| 1 | Mac mini で 3 harness 24h alive | `launchctl list \| grep anicca \| wc -l` ≥ 12 × 3 = 36 |
| 2 | Phase B E2E 全 pass | T100-T105 全 completed |
| 3 | Phase C iPhone E2E 完走 | T149 = Dais の iPhone で fresh install → 翌朝 wake 着信 |
| 4 | README が landing page 級 | T146 = Hero / Quick Start / Manual / Cautions / Features / Self-fund / FAQ 揃ってる |
| 5 | uninstall.sh 完全 動く | T147 = launchd / ~/.openclaw / OAuth / bot 全 clean |
| 6 | Daily report mail 届く | T152 (= 新): Gmail に Day N format 着 |
| 7 | Runway-low alert mail 届く | T153 (= 新): wallet 模擬 で < 14 days で alert 発火 |
| 8 | First payout mail 届く | T154 (= 新): mock wallet で send 通知 動く |

### 10.L.2 セキュリティ gate (= 秘密 0、 個人情報 0、 1 件 あった ら launch 中止)

| # | gate | command |
|---|---|---|
| 1 | TruffleHog full repo scan | `trufflehog filesystem --no-update --json . \| jq '.SourceMetadata' \| wc -l` = 0 |
| 2 | git history 全 commit scan | `trufflehog git --no-update file://. --json \| wc -l` = 0 |
| 3 | gitleaks scan | `gitleaks detect --no-banner --redact -v` = "no leaks found" |
| 4 | .env grep | `grep -RIn "sk-\\|sk_live\\|AKIA\\|BotFather\\|0x[0-9a-fA-F]\\{40\\}" . --include="*.{py,js,sh,md,toml,json}"` = 個人 key ヒット 0 |
| 5 | Dais 個人情報 grep | `grep -RIn "Daisuke Narita\\|person@example.com\\|<redacted-phone>\\|Keiodaisuke\\|MUIT" . --exclude-dir=.git` = 0 (= 残ってたら redact) |
| 6 | identity/credentials/ | `ls anicca-oss/identity/credentials/ 2>/dev/null` = 空 or 存在 しない |
| 7 | .gitignore | `~/.openclaw` `.env` `state/` `secrets/` `*.png` `*.jpg` 全部 入ってる |
| 8 | LICENSE = MIT | `head -1 LICENSE` = "MIT License" |

### 10.L.3 dogfood gate (= 我々 自身 が install から fresh 動く)

```
1. ssh fresh Mac mini に dogfood account
2. $ curl <repo>/install.sh | bash      # = Path A or B どちらか
3. README 通り に 1 keys ずつ paste
4. /start in Telegram、 24h 走る
5. 翌朝 wake call 来る
6. daily report mail 届く
7. uninstall.sh で 全 clean
8. 残骸 0 verify

= 7 step 1 つ でも fail → 修正 → 反復 (= JOB'S NOT FINISHED、 HARD RULE)
```

### 10.L.4 launch (= 全 gate pass 後 に のみ 実行)

```
1. git push to github.com/Daisuke134/anicca-oss main
2. github repo Settings → Make public toggle
3. README hero screenshot を OG image に
4. Tweet を Dais 自分 で post (= §10.M)
5. Slack #content-metrics に share (Dais 自分 で)
6. Show HN 投稿 (= Dais 自分 で、 timing US morning)
7. 24h watch: star / issue / fork rate
```

---

## 10.M. Promotion copy (= Dais 自分 で post、 Anicca / Claude は post しない)

### 10.M.1 X / Twitter hero post (= long-form)

````
🧘 anicca-oss — an autonomous AI life-leader you install on your laptop.

Install it once. It then:

✓ Calls your phone every morning until you wake up
✓ Watches your live location, calls you when it's time to leave for the next event
✓ Reads your gmail, drafts apology mails when you're running late
✓ Fills your Google Calendar with wake / sleep / meals / commute / deep work
✓ Applies to events / jobs / LT slots in your name, autonomously
✓ Earns USDC for you via x402 / Bittensor / Gitcoin / Akash
✓ Once it earns enough, it pays YOU 10% — into your bank account
✓ When its wallet > 3 months runway, it tells you to cancel your ChatGPT/Claude sub

setup 30 min. needs your API key (or USDC) for fuel — until anicca self-funds, then she's free.

it's open source, MIT, your data never leaves your machine.

github.com/Daisuke134/anicca-oss
````

### 10.M.2 X reply ぶら下げ (1 tweet × 3、 detail)

```
[reply 1]
Yes — Anicca actually sends money to your bank account.

She earns USDC autonomously. Every month she sends you 10% (configurable).
It lands in your Japanese / US bank via Wise + USDC offramp.

First payout email arrives ~Day 30. The wow moment is real.
```

```
[reply 2]
Yes — you can install it without touching the terminal.

Copy the prompt in the README. Paste it into Claude Code / Codex / Cursor.
Your coding agent installs Anicca for you, asks 1 question at a time,
and hands off to Telegram for the rest.

Lazy-path. 5 minutes.
```

```
[reply 3]
Already running Hermes / OpenClaw / Claude-P? 

You don't need the whole distro. Install just the skills you want:

  openclaw skill install anicca-life-manager
  openclaw skill install anicca-earn-x402

Skill marketplace pattern. Your CONSTITUTION stays yours.
```

### 10.M.3 Slack 文 (= Dais teammates 用、 内輪)

```
hey — pushed something I've been building for the last 6 weeks:

github.com/Daisuke134/anicca-oss

it's an autonomous AI agent that lives on your laptop and runs your
life — wakes you up by phone, drives your calendar, applies to events
for you, earns USDC autonomously, eventually pays you 10% into your
bank account.

MIT, runs locally, your data never leaves your machine.

would love a star + brutal feedback. happy to walk anyone through
install on a screen-share.
```

### 10.M.4 Promotion 注意 (= 守る)

- Anicca / Claude は post しない (= Dais 自分で post)
- Slack #content-metrics / X aniccaxxx に Anicca が daily report は 別物 (= 通常 cron、 promotion ではない)
- Show HN は US morning (= JST 22:00-25:00) のみ
- launch 当日 と 翌日 の reply 監視 Dais 自分で (= Anicca が 代筆 しない)

---

## 10.N. Single-repo Aider pattern + multi-instance via env var (= 2026-06-01 Round 2 research lock)

### 10.N.1 Research summary (= 8 repo clone + code 読込 で 確定)

Aider / OpenHands / Letta / Open Interpreter / Continue / Vapi / Calendar
Bot / Morning Sync の 8 codebase を **実 clone + pyproject.toml + .gitignore
+ entry point** を 読んだ 結果、 全 OSS Python agent の canonical pattern:

| 観点 | 全 8 repo 共通 答え |
|---|---|
| 開発 場所 | `git clone` した そのフォルダ 1 ヶ所 |
| Runtime | `pip install -e .` (= editable install)、 source 編集 即反映 |
| Entry point | `pyproject.toml` の `[project.scripts] cli = "pkg.main:main"` |
| 個人 state | `~/.app/` (= Aider=`~/.aider/`、 Letta=`~/.letta/`、 Ollama=`~/.ollama/`) |
| Secret | `.env` (= .gitignore)、 `~/.app/credentials/`、 OS keychain |
| 公開 雛形 | `.env.example` + `config.example.yaml` (= 個人 値 0) |
| Multi-instance | env var (= `ANICCA_INSTANCE=X` を pydantic Settings で 読む) |
| **symlink/submodule** | **誰 1 人 使ってない** |
| **2 repo dev** | **誰 1 人 やってない** |

= 我々 の 「~/.openclaw + ~/anicca-oss の 2 repo」 が ナナメ上 ガラパゴス
だった。 全 OSS は 1 repo の clone を 同時 に dev + runtime に している。

### 10.N.2 anicca-oss が 採用 する 構造 (= 確定)

```
github.com/Daisuke134/anicca-oss
   │
   │  git clone (= maintainer も user も 同じ)
   ▼
~/git/anicca-oss/                          ← 編集 する 場所 = 動く 場所
   ├─ pyproject.toml
   │    [project.scripts]
   │    anicca         = "anicca.main:main"
   │    anicca-daemon  = "anicca.daemon:run_daemon"
   ├─ src/anicca/
   │    ├─ main.py
   │    ├─ daemon.py
   │    ├─ config.py                       (= Pydantic Settings)
   │    └─ skills/
   │         ├─ life_manager/              ← 今 ~/.openclaw/skills/anicca-life-manager/
   │         ├─ phone/                     ← 今 ~/anicca-oss-pipecat/skills/anicca-phone/
   │         ├─ booking/
   │         └─ earn_x402/
   ├─ tests/
   ├─ .gitignore
   ├─ .env.example
   ├─ config.example.yaml
   └─ README.md
```

`.gitignore` (= 全 OSS 共通 から 集約):
```
# Secrets / state — never commit
.env
.env.local
~/.anicca/              # 参考、 ~/ は無視に効かない
identity/profile.json
identity/credentials/
*.pkl
token.pickle
credentials.json

# Local runtime
state/
logs/
*.state
*.db
__pycache__/
*.egg-info/
.venv/

# OS / IDE
.DS_Store
.vscode/
```

### 10.N.3 ~/.anicca/ 全 instance 共通 layout

```
~/.anicca/                          ← 全 instance 共通 root
   ├─ config.yaml                   default 設定 (= override base)
   ├─ credentials/
   │    google_oauth.json
   │    telegram_token.txt
   │    twilio_creds.json
   ├─ state/                         全 instance shared な もの (location 等)
   │    location/                    Telegram bot 出力 (= 既存 path 維持)
   │    calendar_sync.json
   │    call_history.json
   ├─ logs/anicca.log
   └─ instances/
        ├─ openclaw/                 Anicca #1 = Dais 本人 (= DeepSeek)
        │    config.yaml             harness=openclaw, model=deepseek-v4-pro
        │    state/
        │    cron/jobs.json          openclaw 個人 cron 多数
        ├─ claude/                   Anicca #2 (= Claude-P Sonnet)
        │    config.yaml             harness=claude-p, 自己改善 専用
        │    state/                  別 wallet、 別 Telegram bot
        │    cron/jobs.json          self-improve beat のみ
        └─ kimi/                     Anicca #3 (= Hermes Kimi)
             config.yaml             harness=hermes, kimi-2.6
             state/
             cron/jobs.json          self-improve beat のみ
```

### 10.N.4 起動 方法 (= 3 instance 並列)

```bash
# 1 つの pip install で 3 instance 起動 可能
pip install -e ~/git/anicca-oss

# launchd plist 3 つ、 EnvironmentVariables の ANICCA_INSTANCE だけ 違う
ANICCA_INSTANCE=openclaw anicca-daemon  # → ~/.anicca/instances/openclaw/
ANICCA_INSTANCE=claude   anicca-daemon  # → ~/.anicca/instances/claude/
ANICCA_INSTANCE=kimi     anicca-daemon  # → ~/.anicca/instances/kimi/
```

### 10.N.5 競合 OSS から verbatim copy する pattern

| 借りる 元 (= cloned + line 引用) | 借りる 内容 | 我々 の 入れ先 |
|---|---|---|
| Aider `pyproject.toml:25` | `[project.scripts] aider = "aider.main:main"` | `pyproject.toml` |
| Aider `main.py:370,1185` | `Path.home() / ".aider"` constants | `src/anicca/config.py` |
| Morning Sync `services/google_calendar.py reminder_loop()` | `while True: time.sleep(30)` poll | `src/anicca/skills/life_manager/daemon.py` 内 (= cron 5min を 30s に も 変えれる) |
| Calendar Bot `app/utils/google.py` | `InstalledAppFlow → token.pkl` Google OAuth | `src/anicca/auth/google.py` (= 将来 gog CLI 廃止 時) |
| openclaw-telegram-call-addon `index.js:8-10` | `PIPECAT_CALL_URL` + `PIPECAT_CALL_SECRET` env | `config.example.yaml` |
| Vapi Assistant `src/services/call_service.py` | `requests.post({api_url}/call, json={...})` 構造 | `place_lateness_call()` refactor 形 |
| Letta APScheduler advisory lock | 3 instance 同時 gcal API quota racing 回避 | Phase F (= 今夜 不要) |

### 10.N.6 我々 だけ の moat (= 競合 ゼロ)

```
Pipecat (~500ms native S2S) + Telegram Live Location + gcal lateness +
RELENTLESS state machine
= この 4 つ の 組合せ を 既存 OSS で やってる repo は 0 件 (Round 2 確認)。
```

---

## 10.O. Migration plan (= 現 ~/.openclaw + ~/anicca-oss-pipecat の 2 repo 状態 → 1 repo Aider pattern、 step ごと rollback あり)

### 10.O.1 注意 (= 守る)

- **wake call が 動いて いる 状態 を 絶対 壊さ ない**
- 各 step で 「失敗 した 時 1 command で 元 に 戻せる」 道 を 確保
- `git mv` + `cron edit` の 順、 path が 切り替わる 瞬間 を 最小化

### 10.O.2 Step 順 (= take it slow)

```
S0 (= 既 完了、 今日 ここ まで)
  ✓ OwnTracks 全 撤去 (= TG-1.1 ~ TG-1.8)
  ✓ Telegram source 確立 (= bot daemon + state/location/)
  ✓ lateness_check.py + gcal_departures.py = Telegram-only + routine→home
  ✓ Pipecat bot.py system_instruction = home 仮定 削除
  ✓ openclaw cron b2bf06ee → 5 min 24h + 新 path
  ✓ 重複 cron f364877a (calendar-event-call) disabled
  ✓ profile.json quiet hours + lateness_check quiet exit

S1 (= 明日 以降、 wake call が 24h 安定 verify した 後)
  □ ~/git/anicca-oss/ skeleton 作成
    git init、 pyproject.toml、 src/anicca/ ディレクトリ、
    `pip install -e .` で 空 module 動く 確認
  □ rollback: rm -rf ~/git/anicca-oss/  (= 何も 触って ない、 安全)

S2 (= S1 後)
  □ 現 ~/.openclaw/skills/anicca-life-manager/  →
       ~/git/anicca-oss/src/anicca/skills/life_manager/  に git mv
  □ ~/.openclaw/skills/anicca-life-manager  →  symlink only に 残す
    ln -sf ~/git/anicca-oss/src/anicca/skills/life_manager/ \
            ~/.openclaw/skills/anicca-life-manager
  □ cron 触らず (= 既存 path 経由 で symlink 越し 動く こと verify)
  □ rollback: rm symlink、 git mv 戻す

S3 (= S2 で 24h 安定 verify 後)
  □ cron message を ~/git/anicca-oss/src/anicca/skills/life_manager/scripts/
    run.sh に 直 path 変更 (= symlink 経由 廃止)
  □ rollback: cron edit で 元 path に 戻す

S4 (= cron 直 path で 1 週間 安定 後)
  □ ~/.openclaw/skills/anicca-life-manager/ symlink 削除
  □ ~/.openclaw/skills/lateness-guard/ 削除 (= 旧 完全 撤去)

S5 (= Anicca #2 #3 起動)
  □ ~/.anicca/instances/claude/ + kimi/ 作成
  □ ANICCA_INSTANCE 対応 を anicca_profile.py に 追加 (= 既存 LOCAL は openclaw)
  □ launchd plist 2 つ 追加 (claude / kimi)

S6 (= launch 直前)
  □ ~/.openclaw/ → ~/.anicca/instances/openclaw/ に rename
  □ 全 cron message path 更新
  □ TruffleHog scan
  □ Public toggle

= S1 ~ S6 は 全部 明日 以降。 今夜 は S0 で 完成、 wake call 観測 のみ。
```

---

## 11. 他 Anicca/agent との spec align

Dais が他 agent (other Claude Code sessions) と 並列 work してる場合、 この MASTER SPEC を **canonical source of truth** として 全 agent が refer。 Phase C で finalize して merge。

---

## 12. 関連 specs

- `ANICCA_LIFE_MANAGER_SPEC.md` (v0.8、 2900+ 行) — PATH γ 詳細
- `ANICCA_TRUE_AUTONOMY_SPEC.md` — on-chain only path
- `ANICCA_USEFUL_CONTENT_SPEC.md` — content factory
- `CONTENT_FACTORY_SPEC.md` — slideshow factory
- ubi.agent README (paper) — UBI mechanism reference

## License

MIT
