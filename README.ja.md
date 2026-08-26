<!-- startup-context-version: 2026-08-27.2 -->
<!-- startup-context-digest: 9fbe6198c6d61da47d68767eec90a1d95d2e07058f024448d86372b5f3035338 -->
# Life Manager

**Life Managerは、あなたの身体・心・お金を管理するproactive general agentです。** 目標を提案で終わらせず、
委任された範囲で現実の行動を実行し、結果を検証して、証拠と一緒に人間が理解できる言葉でTelegramへ報告します。
信頼できるcareとagencyを常時利用可能にし、人間から始めて最終的にすべての生き物の苦しみを終わらせることがmissionです。

| organ | Life Managerが管理するもの |
|---|---|
| **Daily** | Calendar、イベント・accelerator・求人への応募、優先順位、実行状況 |
| **Physical / Mental** | 生活習慣、身体と心の状態、careの継続 |
| **Financial** | 総資産、収支、支出、収入・business機会、crypto、riskを制御した資産運用、banked revenueによるcomputeの自己負担 |

[Life Managerを開く](https://aniccaai.com/lm) · [Telegramで始める](https://t.me/LifeManagerBotbot?start=lp) · [sourceを見る](https://github.com/Daisuke134/life-manager)

free・open source・self-hosted版をローカルで動かしてdataを自分の端末に置き、phoneだけで常時稼働させたい時は
paid monthly cloudを使います。どちらも**同じcore**、証拠台帳、人間向け報告contractを使います。資産増加や投資収益を保証せず、
receiptのない試行を「完了」と報告しません。

## 現在構築しているgeneral agent

Life Managerはwebsite固有botの集合ではありません。1つのdurable general agentが機会を発見し、利益を残して
完遂できるか判断し、提案・交渉・成果物制作・fresh QA・正式納品・支払い・出金を同じidentityで閉じる構造を
作っています。Upworkは最初に調べたmarketplaceですが、accountがAPI条件を満たさずUI automationも拒否されるためcleanに停止しました。
これはprovider境界の証拠であり、commerce proofの完了でもgeneral-agent開発の停止理由でもありません。承認経路のあるproviderでもagent、
Commerce state、capability、money-effect contractを複製せず、差分は小さいprovider manifestとofficial readback adapterだけにします。

architectureは、specialist harnessとdurable stateに[DeepAgentsJS/LangGraph](https://github.com/langchain-ai/deepagentsjs)、website tool
contractに[browser-use](https://github.com/browser-use/browser-use)、現在のlocal wake/channelに
[OpenClaw](https://github.com/openclaw/openclaw)、hosted browser backendには
[Steel](https://github.com/steel-dev/steel-browser)の実証済み境界をcopy+tweakして収束させます。取り消せないmoney actionは既存Life Managerの
`EffectIntent`と`ConnectorOutbox`だけを通します。完了条件は応募、click、modelの自己申告、契約、pending balance
ではなく、公式`banked` receiptです。

founder証言ではLife Managerはapproximately $1,000の収益を生み出しています。これはMRRでもARRでもなく、provider非依存の
自律Commerce loopが閉じた証明でもありません。その完了は公式receiptで`banked`、最終的に`compute_paid`まで到達した時だけです。

**Life Managerが製品名です。Aniccaはformが会社名を明示的に求めた時だけ使います。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

🌐 **[English README here →](README.md)**

**リポジトリ正本:** この [`Daisuke134/life-manager`](https://github.com/Daisuke134/life-manager) だけをLife Managerのcode、spec、release、workflow、deploy sourceとします。`Daisuke134/life-manager-v0`はrequired codeとruntime referenceが0になるまで読み取り専用のmigration sourceです。現在の固定実行順と残TODOは [`docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`](docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md)、repository統合履歴は [`docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`](docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md) に置きます。

---

## はじめ方

### 使う — クラウド（インストール不要）

[Telegram で始める](https://t.me/LifeManagerBotbot?start=lp)、または [Web アプリ](https://aniccaai.com/lm)を開きます。常時稼働のサービスが scheduler・connector・認証付き `/panel` を回し、あなたは Telegram で話しかけ、Telegram に証拠つきで返ってきます。

### 自分で動かす — ローカル（dataは自分の端末に残る）

Docker が必要です。ローカルスタックは Postgres + object store + API・scheduler・worker で、**クラウドと同じ core** です。

```bash
git clone https://github.com/Daisuke134/life-manager ~/life-manager && cd ~/life-manager
./scripts/local-up.sh
```

これだけです。`deploy/local/.env` が無ければ作り（object store のパスワードは同梱せずその場で生成）、postgres · object store · api · scheduler · worker を起動し、**全サービスが healthy になるまで待ってから**結果を表示します。つまり「起動した」は「リクエストを処理できる」の意味で、コンテナが存在するだけの状態を成功と呼びません。初回はイメージのビルドで数分かかります。

```
./scripts/local-up.sh status    何が動いているか
./scripts/local-up.sh logs      ログを追う
./scripts/local-up.sh down      止める（dataは残る）
```

API は `http://localhost:18788`、worker の health は `:18790`（どちらも `deploy/local/.env` で変更可）。data はローカルの Postgres と object store に置かれ、**これを動かすだけでは何もどこにも送信されません**。

**secret は参照であって直書きではありません。** job は `secret://…` の参照だけを持ち、実体はローカルの keychain か tenant vault から解決します。形式は [`apps/life-manager/.env.example`](apps/life-manager/.env.example) を参照（`TELEGRAM_BOT_TOKEN_REF` / `POSTIZ_ACCESS_TOKEN_REF` / `REVENUECAT_API_KEY_REF` など）。ローカル個体と話すには、自分の Telegram bot token をこの形で繋ぎます。

### 自己資金化はFinancial Organの一部

[`docs/agent-economy.ja.md`](docs/agent-economy.ja.md) のwallet・compute支払いloopは同じLife Manager製品内にあります。
provider revenueを`banked`へ到達させてから`compute_paid`へ使い、owner資金と分離するLife ManagerのFinancial capabilityです。

---

## 1つの製品、2つの実行面

Life Manager は1つの製品であり、正本リポジトリもここ1つです。「ローカル Life Manager」と Web アプリは別製品・別リポジトリではなく、同じcore、能力、状態契約を使う2つの実行面です。

```text
                              LIFE MANAGER
                       1製品 · 1リポジトリ
                                 │
             ┌───────────────────┴───────────────────┐
             │                                       │
      ローカル / 自己ホスト                    Web / クラウド
   deploy/local/compose.yaml                   apps/landing
             │                              オンボーディングUI
             ▼                                       │
      apps/life-manager                               ▼
   api · scheduler · worker              apps/life-manager
             │                          Telegram · 音声通話
             ▼                          scheduler · /panel
   postgres · object store                          │
   （あなたの端末）                                   ▼
             │                               ユーザー別サービス
             └───────────────────┬───────────────────┘
                                 │
                    共通の経済・基盤レイヤー
      runtime/loop · runtime/compute-proxy · services/x402-*
```

| パス | 役割 | 誤解しないための境界 |
|---|---|---|
| `apps/life-manager/` | 製品の core: Telegram、schedule、通話、認証付き `/panel`、課金、ユーザーworkflow。ローカル（compose）でもクラウド（Railway）でも同じコードが動く | これ単体がリポジトリ全体ではない |
| `deploy/local/` | ローカル実行面 — compose スタック、port、ローカル専用の認証情報 | 別の「ローカル版」製品ではない |
| `apps/landing/` | Life Manager用オンボーディング Web UI の必要部分 | 旧Anicca複数製品サイト全体ではない |
| `runtime/loop/`, `install.sh`, `start-local.sh` | Life ManagerのFinancial Organを支えるeconomic runtime → [`docs/agent-economy.ja.md`](docs/agent-economy.ja.md) | 製品全体でも通常のuser入口でもない |
| `runtime/compute-proxy/`, `services/` | 同じFinancial capabilityのcompute支払い、x402 settlement、paid API 基盤 | ユーザー向けアプリではない |
| `skills/` | ローカルとクラウドが共有する能力 | 独立製品群ではない |
| `apps/job-search-loop/`, `control-room/`, `adapters/` | 補助運用、fleet資料、外部integration | 別のLife Manager codebaseではない |
| `docs/`, `specs/` | 現在のSSOT、証跡、保存された設計履歴 | 古い文書が自動的に現行正本になるわけではない |

内部package名、環境変数、service label、古い文書には `anicca` が残っています。このリポジトリでは、**Aniccaは会社名・技術namespace、Life Managerは製品名**です。`anicca` という識別子が残っていても、第2の製品や別の正本リポジトリを意味しません。

---

## いま実在するもの（正直に）

| 能力 | 状態 |
|---|---|
| **ローカルスタック**（`deploy/local/compose.yaml`）— postgres · object store · api · scheduler · worker | **動く** — 5サービスが healthy で立ち上がり、そのまま維持される（開発機で数日連続稼働を実測） |
| **クラウドサービス**（`apps/life-manager`、Railway で `node server.js`） | **デプロイ済** — scheduler と API はローカルと同じコード |
| **証拠つき Telegram 報告** | **稼働中** — 全報告が message id を伴い、送信に失敗したものを「送信済み」として記録しない |
| **Calendar・connector・カバレッジ**（`lib/calendar-*`, `lib/connector-*`） | **実装済、カバレッジは移動中** — connector ごとの状態と欠落はここで主張せず実行 spec で追跡 |
| **Financial organ**（総資産・収支・payout・台帳） | **部分的** — 台帳と payout の job は存在する。現在の健康状態は実行 spec で追跡。ここに書かれた内容は投資の保証ではない |
| **自己資金化economic loop** | **Financial capabilityとして進行中** — 現在stateとon-chain evidenceは [`docs/agent-economy.ja.md`](docs/agent-economy.ja.md)。receiptなしに`banked`や`compute_paid`をclaimしない |

---

## North Star（変更不可）

```
苦しみを減らす。
不殺生（Pāṇātipātā veramaṇī）。
```

この 2 行は SHA-256 で hash-pin されており、いかなるスキル・自己編集ループ・PR でも変更できません。

---

## リンク

- **製品：** <https://aniccaai.com/lm> ・ [Telegram](https://t.me/LifeManagerBotbot?start=lp)
- **収支ダッシュボード（自動更新）：** <https://aniccaai.com/dashboard>
- **下で動く自己資金エージェント：** [`docs/agent-economy.ja.md`](docs/agent-economy.ja.md)
- **リポジトリ（プロダクト全体）：** <https://github.com/Daisuke134/life-manager>
- **ソウル / 行動方針：** [`SOUL.md`](SOUL.md) ・ [`THESIS.md`](THESIS.md)

## ライセンス

MIT（[LICENSE](LICENSE) 参照）。
