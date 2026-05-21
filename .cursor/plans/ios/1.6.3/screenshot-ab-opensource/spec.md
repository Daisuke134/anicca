# screenshot-ab オープンソース化 スペック

## 開発環境

| 項目 | 値 |
|------|-----|
| **作業ブランチ** | `dev` |
| **スペックパス** | `.cursor/plans/ios/1.6.3/screenshot-ab-opensource/spec.md` |
| **作業状態** | 設計中 |

---

## 1. 概要（What & Why）

### What

`screenshot-ab` を独立した GitHub リポジトリとして公開する。
App Store スクリーンショット A/B テストを自動化するスキルで、OpenClaw（primary）と Claude Code の両方で動作する。

### Why

- スクリーンショット A/B テストをやっている iOS 開発者は多いが、自動化ツールが存在しない
- Pencil MCP + ASC CLI + RevenueCat の組み合わせは独自の価値がある
- OpenClaw コミュニティへの貢献、X Japanese (aniccaxxx) でのビルドインパブリック

### ポスト先

X アカウント: **aniccaxxx**（日本語）

---

## 2. 受け入れ条件

| # | 条件 | 検証方法 |
|---|------|---------|
| 1 | 別 GitHub リポジトリが存在し、README がある | `gh repo view Daisuke134/screenshot-ab` が成功 |
| 2 | OpenClaw で `screenshot-ab` スキルが動作する | Mac Mini で `openclaw agent --message "screenshot-ab run"` 実行 → フェーズ選択〜完了メッセージまで到達 + exit code 0 |
| 3 | Claude Code でも動作する（手動実行） | `screenshot-ab run` → フェーズ選択画面表示 → CVR分析完了メッセージ到達 |
| 4 | 毎朝 5:00 JST に自動実行され Slack に結果が届く | Mac Mini の cron 実行後ログ（`/Users/anicca/.openclaw/workspace/screenshot-ab/logs/`）に SUCCESS 記録 + Slack チャンネルへのメッセージ着信確認 |
| 5 | ASC 実験開始は「手動のみ」と README に明記されている | README に「⚠️ Start Test は手動のみ（Apple Review 必須）」の記述あり |
| 6 | 実験開始要求時にガードが発火し警告出力 + exit code 非0 で中断（`asc product-pages experiments start` 未実行） | `ASC_BIN=./test/stub-asc.sh node scripts/report.js --force-start 2>&1` の出力に `GUARD: experiment start blocked` が含まれ、exit code 非0かつ `test/asc-calls.log` に `experiments start` の記録が0行 |
| 7 | screenshot-creator / visual-qa / slack-approval / gh CLI / twitter-automation の依存関係がセットアップ手順に書かれている | README の「## Setup」セクション目視確認 |
| 8 | README にコピペ用セットアップ・プロンプトが掲載されている | README の「## Quick Start (Copy & Paste)」セクションあり |
| 9 | X (aniccaxxx) に日本語で投稿され、GitHub リンクが含まれている | ツイート URL 確認 |

---

## 3. As-Is / To-Be

### As-Is（現状）

| 項目 | 現状 |
|------|------|
| スキル場所 | `Daisuke134/anicca-products` の `.cursor/skills/screenshot-ab/` |
| 利用環境 | Anicca プロジェクト内のみ |
| 公開状況 | 非公開（private repo） |
| ドキュメント | SKILL.md のみ（外部向けではない） |
| 依存関係の明示 | なし |

### To-Be（変更後）

| 項目 | To-Be |
|------|-------|
| スキル場所 | `Daisuke134/screenshot-ab` (public repo) |
| 利用環境 | OpenClaw (primary) + Claude Code |
| 公開状況 | **Public** |
| ドキュメント | README.md（外部向け） + SKILL.md |
| 依存関係の明示 | セットアップガイドに全依存を記載 |

### 新リポジトリ構造

```
screenshot-ab/
├── README.md                    ← 外部向けドキュメント（英語 + 日本語）
├── SKILL.md                     ← OpenClaw / Claude Code 共通スキル定義
├── references/
│   ├── pipeline.md              ← パイプライン詳細（既存）
│   ├── setup.md                 ← セットアップ手順（既存 + 更新）
│   ├── headline-gen.md          ← キャッチコピー生成ロジック（既存）
│   └── visual-qa.md             ← Visual QA ガイド（既存）
├── scripts/
│   └── daily-report.sh          ← cron 用ラッパースクリプト（新規）
└── examples/
    ├── openclaw-cron.json        ← OpenClaw cron 設定例（新規）
    └── experiment-result.json   ← 出力例（新規）
```

---

## 4. 機能仕様

### 4.1 日次自動実行フロー（OpenClaw cron — primary）

```
毎朝 5:00 JST
    ↓
[PHASE 1] ASC から実験ステータス取得
    - asc product-pages experiments list
    - 実験が「Running」か確認
    ↓
[PHASE 2] RevenueCat から CVR データ取得（7日間）
    - Offering A vs B のトライアル開始率比較
    ↓
[PHASE 3] 判定
    - CVR 差異 > 5% かつ 統計的有意 → 勝者を Slack 報告
    - CVR 差異 ≤ 5% → 継続報告
    - 実験が「Paused/Ended」→ 手動確認を Slack に通知
    ↓
[PHASE 4] 新スクリーンショット生成（オプション: 週1回）
    - screenshot-creator スキルを呼び出し
    - Pencil MCP で新デザイン生成
    - visual-qa スキルで品質確認
    ↓
[PHASE 5] Slack 報告（slack-approval で承認フロー）
    - 新スクリーンショット候補を見せる
    - ✅ 承認 → asc screenshots upload（自動）
    - ❌ 却下 → そのまま終了
```

### 4.2 ASC 実験に関する絶対制約

**ASC 実験の開始は Claude/エージェントがプログラムで実行することは不可能。**

| 操作 | 自動化可否 | 理由 |
|------|-----------|------|
| 実験作成 | ✅ 可 | `asc product-pages experiments create` |
| スクリーンショット設定 | ✅ 可 | `asc screenshots upload` |
| **実験開始** | **❌ 不可** | Apple Review 必須 → その後 ASC Web UI で "Start Test" を手動クリック |
| 実験停止 | ✅ 可（要確認） | `asc product-pages experiments update --stopped` |
| ステータス取得 | ✅ 可 | `asc product-pages experiments list` |
| 結果取得 | ✅ 可 | ASC Analytics |

**README にこの制約を必ず明記する。**

### 4.3 Claude Code 手動実行フロー

```
ユーザー: "screenshot-ab run"
    ↓
SKILL.md が読み込まれる
    ↓
インタラクティブに各フェーズを選択
- [1] 実験ステータス確認のみ
- [2] CVR データ取得 + 分析
- [3] 新スクリーンショット生成
- [4] フルパイプライン
```

---

## 5. 依存関係（セットアップで必須）

| 依存 | 種別 | インストール方法 | 確認コマンド | 用途 |
|------|------|----------------|------------|------|
| **OpenClaw** | Runtime | `npm install -g openclaw` | `openclaw --version` | primary 実行環境 |
| **Pencil app** | macOS app | Mac App Store | アプリ起動確認 | スクリーンショットデザイン |
| **Pencil MCP 接続** | MCP設定 | Pencil 起動 → Settings → Enable MCP → `mcp__pencil__get_editor_state` | `mcp__pencil__get_editor_state` 成功 | .pen ファイル操作 |
| **`asc` CLI** | CLI | `brew tap rudrankriyam/tap && brew install asc` | `asc --version` | App Store Connect 操作 |
| **`gh` CLI** | CLI | `brew install gh && gh auth login` | `gh auth status` | GitHub リポジトリ管理 |
| **`screenshot-creator` skill** | Skill | `skills/screenshot-creator/SKILL.md`（同梱） | SKILL.md 存在確認 | Pencil MCP ラッパー |
| **`visual-qa` skill** | Skill | `skills/visual-qa/SKILL.md`（同梱） | SKILL.md 存在確認 | スクリーンショット品質確認 |
| **`slack-approval` skill** | Skill | `npx skills install slack-approval` | SKILL.md 存在確認 | Slack 承認フロー |
| **`twitter-automation` skill** | Skill | `npx skills install twitter-automation` | SKILL.md 存在確認 | X 投稿自動化 |
| **RevenueCat MCP** | MCP | `openclaw mcp add revenuecat` | `mcp__revenuecat__mcp_RC_list_apps` 成功 | CVR データ取得 |
| **ASC MCP** | MCP | `openclaw mcp add app-store-connect` | `mcp__app-store-connect__list_apps` 成功 | 実験ステータス取得 |

### 同梱するスキル（リポジトリ内 `skills/` ディレクトリ）

| スキル | 同梱方法 |
|--------|---------|
| `screenshot-creator` | `skills/screenshot-creator/SKILL.md` としてコピー同梱 |
| `visual-qa` | `skills/visual-qa/SKILL.md` としてコピー同梱 |
| `slack-approval` | README に別途インストール手順を記載（同梱しない） |

---

## 6. テストマトリックス

| # | To-Be | テスト名 | 対象ファイル | 実行コマンド | 期待アサーション |
|---|-------|----------|------------|------------|----------------|
| 1 | ASC 実験ステータス取得 | `test_fetch_experiment_status` | `scripts/report.js` | `node scripts/report.js --dry-run 2>&1` | 出力に `experiment_status:` キーが含まれる |
| 2 | CVR 差異計算（小数→%整数） | `test_cvr_diff_calculation` | `scripts/analyze.js` | `node -e "const a=require('./scripts/analyze'); console.log(a.calcDiff(0.10,0.16))"` | 出力が `6`（%差の整数値のみ） |
| 3 | 勝者判定ロジック（差異>5%で winner 確定） | `test_winner_detection` | `scripts/analyze.js` | `node -e "const a=require('./scripts/analyze'); console.log(JSON.stringify(a.detectWinner({a:0.10,b:0.16,minDiff:5})))"` | `{"winner":"b","diff":6,"confident":true}` |
| 4 | Slack 報告フォーマット | `test_slack_report_format` | `scripts/slack.js` | `node -e "const s=require('./scripts/slack'); console.log(JSON.stringify(s.buildReport({winner:'b',diff:6})))"` | `blocks` キーが存在し、`winner` テキストを含む |
| 5 | ASC 実験開始ガード（警告出力+非0終了+asc start未実行） | `test_no_experiment_start_command` | `scripts/report.js` + `test/stub-asc.sh` | `ASC_BIN=./test/stub-asc.sh node scripts/report.js --force-start 2>&1` | 出力に `GUARD: experiment start blocked` が含まれ、exit code 非0かつ `test/asc-calls.log` に `experiments start` が0行 |
| 6 | cron 設定ファイルの正確性 | `test_cron_json_schema` | `examples/openclaw-cron.json` | `node -e "const c=require('./examples/openclaw-cron.json'); if(!c.schedule)throw new Error('missing schedule')"` | exit code 0 |

---

## 7. 境界（やらないこと）

| やらないこと | 理由 |
|-------------|------|
| ASC 実験の自動開始 | Apple Review 必須のため技術的に不可能。ガードで警告出力して処理中断する |
| 初期版の汎用化（README 以外） | 初期版は Anicca のデフォルト値を提供する。`.env` による設定変数化で他アプリ適用可能だが、コア以外のアプリ固有ロジックには対応しない |
| Web ダッシュボード作成 | Slack 報告で十分 |
| CI/CD への組み込み | cron で十分 |
| anicca-products からのコード削除 | 既存 Anicca は引き続き使用 |

---

## 8. 実行手順

### フェーズ 1: リポジトリ作成

```bash
# 新リポジトリを GitHub に作成
gh repo create Daisuke134/screenshot-ab --public --description "App Store screenshot A/B testing automation for OpenClaw & Claude Code"

# ローカルにクローン
cd ~/Downloads
git clone https://github.com/Daisuke134/screenshot-ab.git
cd screenshot-ab
```

### フェーズ 2: ファイルコピー & 更新

```bash
# Anicca プロジェクトからスキルをコピー
ANICCA=~/Downloads/anicca-project

cp $ANICCA/.cursor/skills/screenshot-ab/SKILL.md ./SKILL.md
cp -r $ANICCA/.cursor/skills/screenshot-ab/references/ ./references/

# screenshot-creator と visual-qa もコピー
mkdir -p skills/screenshot-creator skills/visual-qa
cp $ANICCA/.cursor/skills/screenshot-creator/SKILL.md ./skills/screenshot-creator/SKILL.md
cp $ANICCA/.claude/skills/visual-qa/SKILL.md ./skills/visual-qa/SKILL.md
```

### フェーズ 3: README 作成

`README.md` を日英バイリンガルで作成（詳細は references/setup.md を参照）

### フェーズ 4: cron 設定例の作成

`examples/openclaw-cron.json` に 5:00 JST 実行の cron 設定例を作成

### フェーズ 5: X 投稿（aniccaxxx）— 詳細仕様

#### ツイート本文（日本語、280文字以内）

```
App StoreのABスクリーンショットテスト、面倒でやってないでしょ？

ASC CLIとClaude Codeでスキル作りました。

下のプロンプトをClaude Code（またはOpenClaw）にコピペするだけ。
セットアップ完了したら「screenshot-ab run」と言うだけで
・実験ステータス確認
・CVR比較
・新スクリーンショット生成
・Slack報告

全部やってくれます。

👇コピペ用プロンプト
[GitHub README リンク]
```

#### コピペ用セットアップ・プロンプト（README に掲載）

README の冒頭に以下のプロンプトを掲載する。ユーザーはこれを Claude Code または OpenClaw にそのまま貼り付けるだけでセットアップが完了する。

```
以下を実行してください：

1. https://github.com/Daisuke134/screenshot-ab からリポジトリをクローンして、SKILL.md をプロジェクトルートにインストールしてください。
2. references/setup.md を読んで、必要な依存（asc CLI, RevenueCat MCP, ASC MCP, slack-approval）をインストールしてください。
3. .env に以下を設定してください：
   - APP_BUNDLE_ID=（あなたのアプリのBundle ID）
   - RC_PROJECT_ID=（RevenueCat Project ID）
   - ASC_APP_ID=（App Store Connect App ID）
   - SLACK_CHANNEL=（Slack チャンネルID）
4. セットアップが完了したら「完了しました」と報告してください。

セットアップ完了後は「screenshot-ab run」と言うだけで実験ステータス確認・CVR分析・レポートが自動で届きます。
```

#### ポスト要件

| 項目 | 内容 |
|------|------|
| アカウント | aniccaxxx |
| 言語 | 日本語 |
| タイミング | GitHub push 完了直後 |
| 文字数 | 280文字以内 |
| リンク | GitHub README（コピペプロンプト掲載ページ） |
| twitter-automation スキル | 投稿に使用 |

---

## 9. E2E 判定

| 項目 | 値 |
|------|-----|
| UI 変更 | なし（スキル/ドキュメントのみ） |
| 新画面 | なし |
| 結論 | Maestro E2E 不要（スキルのドキュメント化作業のため） |

---

## 10. 実装順序

| # | タスク | 完了基準 |
|---|--------|---------|
| 1 | GitHub リポジトリ作成 | `gh repo view Daisuke134/screenshot-ab` が成功 |
| 2 | 既存スキルファイルをコピー | `SKILL.md` と `references/` が存在 |
| 3 | screenshot-creator / visual-qa を `skills/` に同梱 | `skills/*/SKILL.md` が存在 |
| 4 | SKILL.md を外部向けに更新（Anicca 固有設定を `.env` 変数化） | `APP_BUNDLE_ID`, `RC_PROJECT_ID`, `ASC_APP_ID`, `SLACK_CHANNEL` が設定可能 |
| 5 | `scripts/report.js` + `scripts/analyze.js` + `scripts/slack.js` + `scripts/run-tests.js` 作成 | 各ファイルが存在 |
| 6 | Section 6 テスト全件実行 & pass 確認 | `node scripts/run-tests.js` exit code 0 |
| 7 | `scripts/daily-report.sh` 作成（cron ラッパー） | `bash scripts/daily-report.sh --dry-run` exit code 0 |
| 8 | `examples/openclaw-cron.json` 作成 | `node -e "require('./examples/openclaw-cron.json')"` exit code 0 |
| 9 | `examples/experiment-result.json` 作成（出力例） | JSON バリデーション pass |
| 10 | README.md 作成（日英）+ コピペプロンプト掲載 | 「## Quick Start (Copy & Paste)」セクションあり + ASC制約の警告あり |
| 11 | 初回コミット & push | `git push origin main` 成功 |
| 12 | X (aniccaxxx) に日本語で投稿（twitter-automation スキル使用） | ツイート URL 確認 |

---

最終更新: 2026-02-24
