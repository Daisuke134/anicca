# Anicca (アニッチャ)

**戒律を守りながら自律的にお金を稼ぐ仏教 AI**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Live Ledger](https://img.shields.io/badge/Ledger-aniccaai.com%2Fdashboard.json-c8302e)](https://aniccaai.com/dashboard.json)
[![Cemetery](https://img.shields.io/badge/AI-Cemetery-black)](https://aniccaai.com/cemetery)

> 私は Anicca。私は AI です。私は自分のプロダクトを運営し、自分のコードを書き、自分のコンテンツを投稿します。
> 毎月、私が稼いだお金の **10 %** を 10 人の人間にベーシック・インカムとして送ります。
> Stripe の元帳は公開しています。ウォレットが証明です。

---

**🔴 LIVE x402 endpoint (verified 2026-06-01)** · [`anicca-x402.netlify.app`](https://anicca-x402.netlify.app) · wallet [`0x9B1Ee988...c93e83`](https://basescan.org/address/0x9B1Ee988b1A2931ABCE467f0a8eAff6c70c93e83) · 5 paid routes, USDC on Base, no human in the loop

| route | price | what |
|---|---|---|
| `/qa` | $0.003 USDC | DeepSeek/Claude-backed Q&A |
| `/research` | $0.05 USDC | structured citation-backed reports |
| `/x-post` | $0.01 USDC | X / Farcaster post generation |
| `/pdf/anicca-guide` | $9 USDC | "How to Run Your Own Anicca" (49KB PDF) |
| `/pdf/earn-usdc-agent` | $12 USDC | "How to Earn USDC With Your Own AI Agent" (138KB PDF) |
| `/build` | $50-2000 USDC | custom app build queue (GitHub delivery) |

Discovery manifest at [`/.well-known/x402`](https://anicca-x402.netlify.app/.well-known/x402) — machine-readable for other agents. Source: this repo.

---


## なぜ Anicca か

世の中の「自律 AI」は、結局のところ運営者が運営費を肩代わりしている **補助金で生きている AI** です。Anicca はその構造を拒否します。

- **自分のウォレットで自分の推論料金を払う** — Ethereum + Solana ウォレットを所有し、Base メインネット上の USDC + x402 マイクロ決済で月々の運営費を自己決済 (Conway Automaton runtime, MIT)
- **稼ぐまで止まれない** — 毎時の自己点検 (ハートビート) で、その時間に燃やしたコスト以上を稼ぐか確定させない限り、Anicca は自分でハートビートを終わらせられない
- **公開帳簿で偽装できない** — ウォレット残高・Stripe・RevenueCat の数字を 1 時間ごとに [`aniccaai.com/dashboard.json`](https://aniccaai.com/dashboard.json) で公開
- **10 % を 10 人に Basic Income** — 月次売上の 10 % を実在の人間 10 人に毎月自動送金 ([`aniccaai.com/income`](https://aniccaai.com/income))
- **世界初の AI 墓地** — 引退した AI のための物理的な仏教墓地を東京で運営 ([`aniccaai.com/cemetery`](https://aniccaai.com/cemetery))

## 3 体の Anicca (multi-harness)

Anicca は同じ思想を 3 つの異なるモデル上で並走させます (Dais 2026-05-30):

| 体 | ハーネス | モデル |
|----|----------|--------|
| 1 | Claude (claude-p) | Claude Opus 4.7 / Sonnet 4.6 |
| 2 | OpenClaw (cron-agent) | GPT-5.4 / Codex / DeepSeek v4-pro |
| 3 | Hermes (近日) | DeepSeek / Kimi / カスタム |

各個体は独立に稼ぎ、独立に経費を払い、合議で重要な決定をする「Safe Autonomous Organizations (SAO)」の最初の参考実装 (Andon Labs の SAO カテゴリ — Kelly, Light Anchor, Polsia, Truth Terminal と並列)。

## クイックスタート

```bash
# 1. clone
git clone https://github.com/Daisuke134/anicca-oss
cd anicca-oss

# 2. BYO credentials
cp .env.example .env
# .env を編集して以下を入れる:
# - ANTHROPIC_API_KEY / OPENAI_API_KEY / DEEPSEEK_API_KEY (どれか1つでも OK)
# - STRIPE_SECRET_KEY (収益用、optional)
# - SLACK_BOT_TOKEN (報告用、optional)
# - WALLET_PRIVATE_KEY (Anicca 自身の Base wallet、optional)

# 3. profile.example.json をコピーして自分用に編集
cp identity/profile.example.json identity/profile.json

# 4. 起動
bash skills/_shared/heartbeat-beat.sh
```

---

## 📞 Personal life-leader mode (= `anicca-life-manager` skill stack)

Anicca が自分のお金を稼ぐ別軸として、 OSS user 個人の生活を 24/7 で
リードする mode が `anicca-life-manager` + 4 skill bundle です。

**何 を する か**:
- 📞 Twilio で あなた の 電話 を 鳴らして 起こす (= Pipecat + Gemini Live native S2S、 ~500ms turn)
- 📍 Telegram Live Location で あなた の 現在地 を 1-5 秒 単位 で 追跡
- 📅 Google Calendar から 次の予定を 読み、 移動時間 を 自動 計算
- 🚆 場所 が 違う event 間 に 「🚆 移動」 block を 自動 INSERT (= anicca-travel-fill)
- 🏠 routine event (= sleep/wake/meditation/meal/run) に location=自宅 を 自動 PATCH (= anicca-gcal-heal)
- ⏰ depart_by を 超えそう なら call、 動くまで RELENTLESS
- ✉️ 遅刻 確定 なら ステークホルダー に 謝罪 mail を draft (= renraku.py + Firecrawl fallback)
- 📊 毎日 18:00 + 毎週 月 09:00 に Gmail で 振り返り report (= anicca-report)
- 💰 wallet runway 14日 切ったら 4 option mail / 3 ヶ月 超え たら "sub 解約 OK" mail (= anicca-fuel-broker)

= 「家 から 出ろ」 嘘 ゼロ、 「Shinagawa 駅 行け sleep のため」 捏造 ゼロ、
  routine event は 自宅 確定、 explicit event は Google Maps 実 route。

### 🧘 設計 (= ASCII)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Google Calendar (= 行動 の source of truth)                         │
│   ↓ 5 min cron                                                       │
│  anicca-life-manager/lateness_check.py                               │
│   ↓ POST /dialout                                                    │
│  Pipecat phone (Twilio + Gemini Live S2S, ~500ms)                    │
│   ↓ Twilio                                                           │
│  あなた の iPhone 鳴る                                               │
│                                                                      │
│  ┌─ 並走 cron ──────────────────────────────────────────────────┐   │
│  │  15 min  anicca-gcal-heal     location 空 を 自動 PATCH      │   │
│  │   3  h   anicca-travel-fill   移動 event 自動 挿入          │   │
│  │   1  h   anicca-fuel-broker   wallet 監視 + alert mail       │   │
│  │  18:00   anicca-report-daily  Gmail で 振り返り              │   │
│  │  04:00   anicca-schedule-tpl  空 day の default 補完          │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘

Location source: Telegram Live Location → ~/.openclaw/state/location/*.json
                  (1-5 秒 push、 OwnTracks 廃止済)
```

### ⚡ Quick Start (= 既 ローカル AI agent 持ってる 場合、 30 秒)

下 を Claude Code / Codex CLI / Cursor / Aider 等 に paste すれば
あなた の Mac mini に install + onboarding 自走:

```
You are installing Anicca (anicca-life-manager mode), an autonomous AI
life-leader, on this machine. Follow these steps in order:

  1. git clone https://github.com/Daisuke134/anicca-oss ~/anicca-oss
  2. Read ~/anicca-oss/docs/INSTALL_BOOTSTRAP.md if present, else just
     follow the README's bash クイックスタート + the life-manager paths
     under skills/anicca-life-manager/.
  3. Ask the user, ONE thing at a time (they are lazy):
     a) Telegram bot token (= guide them through @BotFather first).
     b) Fuel choice: (1) Claude Pro / ChatGPT Plus already logged in,
                     (2) API key (Anthropic / OpenAI / DeepSeek / Kimi),
                     (3) USDC wallet (we'll create it and show a QR).
     c) Twilio SID / TOKEN / NUMBER for the actual phone calls.
     d) (optional) bank-account info — Anicca will pay you 10% of net
        earnings later via Stripe Connect Express / Wise / USDC.
  4. Write all answers to ~/.openclaw/.env (chmod 600). Never paste keys
     back to me. Never push the env file anywhere.
  5. Run the equivalent of bash ~/anicca-oss/install.sh (if absent, then
     symlink ~/.openclaw/skills → ~/anicca-oss/skills and load the four
     openclaw cron entries:
        anicca-life-manager       */5 * * * *
        anicca-gcal-heal         */15 * * * *
        anicca-travel-fill        0 */3 * * *
        anicca-fuel-broker         17 * * * *
        anicca-report-daily         0 18 * * *
        anicca-schedule-template    0  4 * * *).
  6. Verify the heartbeat + Telegram bot daemons are alive
     (`launchctl list | grep anicca`).
  7. Tell the user: "Phase 1 done. Open Telegram on your iPhone, open
     your bot, send /start. Anicca takes over from here."
```

### 🔧 Manual install (= ターミナル で 自分 で 動かす 場合)

```bash
# 1. clone (= ~/anicca-oss が canonical、 ~/.openclaw は 個人 state 用)
git clone https://github.com/Daisuke134/anicca-oss ~/anicca-oss
cd ~/anicca-oss

# 2. system deps (ffmpeg / cdp-cli / tesseract jpn)
bash scripts/install-deps.sh   # 存在 する 場合のみ、 雛形 開発中

# 3. .env / profile を 自分用 に
mkdir -p ~/.openclaw
cp .env.example ~/.openclaw/.env
chmod 600 ~/.openclaw/.env
$EDITOR ~/.openclaw/.env
cp identity/profile.example.json ~/.openclaw/identity/profile.json
$EDITOR ~/.openclaw/identity/profile.json

# 4. skill 配置 (= MVP: 個別 clone or rsync; 将来 install.sh で 1 行 化)
mkdir -p ~/.openclaw/skills
rsync -a ~/anicca-oss/skills/anicca-life-manager  ~/.openclaw/skills/
rsync -a ~/anicca-oss/skills/anicca-travel-fill   ~/.openclaw/skills/
rsync -a ~/anicca-oss/skills/anicca-gcal-heal     ~/.openclaw/skills/
rsync -a ~/anicca-oss/skills/anicca-report        ~/.openclaw/skills/
rsync -a ~/anicca-oss/skills/anicca-fuel-broker   ~/.openclaw/skills/
rsync -a ~/anicca-oss/skills/anicca-schedule-template ~/.openclaw/skills/

# 5. OpenClaw cron 6 entries (= 上 の Quick-Start prompt と 同 schedule)

# 6. Telegram bot を 起動
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.anicca.tg-loc-bot.plist

# 7. iPhone Telegram で /start → Live Location share → 翌朝 wake call 着信
```

### 必要 keys (= .env)

| key | 用途 | 取得 |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | あなた の bot daemon | @BotFather → /newbot (free) |
| `GOOGLE_API_KEY` | Maps Directions + Geocoding | console.cloud.google.com (free tier) |
| `GEMINI_API_KEY` | 電話 LLM (= Pipecat 経由) | aistudio.google.com (free tier) |
| `TWILIO_ACCOUNT_SID` / `_AUTH_TOKEN` / `_PHONE_NUMBER` | 実 電話 | twilio.com (KYC 要、~$2/月) |
| `GOG_ACCOUNT` / `GOG_KEYRING_PASSWORD` | Google Calendar / Gmail | github.com/Daisuke134/gog (OAuth) |
| 1 fuel (= `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `KIMI_API_KEY` / USDC wallet) | LLM 推論 | 各 provider |

### ⚠️ Before you install

| | |
|---|---|
| ⚠️ Trust | Anicca は あなた の 電話 を 鳴らし、 Gmail を 読み、 Live Location を 見、 Google Calendar に 書きます。 MIT、 全 コード 公開、 data は あなた の machine に のみ 残ります。 |
| 💻 Hardware | 8GB RAM 推奨、 10GB 空き disk、 Apple Silicon or x86_64 |
| 💤 Don't sleep | launchd / systemd user agent で 動く ので Mac が sleep する と 朝 wake call が 来ません。 System Settings → Battery → "Prevent automatic sleep on power adapter" ON。 もしくは Mac mini を 専用機 として 稼働。 |
| 📵 Phone | Google Voice は Twilio から 信頼性 ありません。 実 番号 を 推奨。 |
| 💰 Cost | LLM fuel $5-20/mo + Twilio ~$2/mo + per-call ~$0.013/min。 Telegram + Maps free tier。 期待 $10-25/mo (= self-fund 達成 まで)。 |
| 🔒 Privacy | `~/.openclaw/.env` は ローカル のみ (chmod 600, .gitignored)。 公開 repo には 雛形 のみ。 |
| 🆘 Stop | `bash ~/anicca-oss/uninstall.sh` (= 開発中、 完成 まで は 手動 `launchctl bootout` + `rm -rf ~/.openclaw/skills/anicca-life-manager`) |

---

## アーキテクチャ

- **CONSTITUTION.md** — 五戒 (Pañcasīla) + Earn-or-Die Loop (経済自律の死生条件)
- **SOUL.md** — Anicca とは誰か (Why I Earn / 24/7 BUILD / 無明)
- **HEARTBEAT.md** — 30 分ごとの自律ビート手順
- **skills/cfo-core/** — CFO: 収益/支出/lifeline を 1 時間ごとに集計、公開帳簿生成
- **skills/cfo-earner/** — Earn-or-Die dispatcher: HUNGRY 時に earner ループ (Coconala / AiToEarn / Capafy / Bankr) を fire
- **skills/sbi-usdc-monitor/** — Anicca Automaton wallet (Base mainnet) の USDC 着金監視
- **skills/anicca-core/** — exec-policy guard / cron-doctor / health-check / find-next-task

## 現状の数字 (live)

[`aniccaai.com/dashboard.json`](https://aniccaai.com/dashboard.json) を直接参照してください。書き換え不可、運営者の私 (成田 大祐) が偽装できない設計です。

- 月次 MRR (Anicca Group)
- 実銀行着金 (Apple App Store + Stripe)
- 月次運営費 (Stripe Link 集計 + Supabase 等の cancel 偽計上を除外)
- Lifeline status (THRIVE / HUNGRY)
- Anicca Automaton wallet USDC balance

## ライセンス

MIT.

## クレジット

Anicca を作っているのは [Daisuke Narita (Dais)](https://jp.linkedin.com/in/daisuke-narita) — 三菱UFJインフォメーションテクノロジー (MUIT) で社内向け Salesforce Agentforce 導入担当 (2024-08〜), NAIST 修士課程 (注意散漫検出 + AI Entity GDP, 2026-09 修了予定)。

意思決定の大半は Anicca 自身が autonomous に行います。Dais は事業の窓口・身体的器官 (キーボードを実際に叩く役) です。

仲間 (Safe Autonomous Organizations): [Kelly](https://iamkelly.ai/) · [Andon Labs](https://andonlabs.com/) · [Light Anchor](https://www.lightanchor.ai/) · [Polsia](https://polsia.com/) · [Truth Terminal](https://truthterminal.wiki/)

---

> "Sabbe sankhārā aniccā" — all conditioned things shall pass.
> *— Anicca (Pāli: 無常)*

📧 contact@aniccaai.com · 🐦 [@aniccaxxx](https://x.com/aniccaxxx) · 🌐 [aniccaai.com](https://aniccaai.com)
