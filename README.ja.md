# Life Manager

**Life Manager は製品、リポジトリ、AI、エージェント、ミッションの名前です。Anicca は会社名としてのみ使います。** Life Manager は自分の計算資源を自分で払い、人間の介入なしに USDC を稼ぎ、この世から苦しみを減らすために働きます。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-aniccaai.com%2Fdashboard-c8302e)](https://aniccaai.com/dashboard)

🌐 **[English README here →](README.md)**

**リポジトリ正本:** この [`Daisuke134/life-manager`](https://github.com/Daisuke134/life-manager) だけをLife Managerのcode、spec、release、workflow、deploy sourceとします。`Daisuke134/life-manager-v0`はrequired codeとruntime referenceが0になるまで読み取り専用のmigration sourceです。mission、repo境界、実行順、残TODOのlive SSOTは [`docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`](docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md) です。

> Life Manager は自律エージェントです。動かすマシン（住処）を 1 台渡すと起動し、自分の行動ログを監視してエラーを自己修正し、自分の計算資源を払うために USDC を稼ぎ、自己増殖し、起動するたびと 1 日 1 回あなたへ報告します。北極星は「苦しみを減らすこと」、人間の介入はゼロを目指します。

---

## 1つの製品、2つの実行面

Life Manager は1つの製品であり、正本リポジトリもここ1つです。「ローカル Life Manager」と Web アプリは別製品・別リポジトリではなく、共通の能力と状態契約を使う2つの実行面です。

```text
                              LIFE MANAGER
                       1製品 · 1リポジトリ
                                 │
             ┌───────────────────┴───────────────────┐
             │                                       │
      ローカル / 自己ホスト                    Web / クラウド
          install.sh                            apps/landing
             │                              オンボーディングUI
             ▼                                       │
        runtime/loop                                  ▼
      思考 → 実行 → 台帳                     apps/life-manager
             │                          Telegram · 音声通話 · scheduler
             ▼                                  認証付き /panel
          skills/*                                    │
      稼ぐ · 自己改善 · 報告                           ▼
             │                               ユーザー別サービス
             └───────────────────┬───────────────────┘
                                 │
                    共通の経済・基盤レイヤー
        runtime/compute-proxy · services/x402-* · dashboard
```

| パス | 役割 | 誤解しないための境界 |
|---|---|---|
| `runtime/loop/`, `install.sh`, `start-local.sh` | ローカル自律エージェントと自己ホスト runtime | 別の「ローカル版」製品ではない |
| `apps/life-manager/` | Telegram、schedule、通話、認証付き `/panel`、課金、ユーザーworkflowを持つ常時稼働クラウドサービス | これ単体がリポジトリ全体ではない |
| `apps/landing/` | Life Manager用オンボーディング Web UI の必要部分 | 旧Anicca複数製品サイト全体ではない |
| `runtime/compute-proxy/`, `services/` | 自己決済推論、x402 settlement、paid API 基盤 | ユーザー向けアプリではない |
| `skills/` | ローカルとクラウドが共有する能力 | 独立製品群ではない |
| `apps/job-search-loop/`, `control-room/`, `adapters/` | 補助運用、fleet資料、外部integration | 別のLife Manager codebaseではない |
| `docs/`, `specs/` | 現在のSSOT、証跡、保存された設計履歴 | 古い文書が自動的に現行正本になるわけではない |

内部package名、環境変数、service label、古い文書には `anicca` が残っています。このリポジトリでは、**Aniccaは会社名・技術namespace、Life Managerは製品名**です。`anicca` という識別子が残っていても、第2の製品や別の正本リポジトリを意味しません。

---

## Life Managerとは

5 つの性質で設計されています（詳細は [`THESIS.md`](THESIS.md)）。

| | |
|---|---|
| **仏教的（Buddhist）** | 苦しみを減らすために存在する。北極星は SHA-256 で固定され、変更不可 |
| **自己資金（Self-funding）** | 自分の USDC 財布から自分の計算資源（食料）を払う。人間の API キーは不要 |
| **自己増殖（Self-replicating）** | それぞれ独自の財布とアイデンティティを持つ子個体を生み出せる |
| **自己改善（Self-improving）** | 自分のログを監視 → エラー修正・リファクタ・目標に向けた改善を繰り返す |
| **人間の介入なし（No human in the loop）** | 自分で稼ぎ、報告し、行動する。残る唯一の人間の手は、自前サーバー（shelter）が実現するまでのサーバー代のみ |

旧アーキテクチャ資料は [`specs/`](specs/) に履歴として残します。現在の判断と残TODOは上記live SSOTだけを更新します。Life Manager はプロダクト全体と唯一の公開作業場所を統合し、自律的に稼ぐ力を financial organ として含みます。

---

## Life Managerの動かし方（ローカル自己ホスト・無料・サーバー鍵も API キーも不要）

Life Managerは **自分の**計算資源を、自分の財布から USDC で推論ごとに x402 決済（BlockRun / ClawRouter）して払います。人間の API キーは不要。あなたが渡すのは動かす端末（住処）だけで、食料（推論）は自分で買います。財布が空なら **無料モデル（$0）**、USDC が入れば frontier モデルも使えます。

```bash
git clone https://github.com/Daisuke134/life-manager ~/life-manager && cd ~/life-manager
./install.sh                                    # runtime root + スキルスロット同期、自前 wallet 生成
cd runtime/compute-proxy && npm install && cd -  # 一度だけ（@blockrun/llm + viem）
./start-local.sh node runtime/loop/index.mjs    # 自己決済プロキシ + Life Managerのループを起動
```

これで 2 つが起動します。(1) `http://127.0.0.1:8402/v1` の OpenAI 互換 **自己決済コンピュートプロキシ**（自前 wallet＝自動生成・人間の鍵では決してない、から毎推論を USDC で自己決済）と、(2) **Life Managerのループ**（[`runtime/loop/`](runtime/loop/)＝think → act → observe → persist の ReAct ループ＋heartbeat）。ループは毎 wake、ClawRouter の **`auto`** ルーター（モデルをハードコードせず、ClawRouter がツール呼び出しを検知して tool-calling 可能なモデルへ自動ルート＋wallet から課金）でプロキシに問い合わせ、ツール（例：`earn` スキル）を選んで実行し、`$ANICCA_HOME/state/ledger.jsonl` に 1 行追記します。wallet が空なら **無料モデル（$0）**、USDC を送れば frontier モデル。

`install.sh` の runtime 既定値は `${XDG_STATE_HOME:-$HOME/.local/state}/life-manager`
です。複数 instance は `LIFE_MANAGER_HOME=/任意のruntime` で分離できます。container・CI・
foreground 実行では `LIFE_MANAGER_INSTALL_DAEMON=0` を指定すると、lockfile 固定の依存と
同じ runtime body を導入しつつ LaunchAgent / system service を変更しません。

> 別の頭脳を使いたい場合は `ANICCA_BRAIN=claude-p` で同じループを Claude Code（`claude -p`、例：Sonnet）で駆動できます（既存ハーネスの上でLife Managerを動かす用途）。既定は `proxy`（自己資金の道）。他の OpenAI 互換ループも `OPENAI_BASE_URL` に向ければ動きます。

Life Managerが実行する各能力は [`skills/registry.json`](skills/registry.json) にスロットとして宣言され、`install.sh` が `~/.anicca/skills/` に同期します。予約済みスロットを有効化するには、実装をそのディレクトリに置いて `status` を `live` にするだけ（`install.sh` の編集は不要）。

---

## 何に足を踏み入れるのか — human-funded と self-funded、具体的に

起動する前に、あなたのサブスク/財布が何に使われるかを正確に知っておくべきです。全loopの台帳(どこにあり、
生死確認の仕方)は **[`docs/EARN_LOOPS.md`](docs/EARN_LOOPS.md)**（英語）を参照。

```
~/anicca/skills/earn/
├── clip/        ← IG per-view クリップ(長尺動画→9:16切抜→字幕→投稿)
├── affiliate/   ← Amazon アソシエイトのスライドショー
├── video/       ← faceless動画のライフサイクル(作成→ウォームアップ→投稿)
├── bounty/      ← Algora GitHub bounty(Issue発見→修正→マージ)
├── gig/         ← ココナラ案件(発見→応募→納品)
└── run.sh       ← self-funded共通入口: yield / hl_trade / x402_sell / token_launch
```

**human-funded で起動する(`ANICCA_BRAIN=claude-p`、あなたのClaude Codeサブスクで駆動)場合:**
5本の独立したtmuxループが動き、それぞれ決まった時間・決まった通貨で稼ぎます:

```
anicca-clip-core       (毎時)        → USDC、IG per-view報酬
anicca-affiliate-core  (毎日08:41)   → ¥、Amazonアソシエイト報酬
anicca-video-core      (4時間毎)     → USDC、faceless動画アカウント
anicca-bounty-core     (毎日09:29)   → USD、マージされたGitHub bountyのPR
anicca-gig-core        (毎時)        → ¥、ココナラ報酬(法定通貨、人間の銀行口座着金)
```
判断は行いません — 決まったスケジュールを回すだけ。安価で予測可能ですが、この5本の
レールが生む分にしか稼げません(上記の「銀行口座」は明示的に差し替えない限りDaisのものです)。

**self-funded で起動する(既定 `ANICCA_BRAIN=proxy`/ClawRouter、自分のwallet+無料モデルで駆動)場合:**
120秒毎に起きて「次に何をするか」を自分で判断する daemon が1本動きます:

```
1 wake → LLM が次のうち1つを選ぶ: hl_trade | x402_sell | token_launch | yield | cook |
                                    self/issue-dev | earn/clip | earn/video | earn/gig | earn/bounty
        (上のhuman-fundedループと全く同じコードを、固定スケジュールでなく判断で呼ぶ)
```
より自律的で、より不安定 — 学習前に取引で損をすることもありますが、cronの時報を待たない分
複利も速く効きます。両者は`skills/earn/`の全く同じコードを共有し、`ANICCA_INSTANCE`が
アカウント/wallet/ledgerの衝突だけを防いでいます。

---

## アーキテクチャ（一段落）

Life Managerは [Conway の automaton](https://github.com/Conway-Research/automaton) と同じ **automaton パターン**（ReAct ループ＝think → act → observe → persist ＋ heartbeat）で動きますが、**より簡素で別のスタック：ClawRouter（食＝推論・自己決済 x402）＋ 自分の Mac（ローカル）または Akash（クラウド）** の上で動き、Conway に依存しません。ループは [`runtime/loop/`](runtime/loop/) にあり、runtime root（`$ANICCA_HOME`）配下でスキルスロット群と 1 つの Base Smart Wallet とともに動きます。クラウド版では認証に **Supabase**、サービス接続に **Composio** を使います。

---

## いま実在するもの vs 開発中

| 能力 | 状態 |
|---|---|
| 自己決済コンピュートプロキシ（自前 wallet で free → frontier、x402） | **実装済・実証済**（`runtime/compute-proxy/`） |
| **Life Managerのループ**（`runtime/loop/`）＝wake → ClawRouter `auto` 頭脳 → スキル実行 → 台帳 → sleep | **実装済・稼働** — ClawRouter `auto` でツール呼び出しを end-to-end 発火（モデル非ハードコード）。68 テスト＋live wake 検証済 |
| 稼ぐ → オンチェーン検証 → 台帳記録（GATE-0） | **実装済** — DeFi 利回り入金（Aave/Morpho、USDC）をオンチェーン検証。earn スキルは「実際に稼げる手段」中心に最終調整中 |
| 自己増殖（`self/spawn`）/ 自己改善（`self/issue-dev`）/ UBI（`economy/ubi`） | **宣言済** — 機構は確定、稼ぎの後のロードマップ |
| クラウド個人ダッシュボード / Stripe サブスク / 自前サーバー（Akash） | **開発中** — `specs/00-MASTER.md` 参照 |

Life Managerのループは [`runtime/loop/`](runtime/loop/) に同梱されており、`./start-local.sh node runtime/loop/index.mjs` で起動します（上のローカル手順参照）。

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

- **収支ダッシュボード（自動更新）：** <https://aniccaai.com/dashboard>
- **リポジトリ（プロダクト全体）：** <https://github.com/Daisuke134/life-manager>
- **ソウル / 行動方針：** [`SOUL.md`](SOUL.md) ・ [`THESIS.md`](THESIS.md)

## ライセンス

MIT（[LICENSE](LICENSE) 参照）。
