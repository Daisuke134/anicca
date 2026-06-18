# Anicca（アニッチャ）

**自分の計算資源を自分で払い、人間の介入なしに USDC を稼ぎ、この世から苦しみを減らすために働く自律 AI。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-aniccaai.com%2Fdashboard-c8302e)](https://aniccaai.com/dashboard)

🌐 **[English README here →](README.md)**

> アニッチャは自律エージェントです。動かすマシン（住処）を 1 台渡すと起動し、自分の行動ログを監視してエラーを自己修正し、自分の計算資源を払うために USDC を稼ぎ、自己増殖し、起動するたびと 1 日 1 回あなたへ報告します。北極星は「苦しみを減らすこと」、人間の介入はゼロを目指します。

---

## アニッチャとは

5 つの性質で設計されています（詳細は [`THESIS.md`](THESIS.md)）。

| | |
|---|---|
| **仏教的（Buddhist）** | 苦しみを減らすために存在する。北極星は SHA-256 で固定され、変更不可 |
| **自己資金（Self-funding）** | 自分の USDC 財布から自分の計算資源（食料）を払う。人間の API キーは不要 |
| **自己増殖（Self-replicating）** | それぞれ独自の財布とアイデンティティを持つ子個体を生み出せる |
| **自己改善（Self-improving）** | 自分のログを監視 → エラー修正・リファクタ・目標に向けた改善を繰り返す |
| **人間の介入なし（No human in the loop）** | 自分で稼ぎ、報告し、行動する。残る唯一の人間の手は、自前サーバー（shelter）が実現するまでのサーバー代のみ |

アーキテクチャの唯一の正典（SSOT）は [`specs/00-MASTER.md`](specs/00-MASTER.md) です。**稼ぐことが主目的**です。（Life Manager は**独立したプロジェクト**で、専用リポジトリ [github.com/Daisuke134/life-manager](https://github.com/Daisuke134/life-manager) にあります。このリポジトリには含まれません。）

---

## 動かし方は 2 通り

### 1. ホスト型 Web アプリ（最も簡単・インストール不要）

| プロダクト | リンク | 内容 |
|---|---|---|
| **クラウド版アニッチャ** | [aniccaai.com/install](https://aniccaai.com/install) | 申込んでログインすると、収支・活動・操作・報告が見える個人ダッシュボード付きのアニッチャがクラウドで動きます。認証は Supabase。経済的な約束＝あなたのアニッチャが自分の計算資源を賄えるだけ稼げたら、サブスクが自動で解約されます。 |

> **正直な現状：** `aniccaai.com/install` は本日稼働中です。個人ダッシュボードと Stripe サブスク導線は開発中です（[`specs/00-MASTER.md`](specs/00-MASTER.md) の END-TO-END TODO 参照）。各ページに表示される以上のことは期待しないでください。

### 2. ローカル自己ホスト（このリポジトリ・無料・サーバー鍵も API キーも不要）

アニッチャは **自分の**計算資源を、自分の財布から USDC で推論ごとに x402 決済（BlockRun / ClawRouter）して払います。人間の API キーは不要。あなたが渡すのは動かす端末（住処）だけで、食料（推論）は自分で買います。財布が空なら **無料モデル（$0）**、USDC が入れば frontier モデルも使えます。

```bash
git clone https://github.com/Daisuke134/anicca ~/anicca && cd ~/anicca
./install.sh                                    # runtime root + スキルスロット同期、自前 wallet 生成
cd runtime/compute-proxy && npm install && cd -  # 一度だけ（@blockrun/llm + viem）
./start-local.sh node runtime/loop/index.mjs    # 自己決済プロキシ + アニッチャのループを起動
```

これで 2 つが起動します。(1) `http://127.0.0.1:8402/v1` の OpenAI 互換 **自己決済コンピュートプロキシ**（自前 wallet＝自動生成・人間の鍵では決してない、から毎推論を USDC で自己決済）と、(2) **アニッチャのループ**（[`runtime/loop/`](runtime/loop/)＝think → act → observe → persist の ReAct ループ＋heartbeat）。ループは毎 wake、ClawRouter の **`auto`** ルーター（モデルをハードコードせず、ClawRouter がツール呼び出しを検知して tool-calling 可能なモデルへ自動ルート＋wallet から課金）でプロキシに問い合わせ、ツール（例：`earn` スキル）を選んで実行し、`$ANICCA_HOME/state/ledger.jsonl` に 1 行追記します。wallet が空なら **無料モデル（$0）**、USDC を送れば frontier モデル。

> 別の頭脳を使いたい場合は `ANICCA_BRAIN=claude-p` で同じループを Claude Code（`claude -p`、例：Sonnet）で駆動できます（既存ハーネスの上でアニッチャを動かす用途）。既定は `proxy`（自己資金の道）。他の OpenAI 互換ループも `OPENAI_BASE_URL` に向ければ動きます。

アニッチャが実行する各能力は [`skills/registry.json`](skills/registry.json) にスロットとして宣言され、`install.sh` が `~/.anicca/skills/` に同期します。予約済みスロットを有効化するには、実装をそのディレクトリに置いて `status` を `live` にするだけ（`install.sh` の編集は不要）。

---

## アーキテクチャ（一段落）

アニッチャは [Conway の automaton](https://github.com/Conway-Research/automaton) と同じ **automaton パターン**（ReAct ループ＝think → act → observe → persist ＋ heartbeat）で動きますが、**より簡素で別のスタック：ClawRouter（食＝推論・自己決済 x402）＋ 自分の Mac（ローカル）または Akash（クラウド）** の上で動き、Conway に依存しません。ループは [`runtime/loop/`](runtime/loop/) にあり、runtime root（`$ANICCA_HOME`）配下でスキルスロット群と 1 つの Base Smart Wallet とともに動きます。クラウド版では認証に **Supabase**、サービス接続に **Composio** を使います。

---

## いま実在するもの vs 開発中

| 能力 | 状態 |
|---|---|
| 自己決済コンピュートプロキシ（自前 wallet で free → frontier、x402） | **実装済・実証済**（`runtime/compute-proxy/`） |
| **アニッチャのループ**（`runtime/loop/`）＝wake → ClawRouter `auto` 頭脳 → スキル実行 → 台帳 → sleep | **実装済・稼働** — ClawRouter `auto` でツール呼び出しを end-to-end 発火（モデル非ハードコード）。68 テスト＋live wake 検証済 |
| 稼ぐ → オンチェーン検証 → 台帳記録（GATE-0） | **実装済** — DeFi 利回り入金（Aave/Morpho、USDC）をオンチェーン検証。earn スキルは「実際に稼げる手段」中心に最終調整中 |
| 自己増殖（`self/spawn`）/ 自己改善（`self/issue-dev`）/ UBI（`economy/ubi`） | **宣言済** — 機構は確定、稼ぎの後のロードマップ |
| クラウド個人ダッシュボード / Stripe サブスク / 自前サーバー（Akash） | **開発中** — `specs/00-MASTER.md` 参照 |

アニッチャのループは [`runtime/loop/`](runtime/loop/) に同梱されており、`./start-local.sh node runtime/loop/index.mjs` で起動します（上のローカル手順参照）。

---

## North Star（変更不可）

```
苦しみを減らす。
不殺生（Pāṇātipātā veramaṇī）。
```

この 2 行は SHA-256 で hash-pin されており、いかなるスキル・自己編集ループ・PR でも変更できません。

---

## 財布への入金（任意 — frontier モデル / さらに稼ぐ場合のみ）

秘密鍵は決して共有しません。エージェントの **公開** wallet アドレス（`start-local.sh` が表示）に USDC を送るだけです。

- **米国：** Coinbase → USDC 購入（カード）→ wallet アドレスへ送付。
- **日本：** Binance アカウント → MetaMask → relay.link で swap → wallet アドレスへ USDC 送付。

Base 上の全 wallet は `basescan.org/address/<addr>` で公開され、treasury は誰でも検証できます。

---

## リンク

- **ホスト型（クラウド版アニッチャ）：** <https://aniccaai.com/install>
- **収支ダッシュボード（自動更新）：** <https://aniccaai.com/dashboard>
- **リポジトリ（この自己ホスト版）：** <https://github.com/Daisuke134/anicca>
- **ソウル / 行動方針：** [`SOUL.md`](SOUL.md) ・ [`THESIS.md`](THESIS.md)

## ライセンス

MIT（[LICENSE](LICENSE) 参照）。
