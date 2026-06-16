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

アーキテクチャの唯一の正典（SSOT）は [`specs/00-MASTER.md`](specs/00-MASTER.md) です。**稼ぐことが主目的**であり、後述の Life Manager は独立した任意プロダクトです。

---

## 動かし方は 2 通り

### 1. ホスト型 Web アプリ（最も簡単・インストール不要）

| プロダクト | リンク | 内容 |
|---|---|---|
| **クラウド版アニッチャ** | [aniccaai.com/install](https://aniccaai.com/install) | 申込んでログインすると、収支・活動・操作・報告が見える個人ダッシュボード付きのアニッチャがクラウドで動きます。認証は Supabase。経済的な約束＝あなたのアニッチャが自分の計算資源を賄えるだけ稼げたら、サブスクが自動で解約されます。 |
| **Life Manager** | [aniccaai.com/lm](https://aniccaai.com/lm) | 独立したプロダクト：Google カレンダー / Gmail / Telegram を（Composio 経由で）接続すると、各予定の約 15 分前にアニッチャが電話（Telnyx + Gemini Live、ボイス＝Charon）をかけ、間に合うように「今出て」と伝えます。 |

> **正直な現状：** `aniccaai.com/install` は本日稼働中です。個人ダッシュボード・Stripe サブスク導線・`aniccaai.com/lm` の Life Manager ページは開発中です（[`specs/00-MASTER.md`](specs/00-MASTER.md) の END-TO-END TODO 参照）。各ページに表示される以上のことは期待しないでください。

### 2. ローカル自己ホスト（このリポジトリ・無料・サーバー鍵も API キーも不要）

アニッチャは **自分の**計算資源を、自分の財布から USDC で推論ごとに x402 決済（BlockRun / ClawRouter）して払います。人間の API キーは不要。あなたが渡すのは動かす端末（住処）だけで、食料（推論）は自分で買います。財布が空なら **無料モデル（$0）**、USDC が入れば frontier モデルも使えます。

```bash
git clone https://github.com/Daisuke134/anicca ~/anicca && cd ~/anicca
./install.sh                                    # runtime root + スキルスロットを ~/.anicca に同期
cd runtime/compute-proxy && npm install         # 一度だけ（@blockrun/llm + viem）
./start-local.sh                                # 自前 wallet を自動生成 → 自己決済プロキシ起動
```

`start-local.sh` は `http://127.0.0.1:8402/v1` に OpenAI 互換の **自己決済コンピュートプロキシ**を立て、`~/.automaton/wallet.json` の自前 wallet（自動生成・人間の鍵では決してない）から毎推論を USDC で自己決済します。frontier モデルを使いたければ、表示された wallet アドレスに USDC を送るだけです。

> **正直なスコープ（HARD 0.24 — 偽りの主張なし）：** このリポジトリには automaton ループ本体は **同梱されていません**。`install.sh` にも明記されており、`start-local.sh` は **コンピュートプロキシだけ**を起動します。あなた自身の OpenAI 互換ループを以下で差し込んでください。
>
> ```bash
> ./start-local.sh <your-loop-cmd>
> ```
>
> `OPENAI_BASE_URL` を読むループなら自動で自己決済プロキシ経由になります。引数なしで実行するとプロキシを前面で保持し、差し込み方を表示します。**BYOK は任意** — `~/.anicca/.env` に `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` を置けばそちらも使えますが、既定の無料ローカル動作には不要です。

アニッチャが実行する各能力は [`skills/registry.json`](skills/registry.json) にスロットとして宣言され、`install.sh` が `~/.anicca/skills/` に同期します。予約済みスロットを有効化するには、実装をそのディレクトリに置いて `status` を `live` にするだけ（`install.sh` の編集は不要）。

---

## アーキテクチャ（一段落）

1 つの **automaton** runtime（ReAct ループ＝think → act → observe → persist ＋ heartbeat スケジューラ）が runtime root（`~/.anicca`）配下で、スキルスロット群と 1 つの Base Smart Wallet とともに動きます。計算資源は **x402 で USDC を都度払って購入**（BlockRun / ClawRouter）— 人間の API キー不要。Web プロダクトでは認証に **Supabase**、サービス接続（Gmail / Google カレンダー / Telegram）に **Composio** を使います。Life Manager の約 15 分前の電話は **Telnyx + Gemini Live（ボイス＝Charon）** で発信します。

> **runtime ディレクトリ名について：** かつての「Hermes pivot」（`specs/07-HERMES-PIVOT.md`）は **撤回**され、runtime は **automaton** ループを直接動かす方針に確定しています（`specs/00-MASTER.md`）。genesis Mac 上では runtime ディレクトリ名が歴史的経緯で `~/.hermes/` のままですが、その中で動いているのは Hermes デーモンではなく **automaton** です。アニッチャは「二重脳」ではありません。

---

## いま実在するもの vs 開発中

| 能力 | 状態 |
|---|---|
| 自己決済コンピュートプロキシ（自前 wallet で free → frontier、x402） | **実装済・実証済**（`runtime/compute-proxy/`） |
| 稼ぐ → オンチェーン検証 → 台帳記録（GATE-0） | **稼働中** — 初の黒字 wake を 2026-06-16 にオンチェーン検証（実 ETH→USDC swap、純益プラス） |
| Life Manager：`ask`（情報不明時にメールで質問）/ `notify`（遅刻ドラフト → 承認 → 送信） | **稼働中**のスキルスロット |
| Life Manager：`travel`（移動ブロック自動挿入）/ `call`（15 分前の電話） | **宣言済** — 実装着地予定 |
| 自己増殖（`self/spawn`）/ 自己改善（`self/issue-dev`）/ UBI（`economy/ubi`） | **宣言済** — 機構は確定、稼ぎの後のロードマップ |
| クラウド個人ダッシュボード / Stripe サブスク / 自前サーバー（Akash） | **開発中** — `specs/00-MASTER.md` 参照 |

automaton ループ本体は **このリポジトリには同梱されていません**（自分の runner を持ち込む — 上のローカル手順参照）。

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
- **ホスト型（Life Manager）：** <https://aniccaai.com/lm>
- **収支ダッシュボード（自動更新）：** <https://aniccaai.com/dashboard>
- **リポジトリ（この自己ホスト版）：** <https://github.com/Daisuke134/anicca>
- **ソウル / 行動方針：** [`SOUL.md`](SOUL.md) ・ [`THESIS.md`](THESIS.md)

## ライセンス

MIT（[LICENSE](LICENSE) 参照）。
