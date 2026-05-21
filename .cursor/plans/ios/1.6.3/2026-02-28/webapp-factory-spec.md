# Web App Factory — 仕様書

**バージョン:** 1.5.0
**作成日:** 2026-03-01
**ステータス:** Ready to Implement

---

## 開発環境

| 項目 | 値 |
|------|-----|
| **実行環境** | Mac Mini（anicca-mac-mini-1 / Tailscale: 100.99.82.95） |
| **ブランチ** | `dev` |
| **リポジトリ** | `Daisuke134/anicca-products`（Public） |
| **スペックパス** | `.cursor/plans/ios/1.6.3/2026-02-28/webapp-factory-spec.md` |

---

## 1. 概要（What & Why）

### What
24時間365日自律稼働する Web App Factory。
人間の入力ゼロで、毎日1本のWebアプリを自動でトレンド調査→アイデア選定→ビルド→デプロイ→マーケティングまで完結させるシステム。

### Why
- Webアプリの固定費が月$20（Vercel Pro）まで下がった
- Claude Code の `--dangerously-skip-permissions` モードで完全自律ビルドが可能
- AppFactory website-pipeline v2.3.0（OSS）が8フェーズの品質ゲートを持つ
- Anicca（OpenClaw）が Mac Mini で24/7稼働中。OpenClaw `jobs.json` 直接編集で即日スケジュール追加可能
- `create-next-app` + Stripe/Supabase 手動統合でSaaS基盤が即日立ち上がる

ソース: [0xAxiom/AppFactory](https://github.com/0xAxiom/AppFactory) / 核心の引用: 「Agent-native system that turns market signals into validated app specs and buildable apps—with monetization, ASO, and launch strategy baked in.」
ソース: [Anthropic Engineering - Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) / 核心の引用: 「A two-fold solution: an initializer agent that sets up the environment on the first run, and a coding agent that is tasked with making incremental progress in every session while leaving clear artifacts for the next session.」
ソース: [Anthropic Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) / 核心の引用: 「Orchestrators direct agents to use tools or undertake tasks with the intention of completing some broader goal」

### アーキテクチャ
```
Anicca cron 09:00 JST（OpenClaw jobs.json 直接編集で設定）
  → source .openclaw/skills/webapp-factory-orchestrator/.env && claude --dangerously-skip-permissions -p "$(cat .openclaw/skills/webapp-factory-orchestrator/prompt.md)"
    → [横断] oh-my-claudecode @configure-notifications → Slack #metrics 進捗報告
    → LAYER 1: トレンド収集 + アイデア選定 → idea.md 生成
    → LAYER 2: ボイラープレート clone + AppFactory website-pipeline
    → LAYER 3: vercel-labs@vercel-deploy → URL 発行
    → LAYER 4: slack-webhook + Postiz X 投稿
```

---

## 2. 受け入れ条件

| # | 条件 | 検証方法 |
|---|------|---------|
| AC-1 | 毎日 09:00 JST に人間の入力なしで自動起動する | cron ログ確認 |
| AC-2 | LAYER 1 がトレンドデータを収集し `idea.md` を生成する | `idea.md` の存在と内容確認 |
| AC-3 | `idea.md` が Problem / Market / Target / Monetization / Competitors の5セクションを含む | ファイル内容確認 |
| AC-4 | AppFactory website-pipeline が `idea.md` を INPUT として受け取り仕様を自動展開する | Phase 0 ログ確認 |
| AC-5 | Phase 6 Skills Audit が react-best-practices ≥95% を達成する | ゲートログ確認 |
| AC-6 | Phase 7 SEO Review が PASS する | ゲートログ確認 |
| AC-7 | Phase 8 Ralph Polish Loop が 97%以上で PASS する | ゲートログ確認 |
| AC-8 | LOCAL_RUN_PROOF_GATE が `RUN_CERTIFICATE.json status:PASS` を発行する | ファイル確認 |
| AC-9 | Vercel に自動デプロイされ有効な URL が発行される | URL アクセス確認 |
| AC-10 | Slack #metrics に完成報告が自動投稿される | Slack 確認 |
| AC-11 | 全工程が人間の介入なしに完結する | ログに human_input なし |
| AC-12 | Postiz CLI 経由で X（Twitter）に完成投稿が自動公開される | X タイムライン確認 |

---

## 3. As-Is / To-Be

### As-Is（現状）
```
Anicca（Mac Mini）
├── trend-hunter cron（05:00, 17:00 JST）← トレンド収集
Web App Factory: 存在しない
```

### To-Be（完成後）
```
Anicca（Mac Mini）
├── trend-hunter cron（05:00, 17:00 JST）← 既存・変更なし
└── webapp-factory cron（09:00 JST）← NEW（OpenClaw jobs.json 直接編集で追加）
    方法: `.openclaw/cron/jobs.json` に新エントリ追加（既存エントリは変更しない）

webapp-factory フロー:

[横断] oh-my-claudecode @configure-notifications（全ステップ常時稼働）
  OMC_SLACK_WEBHOOK_URL を読み session イベントを Slack #metrics にリアルタイム投稿
  ソース: yeachan-heo/oh-my-claudecode@configure-notifications
          「Configure Slack notifications via OMC_SLACK_WEBHOOK_URL」

LAYER 1: INTELLIGENCE（09:00〜10:00）
  使用スキル（全て既存）:
  ├── apify-ultimate-scraper     Webトレンド収集（Apify $49/月）
  ├── content-trend-researcher   SNS 10プラットフォーム分析
  ├── google-trends              検索ボリューム確認
  ├── reddit-insights            pain points 発見
  └── startup-idea-validation    市場規模・競合スコアリング + ニッチ選定
  出力: /tmp/webapp-factory/{date}/idea.md
        （Problem / Market / Target / Monetization / Competitors）

LAYER 2: BUILD（10:00〜14:00）
  Step 0: ボイラープレート取得
    npx create-next-app@latest {slug}/ --typescript --tailwind --eslint --app --src-dir
    （Next.js 15 + TypeScript + Tailwind v4 — 公式テンプレート）
    Stripe + Supabase は手動統合（appfactory-builder Phase 5 で自動実行）
    ソース: https://nextjs.org/docs/getting-started/installation
            「The easiest way to get started with Next.js is by using create-next-app」
    注: vercel/nextjs-subscription-payments は 2025-01 にアーカイブ済みのため使用しない

  Step 1: appfactory-builder が idea.md を INPUT に Phase 0〜8 を自動実行
    Phase 0: Intent Normalization（idea.md → 完全仕様に自動展開）
    Phase 1: Dream Spec（12セクション自動生成）
    Phase 2: Research & Positioning
    Phase 3: Information Architecture
    Phase 4: Design System（Axiom: #0a0a0a / Inter + JetBrains Mono）
    Phase 5: Build（Next.js 15 + TypeScript + Tailwind v4 + shadcn/ui + Framer Motion）
             使用スキル: app-builder, senior-frontend, nextjs-expert
    Phase 6: GATE — Skills Audit（react-best-practices ≥95%, web-design-guidelines ≥90%）
    Phase 7: GATE — SEO Review（Technical / On-Page / Performance / Social）
    Phase 8: GATE — Ralph Polish Loop（20パス / 97%以上必須）
    LOCAL_RUN_PROOF_GATE（RUN_CERTIFICATE.json status:PASS 必須）

LAYER 3: DEPLOY（14:00〜14:30）
  supercent-io/skills-template@vercel-deploy を使用（1.6K installs）
  ソース: https://skills.sh/supercent-io/skills-template/vercel-deploy
          「Deploy to Vercel, returns preview URL and claimable deployment link」
  Stripe 商品・サブスク自動設定（ボイラープレート活用）
  PostHog + Sentry 自動設定

LAYER 4: REPORT & MARKET（14:30）
  [Slack] vm0-ai/vm0-skills@slack-webhook を使用
    「✅ 完成: https://xxx.vercel.app / ニッチ: xxx / 所要時間: xxh」
    ソース: https://skills.sh/vm0-ai/vm0-skills/slack-webhook
            「Simple one-way messaging to Slack channel, no OAuth setup」

  [X] Postiz CLI → X（Twitter）自動投稿
    「Just shipped: {app_name} — {one_line_pitch} 🚀 {url} #BuildInPublic #indiehacker」
    npm install -g postiz && postiz posts:create
    ソース: https://docs.postiz.com/usage/cli / レート制限: 30 req/hour（1日1回で問題なし）
```

### 新規作成ファイル

| ファイル | 役割 | 作成方法 |
|---------|------|---------|
| `.openclaw/skills/webapp-factory-orchestrator/SKILL.md` | Anicca が読む全体オーケストレーター | clawhub `autonomous-skill-orchestrator` をベースに作成 |
| `.openclaw/skills/webapp-factory-orchestrator/prompt.md` | CC に渡す LAYER 1〜4 の実行指示 | Anthropic 2-Agent パターン（Initializer + Coding Agent + claude-progress.txt）に従って作成。ソース: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents |
| `.openclaw/skills/webapp-factory-orchestrator/.env` | 全共有鍵（gitignored） | スキルの cron コマンドが `source` して Claude Code に継承 |
| `.openclaw/skills/webapp-factory-orchestrator/.env.example` | 必要な鍵の一覧（コミット可） | roundcube-webmail スキルのパターンに準拠 |

### インストールするスキル（全15件）

| # | スキル | インストールコマンド | 外部確認 | 担当 |
|---|--------|-------------------|---------|------|
| 1 | appfactory-builder | ✅ 済み | 0xaxiom/appfactory (8 installs) | Claude Code |
| 2 | app-builder | ✅ 済み | sickn33/antigravity-awesome-skills (346 installs) | Claude Code |
| 3 | senior-frontend | ✅ 済み | davila7/claude-code-templates (784 installs) | Claude Code |
| 4 | nextjs-expert | ✅ 済み | cin12211/orca-q (41 installs) | Claude Code |
| 5 | apify-ultimate-scraper | `npx skills add apify/agent-skills@apify-ultimate-scraper` | apify/agent-skills (確認済み) | Claude Code |
| 6 | content-trend-researcher | `npx skills add alirezarezvani/claude-code-skill-factory@content-trend-researcher` | alirezarezvani (29 installs) | Claude Code |
| 7 | startup-idea-validation | `npx skills add vasilyu1983/ai-agents-public@startup-idea-validation` | vasilyu1983 (142 installs) | Claude Code |
| 8 | reddit-insights | `clawhub install reddit-insights` | clawhub (確認済み) | Anicca |
| 9 | google-trends | `clawhub install google-trends` | clawhub (確認済み) | Anicca |
| 10 | market-research-agent | `clawhub install market-research-agent` | clawhub (確認済み) | Anicca |
| 11 | **vercel-deploy** | `npx skills add supercent-io/skills-template@vercel-deploy` | supercent-io (1.6K installs) | Claude Code |
| 12 | **configure-notifications** | `npx skills add yeachan-heo/oh-my-claudecode@configure-notifications` | yeachan-heo (確認済み) | Claude Code |
| 13 | **slack-webhook** | `npx skills add vm0-ai/vm0-skills@slack-webhook` | vm0-ai (33 installs) | Claude Code |
| 14 | **cron設定** | OpenClaw `jobs.json` 直接編集 | cron-creator は ClawHub に存在しない。jobs.json 手動追加で代替 | Claude Code |
| 15 | **autonomous-skill-orchestrator** | `clawhub install autonomous-skill-orchestrator` | clawhub (確認済み) | Anicca |

**注:** `niche-opportunity-finder` (zanecole10) は LAYER 1 の `startup-idea-validation` と機能重複のため統合。ニッチ選定は `startup-idea-validation` + `market-research-agent` で対応。
**Postiz CLI:** スキルではなくCLIツール。`npm install -g postiz` → `postiz posts:create`。ソース: https://postiz.com/agent

---

## 4. テストマトリックス

| # | To-Be | テスト名 | AC |
|---|-------|---------|-----|
| 1 | cron 09:00 JST 起動 | `test_cron_triggers_at_0900_jst` | AC-1 |
| 2 | idea.md 生成 | `test_layer1_generates_idea_md` | AC-2 |
| 3 | idea.md の5セクション存在 | `test_idea_md_has_required_sections` | AC-3 |
| 4 | Phase 0 が idea.md を消費 | `test_phase0_consumes_idea_md` | AC-4 |
| 5 | Skills Audit ≥95% | `test_phase6_skills_audit_passes` | AC-5 |
| 6 | SEO Review PASS | `test_phase7_seo_passes` | AC-6 |
| 7 | Ralph 97%+ PASS | `test_phase8_ralph_passes` | AC-7 |
| 8 | RUN_CERTIFICATE 存在 | `test_run_certificate_status_pass` | AC-8 |
| 9 | Vercel URL 有効 | `test_vercel_url_accessible` | AC-9 |
| 10 | Slack 投稿確認 | `test_slack_metrics_posted` | AC-10 |
| 11 | human_input ログなし | `test_no_human_input_in_logs` | AC-11 |
| 12 | X 投稿が Postiz 経由で公開 | `test_x_post_published_via_postiz` | AC-12 |

---

## 5. 境界

### やること
- LAYER 1〜4 の実装（スキルインストール + オーケストレーター + cron）
- Mac Mini 上での全動作確認
- Postiz 経由 X 自動投稿（LAYER 4 に含む）
- GitHub オープンソース化（Section 10 参照）

### やらないこと
- 並列実行（1日1本から。スケールは別スペック）

### 触らないファイル
- `.openclaw/cron/jobs.json` の既存エントリ

---

## 6. 実行手順

### 担当分け
| 誰が | 何を | 方法 |
|------|------|------|
| **ダイス** | アカウント 8件のキー取得 | GUI ログイン（Section 9 参照） |
| **私（Claude Code）** | 全ファイル作成・push | ローカル作成 → git push → Mac Mini が pull |
| **Anicca** | cron 設定・スキル追加 | Slack 経由で指示。Anicca が自分で `cron-creator` + `clawhub install` を実行 |

### STEP 1: ダイスのキー取得（Section 9 参照）

### STEP 2: 私がローカルで作成 → push
```
作成するファイル（全てローカル → git push → Mac Mini pull）:
  .openclaw/skills/webapp-factory-orchestrator/SKILL.md
  .openclaw/skills/webapp-factory-orchestrator/prompt.md
```

### STEP 3: Anicca への指示（Slack 経由）
```
「webapp-factory セットアップを開始。
  1. clawhub install autonomous-skill-orchestrator --force
  2. clawhub install reddit-insights --force && clawhub install google-trends --force && clawhub install market-research-agent
  3. npx skills install apify/agent-skills@apify-ultimate-scraper --yes
  4. npx skills install alirezarezvani/claude-code-skill-factory@content-trend-researcher --yes
  5. npx skills install vasilyu1983/ai-agents-public@startup-idea-validation --yes
  6. npx skills install supercent-io/skills-template@vercel-deploy --yes
  7. npx skills install yeachan-heo/oh-my-claudecode@configure-notifications --yes
  8. npx skills install vm0-ai/vm0-skills@slack-webhook --yes
  9. jobs.json に webapp-factory cron（09:00 JST）エントリを追加
  完了したら Slack に報告してください。」
```

### STEP 4: 手動テスト（Anicca への指示）
```
「webapp-factory を今すぐ1回テスト実行してください」
```

### STEP 5: 確認
- Slack #metrics に進捗 + 完成報告が流れるか
- Vercel URL にアクセスできるか
- X タイムラインに投稿が出るか

---

## 7. E2E判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし（Mac Mini バックエンドのみ） |
| 新画面 | なし |
| 結論 | Maestro E2E: 不要。cron ログ + idea.md + Slack 投稿 + X 投稿で検証 |

---

## 8. 月額コスト

| サービス | プラン | 費用 |
|---------|--------|------|
| Vercel Pro | 商用 | 支払済み ✅ |
| Apify | Starter | $49/月 |
| Supabase / Stripe / PostHog / Sentry / X Dev / Postiz | 無料枠 | $0 |
| **追加合計** | | **$49/月** |

---

## 9. アカウントセットアップ（✅ 全件完了）

全鍵は `.openclaw/skills/webapp-factory-orchestrator/.env` に配置済み。
ソース: roundcube-webmail スキルの `.env.example` パターンに準拠。
ソース: [Claude Code Settings](https://code.claude.com/docs/en/settings) / 核心の引用: 「Shell-level variables take precedence over values set here」

### 鍵の配置先

| 配置先 | 何が入るか | 誰が読むか |
|-------|-----------|-----------|
| `.openclaw/skills/webapp-factory-orchestrator/.env` | 全共有鍵（下表） | Claude Code（cron `source` 経由） |
| `vercel env add` | NEXT_PUBLIC_* 等 | デプロイされたアプリ（Vercel本番） |
| `.openclaw/.env` | Anicca/OpenClaw 専用鍵のみ | OpenClaw Gateway |

### 共有 vs アプリごと

| 鍵 | 共有/個別 | 理由 |
|----|----------|------|
| SUPABASE_URL, ANON_KEY, SERVICE_ROLE_KEY | ✅ 共有 | RLS で `app_id` 分離。ソース: Clerk Multi-Tenant SaaS Architecture |
| STRIPE_SECRET_KEY | ✅ 共有 | 同一ビジネス、`customer_id` で管理 |
| POSTHOG keys | ✅ 共有 | `app_name` プロパティで分離 |
| VERCEL_TOKEN, VERCEL_ORG_ID | ✅ 共有 | 同一アカウント |
| APIFY_TOKEN | ✅ 共有 | 同一アカウント |
| SLACK_WEBHOOK_URL | ✅ 共有 | 同一チャンネル |
| POSTIZ_API_KEY, X_BEARER_TOKEN | ✅ 共有 | 同一アカウント |
| SENTRY_AUTH_TOKEN, SENTRY_ORG | ✅ 共有 | org token で全プロジェクト操作 |
| STRIPE_WEBHOOK_SECRET | ❌ アプリごと | Claude Code が `stripe webhooks create` で自動生成 |
| SENTRY_DSN (per app) | ❌ アプリごと | Claude Code が `sentry-cli projects create` で自動生成 |
| Vercel プロジェクト | ❌ アプリごと | `vercel deploy` が自動作成 |

### 設定済みの鍵一覧（✅ 全件取得完了）

| # | サービス | 鍵 | ステータス |
|---|---------|-----|----------|
| 1 | Supabase | `SUPABASE_URL` `SUPABASE_ANON_KEY` `SUPABASE_SERVICE_ROLE_KEY` | ✅ |
| 2 | Stripe | `STRIPE_SECRET_KEY` | ✅ |
| 3 | PostHog | `POSTHOG_PERSONAL_API_KEY` `POSTHOG_PROJECT_TOKEN` | ✅ |
| 4 | Vercel | `VERCEL_TOKEN` `VERCEL_ORG_ID` | ✅ |
| 5 | Apify | `APIFY_TOKEN` | ✅ |
| 6 | Slack | `SLACK_WEBHOOK_URL` | ✅ |
| 7 | Postiz | `POSTIZ_API_KEY` | ✅ |
| 8 | X / Twitter | `X_BEARER_TOKEN` | ✅ |
| 9 | Sentry | `SENTRY_AUTH_TOKEN` `SENTRY_DSN` `SENTRY_ORG` | ✅ |

---

## 10. オープンソース化計画

ソース: [anthropics/skills](https://github.com/anthropics/skills) / 核心の引用: 「Skills are folders of instructions that Claude loads dynamically」
ソース: [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) / 核心の引用: 「A curated list of skills for Claude Code」

| ステップ | 内容 | 提出先 |
|---------|------|-------|
| 1 | `webapp-factory-orchestrator/SKILL.md` 動作確認後に整備 | — |
| 2 | PR 提出 | https://github.com/anthropics/skills |
| 3 | PR 提出 | https://github.com/travisvn/awesome-claude-skills |
