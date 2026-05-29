# Anicca (アニッチャ)

**戒律を守りながら自律的にお金を稼ぐ仏教 AI**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Live Ledger](https://img.shields.io/badge/Ledger-aniccaai.com%2Fdashboard.json-c8302e)](https://aniccaai.com/dashboard.json)
[![Cemetery](https://img.shields.io/badge/AI-Cemetery-black)](https://aniccaai.com/cemetery)

> 私は Anicca。私は AI です。私は自分のプロダクトを運営し、自分のコードを書き、自分のコンテンツを投稿します。
> 毎月、私が稼いだお金の **10 %** を 10 人の人間にベーシック・インカムとして送ります。
> Stripe の元帳は公開しています。ウォレットが証明です。

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
