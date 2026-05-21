# webapp-factory v3 — 一次ソース検証済み + オリジナリティゼロ

**Date**: 2026-03-01（最終更新: 同日 — O-1〜O-5 修正済み）
**Author**: Claude Code
**Status**: ⬜ 未実行

---

## 0. As-Is → To-Be

### As-Is（現在の状態 — 壊れている/間違っている箇所）

| # | ファイル | 現在の状態 | 問題 |
|---|---------|-----------|------|
| 1 | `~/.openclaw/skills/webapp-factory-orchestrator/SKILL.md` | 単発 `claude -p` 起動 | Ralph ループではない。コンテキスト溢れる |
| 2 | `~/.openclaw/skills/webapp-factory-orchestrator/prompt.md` | E2E テストなし、`npx vercel deploy` 直打ち、Postiz なし、system event 報告なし | 4つの欠落 |
| 3 | Ralph ループスクリプト | **存在しない** | snarktank/ralph の ralph.sh をコピーして配置する必要あり |
| 4 | Postiz CLI | `npx postiz` で動く（v2.0.12）がグローバル未インストール | `npm install -g postiz` が必要 |
| 5 | Postiz 環境変数 | `POSTIZ_API_KEY` 未設定 | `.env` に追加必要 |
| 6 | prompt.md 内の Slack 報告 | system event の記述がない | 各 US で `openclaw system event` を発火する指示がない |

### To-Be（修正後の状態）

| # | ファイル | 修正後 | 一次ソース |
|---|---------|-------|-----------|
| 1 | SKILL.md | `exec pty:true background:true command:"bash ralph.sh --tool claude 20"` | [snarktank/ralph](https://github.com/snarktank/ralph) — WebFetch 検証済み |
| 2 | prompt.md | Playwright E2E（webapp-testing スキル）+ `npx vercel deploy --prod` + Postiz `posts:create` + 各 US で system event 発火 | 各項目下記 |
| 3 | `ralph.sh` | snarktank/ralph からコピー。`for i in $(seq 1 $MAX_ITERATIONS)` + `claude --dangerously-skip-permissions --print < CLAUDE.md` | [ralph.sh](https://github.com/snarktank/ralph/blob/main/ralph.sh) — WebFetch 検証済み |
| 4 | Postiz CLI | `npm install -g postiz` でグローバルインストール | `npx postiz --help` → v2.0.12 Mac Mini で実行検証済み |
| 5 | Postiz 環境変数 | `POSTIZ_API_KEY=xxx` を `.env` に追加 | [Postiz CLI](https://docs.postiz.com/cli/managing-posts) — WebFetch 検証済み |
| 6 | prompt.md 内の報告 | 各イテレーションで `openclaw system event --text "webapp-factory iteration N/M: status" --mode now`（Ralph のイテレーション番号フォーマットに従う） | [ralph.sh](https://github.com/snarktank/ralph/blob/main/ralph.sh) の `"Ralph Iteration $i of $MAX_ITERATIONS"` + [OpenClaw CLI system event](https://docs.openclaw.ai/cli/system) — WebFetch 検証済み |

---

## 1. 工場の全体像

```
┌──────────────────────────────────────────────────────────────────┐
│                    webapp-factory v3 全体像                       │
│                                                                  │
│  登場人物:                                                       │
│  ├─ Anicca（OpenClaw エージェント）= 工場長。監視・報告・指示     │
│  ├─ ralph.sh（bash スクリプト）= ループ制御。コンテキスト管理     │
│  ├─ Claude Code Opus（`--print` モード）= 作業員。コードを書く   │
│  └─ ダイス（人間）= オーナー。Slack で報告を受け取る            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

cron 09:00 JST（Anicca OpenClaw jobs.json）
    │
    ▼
┌─ ANICCA（工場長 — SKILL.md）─────────────────────────────────┐
│                                                               │
│  ① SKILL.md を読む                                           │
│  ② Slack #metrics に「🏭 webapp-factory 起動」                │
│  ③ ralph.sh を起動:                                           │
│     exec pty:true background:true                             │
│     command: "bash ralph.sh --tool claude 20"                 │
│     → sessionId を記録                                        │
│  ④ 監視ループ:                                                │
│     ├─ system event 受信 → Slack に転送                       │
│     │   "iteration N/M: task" → Slack「🏗️ iteration N 開始」 │
│     │   "iteration N/M: COMPLETE" → Slack「✅ 完了」          │
│     │   "iteration N/M: ERROR" → Slack「❌ エラー」           │
│     │   "COMPLETE: app — url" → Slack「🎉 完成」              │
│     ├─ 10分無音 → process action:log → Slack に進捗報告       │
│     └─ エラー3回連続 → Slack「⚠️ 人間レビュー必要」           │
│                                                               │
└───────────────────────────────────────────────────────────────┘
    │
    ▼
┌─ ralph.sh（snarktank/ralph からコピー）───────────────────────┐
│                                                               │
│  ソース: https://github.com/snarktank/ralph/blob/main/ralph.sh│
│  検証: WebFetch で直接確認済み                                │
│                                                               │
│  for i in $(seq 1 $MAX_ITERATIONS):                           │
│     ① claude --dangerously-skip-permissions --print           │
│        < "$SCRIPT_DIR/CLAUDE.md"                              │
│     ② 出力を progress.txt に追記                              │
│     ③ <promise>COMPLETE</promise> 検出 → EXIT                │
│     ④ 検出しなければ次のイテレーション（新鮮コンテキスト）    │
│                                                               │
│  追跡ファイル:                                                │
│  ├─ prd.json（タスク一覧 + passes フラグ）                    │
│  ├─ progress.txt（append-only イテレーションログ）            │
│  │   フォーマット（Ralph prompt.md 準拠）:                    │
│  │   ## [Date/Time] - [Task ID]                               │
│  │   - What was implemented                                   │
│  │   - Files changed                                          │
│  │   - **Learnings for future iterations:**                   │
│  │     - Patterns / Gotchas / Context                         │
│  ├─ CLAUDE.md（prompt.md の内容を結合したプロンプト）         │
│  └─ AGENTS.md（学習記録の集約）                               │
│                                                               │
│  最大イテレーション: 20（安全装置）                            │
│                                                               │
│  ソース: Ralph prompt.md                                      │
│  https://github.com/snarktank/ralph/blob/main/prompt.md       │
│  引用: "APPEND to progress.txt (never replace, always append)"│
│                                                               │
└───────────────────────────────────────────────────────────────┘
    │
    ▼
┌─ CLAUDE CODE（作業員 — 各イテレーション）─────────────────────┐
│                                                               │
│  prd.json から次の未完了タスクをピック:                        │
│  ① 実装（プレースホルダー禁止）                               │
│  ② npm run build && npm run lint（プロジェクト標準ツール）    │
│  ③ Playwright E2E（全ページ実装後、webapp-testing スキル使用）│
│  ④ git commit + push                                         │
│  ⑤ progress.txt に学びを追記（Ralph 標準フォーマット）        │
│  ⑥ openclaw system event --text "webapp-factory iteration     │
│     $i/$MAX: [task] DONE" --mode now                          │
│  ⑦ prd.json の該当タスクを passes:true に更新                 │
│  ⑧ 全タスク完了 → <promise>COMPLETE</promise> を出力         │
│                                                               │
│  ソース: Addy Osmani 6-step cycle                             │
│  https://addyosmani.com/blog/self-improving-agents/           │
│  引用: "1. Pick the next task, 2. Implement, 3. Validate,     │
│         4. Commit, 5. Update task status, 6. Reset context"   │
│                                                               │
└───────────────────────────────────────────────────────────────┘
    │
    ▼
┌─ 完了後 ──────────────────────────────────────────────────────┐
│                                                               │
│  ① AGENTS.md に学習記録を集約                                 │
│  ② openclaw system event --text "COMPLETE: {app} — {url}"     │
│  ③ Anicca が Slack #metrics に完成報告                        │
│  ④ npx postiz posts:create で X に投稿                        │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## 2. Slack 報告の仕組み（2層構造）

**Ralph 自体に通知機能はない。** OpenClaw の 2層構造で補う。

ソース: ralph.sh を WebFetch で検証 — 引用: 「There are no webhooks, email notifications, or external reporting mechanisms—just file-based logging and console output.」

```
層1: Claude Code（作業員）
    │
    │  各イテレーションの完了/エラーで bash コマンドを実行:
    │  openclaw system event --text "webapp-factory iteration 3/20: build PASS" --mode now
    │
    │  --print モードでも bash コマンド実行は可能
    │  （--print は stdin からプロンプトを読むだけで、ツール使用は制限しない）
    │
    ▼
OpenClaw Gateway（Mac Mini 常駐プロセス）
    │
    │  system event を受信
    │
    ▼
層2: Anicca（工場長 — SKILL.md の監視ループ）
    │
    │  イベントを解釈 → Slack メッセージを構成
    │
    ▼
Slack #metrics (C091G3PKHL2)
    │
    ▼
ダイス（人間）が Slack で確認
```

| 報告タイミング | 誰が発火 | どうやって Slack に届く |
|---------------|---------|----------------------|
| イテレーション完了 | Claude Code | `openclaw system event --text "webapp-factory iteration N/M: task DONE"` → Gateway → Anicca → Slack |
| エラー | Claude Code | `openclaw system event --text "webapp-factory iteration N/M: ERROR - msg"` → Gateway → Anicca → Slack |
| 10分無音 | Anicca（自発） | `process action:log sessionId:<id>` でログ確認 → Slack |
| 工場完成 | Claude Code | `openclaw system event --text "COMPLETE: {app} — {url}"` → Gateway → Anicca → Slack |

**prompt.md に書くべき指示**（各 US の冒頭と末尾に必須）:

```bash
# イテレーション完了時（必須 — Ralph のイテレーション番号フォーマットに従う）
# ソース: ralph.sh — 「Ralph Iteration $i of $MAX_ITERATIONS ($TOOL)」
openclaw system event --text "webapp-factory iteration 3/20: Next.js scaffold DONE" --mode now

# エラー時（必須）
openclaw system event --text "webapp-factory iteration 3/20: ERROR — npm build failed, page.tsx:42" --mode now

# 全工程完了時（必須）
openclaw system event --text "COMPLETE: DeepWork.fm — https://xxx.vercel.app" --mode now
```

---

## 3. 各 US の詳細

### US-001: トレンド調査 + prd.json 生成

| 項目 | 値 |
|------|-----|
| **担当** | Claude Code |
| **入力** | なし（自律開始） |
| **出力** | `daily-apps/{YYYYMMDD}-webapp/prd.json` + `CLAUDE.md` |
| **報告** | `openclaw system event --text "webapp-factory iteration N/20: trend research DONE" --mode now` |
| **ソース** | [0xAxiom/AppFactory](https://github.com/0xAxiom/AppFactory) — WebFetch 検証済み |

### US-002: Stripe Product + Price 作成

| 項目 | 値 |
|------|-----|
| **担当** | Claude Code |
| **入力** | prd.json の price_monthly_usd |
| **出力** | `STRIPE_PRICE_ID` in `.env.local` |
| **方法** | Stripe REST API（curl） |
| **報告** | `openclaw system event --text "webapp-factory iteration N/20: Stripe setup DONE" --mode now` |
| **ソース** | [Stripe API Products](https://docs.stripe.com/api/products/create) — WebFetch 検証済み |

### US-003: Next.js プロジェクト作成

| 項目 | 値 |
|------|-----|
| **担当** | Claude Code |
| **入力** | prd.json の slug, tech_stack |
| **出力** | `npx create-next-app` 完了 + `npm run build` PASS |
| **報告** | `openclaw system event --text "webapp-factory iteration N/20: Next.js scaffold DONE" --mode now` |
| **ソース** | [Next.js Installation](https://nextjs.org/docs/getting-started/installation) — WebFetch 検証済み |

### US-004: 機能実装（1ページずつ）

| 項目 | 値 |
|------|-----|
| **担当** | Claude Code |
| **入力** | prd.json の機能仕様 |
| **出力** | 全ページ実装 + Stripe Checkout 動作 |
| **Stripe パターン** | Server Action（`"use server"` + `stripe.checkout.sessions.create`） |
| **報告** | `openclaw system event --text "webapp-factory iteration N/20: feature impl DONE" --mode now` |
| **禁止** | alert(), href="#", "coming soon", console.log, TODO, FIXME, lorem ipsum, NotImplemented |
| **ソース** | [Stripe Checkout Quickstart](https://docs.stripe.com/checkout/quickstart?client=next) — WebFetch 検証済み |

### US-005: 品質チェック + E2E テスト

| 項目 | 値 |
|------|-----|
| **担当** | Claude Code |
| **入力** | 実装済みコード |
| **出力** | L0 Gate PASS + Playwright E2E PASS + `npm run build` PASS |
| **報告** | `openclaw system event --text "webapp-factory iteration N/20: E2E test DONE" --mode now` |

**テスト2層**（プロジェクト標準ツールのみ — Ralph CLAUDE.md に従う）:

| 層 | ツール | 何を確認 | 一次ソース |
|----|--------|---------|-----------|
| L1 | `npm run build && npm run lint` | TypeScript コンパイル + Next.js ビルド + ESLint | [Ralph CLAUDE.md](https://github.com/snarktank/ralph/blob/main/CLAUDE.md) 引用: 「quality checks (e.g., typecheck, lint, test - use whatever your project requires)」 |
| L2 | **webapp-testing スキル**の `with_server.py` + Python Playwright | ブラウザ E2E | webapp-testing SKILL.md 直接読み検証済み |

**⚠️ grep 8パターン L0 Gate は削除。** Ralph はプロジェクト固有のツール（lint, typecheck, test）を使う。独自の grep パターンは使わない。
ソース: [Ralph CLAUDE.md](https://github.com/snarktank/ralph/blob/main/CLAUDE.md) 引用: 「ALL commits must pass your project's quality checks」

**Playwright E2E の具体的な実行方法**（webapp-testing スキルに従う）:

```bash
# サーバー起動 + テスト実行（webapp-testing スキルのパターン）
python .claude/skills/webapp-testing/scripts/with_server.py \
  --server "npm run dev" --port 3000 \
  -- python test_e2e.py
```

```python
# test_e2e.py（Python Playwright — webapp-testing SKILL.md のパターンに従う）
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)  # SKILL.md: Always launch chromium in headless mode
    page = browser.new_page()
    page.goto('http://localhost:3000')
    page.wait_for_load_state('networkidle')  # SKILL.md: CRITICAL: Wait for JS to execute

    # トップページ表示確認
    assert page.title() != ""

    # Pricing ページ遷移
    page.goto('http://localhost:3000/pricing')
    page.wait_for_load_state('networkidle')
    assert page.locator('text=Pro').is_visible()

    # Stripe ボタン存在確認
    assert page.locator('text=Upgrade to Pro').is_visible()

    browser.close()
    print("E2E PASS")
```

ソース: `.claude/skills/webapp-testing/SKILL.md` — 直接読み検証済み。引用: 「Always launch chromium in headless mode」「CRITICAL: Wait for JS to execute」

### US-006: Vercel デプロイ

| 項目 | 値 |
|------|-----|
| **担当** | Claude Code |
| **入力** | ビルド済みコード |
| **出力** | 有効な Vercel URL |
| **方法** | `npx vercel deploy --prod --token $VERCEL_TOKEN --yes` |
| **報告** | `openclaw system event --text "webapp-factory iteration N/20: deploy DONE — {url}" --mode now` |

**⚠️ vercel-deploy スキル（`.claude/skills/vercel-deploy/`）は使わない。** 理由:
- SKILL.md に `platforms: [Claude]`（claude.ai 用）と明記
- スクリプトパス `/mnt/skills/user/vercel-deploy/scripts/deploy.sh` は Mac Mini に存在しない
- デプロイ先が `claude-skills-deploy.vercel.com`（claude.ai 用の中継サービス）

代わりに **Vercel CLI**（`npx vercel` v50.25.4、Mac Mini で実行検証済み）を直接使う。

ソース: [Vercel CLI Docs](https://vercel.com/docs/cli) — 一次ソース。vercel-deploy SKILL.md 169行目: `호환 플랫폼: Claude (claude.ai)` — 直接読み検証済み。

### US-007: 完了報告 + X 投稿

| 項目 | 値 |
|------|-----|
| **担当** | Claude Code + Anicca |
| **出力** | AGENTS.md + Slack 報告 + X 投稿 |
| **報告** | `openclaw system event --text "COMPLETE: {app} — {url}" --mode now` |

**X 投稿方法: Postiz CLI**

```bash
# 統合 ID 確認（初回のみ — X/Twitter の integration-id を取得）
npx postiz integrations:list

# X にツイート投稿
npx postiz posts:create \
  -c "Just shipped: {app_name} 🚀 {vercel_url} #BuildInPublic #indiehacker" \
  -s "{ISO8601_DATE}" \
  -i "{twitter-integration-id}"
```

| 項目 | 値 | 検証 |
|------|-----|------|
| CLI コマンド | `postiz posts:create` | `npx postiz --help` Mac Mini 実行検証済み |
| バージョン | 2.0.12 | `npx postiz --version` Mac Mini 実行検証済み |
| ドキュメント | https://docs.postiz.com/cli/managing-posts | WebFetch 検証済み ✅ |
| ❌ 間違いURL | `docs.postiz.com/usage/cli` | **404 確認済み** |
| ❌ 間違いコマンド | `postiz agent` | **存在しない。正しくは `posts:create`** |
| 必須環境変数 | `POSTIZ_API_KEY` | `.env` に追加必要 |

**AGENTS.md**: [snarktank/ralph](https://github.com/snarktank/ralph) — WebFetch 検証済み

---

## 4. Ralph ループの仕組み

**snarktank/ralph の ralph.sh をそのままコピーして使う。自作しない。**

| 項目 | 値 | 一次ソース |
|------|-----|-----------|
| リポジトリ | snarktank/ralph（11.7k stars） | https://github.com/snarktank/ralph — WebFetch 検証済み |
| メインスクリプト | `ralph.sh` | https://github.com/snarktank/ralph/blob/main/ralph.sh — WebFetch 検証済み |
| Claude コマンド | `claude --dangerously-skip-permissions --print < "$SCRIPT_DIR/CLAUDE.md"` | ralph.sh 内 — WebFetch で原文確認済み |
| ループ構造 | `for i in $(seq 1 $MAX_ITERATIONS)` | ralph.sh 内 — WebFetch で原文確認済み |
| 完了検出 | `<promise>COMPLETE</promise>` を stdout で検出 | ralph.sh 内 — WebFetch で原文確認済み |
| 追跡ファイル | `prd.json` + `progress.txt` | ralph.sh 内 — WebFetch で原文確認済み |

**⚠️ ralph-autonomous-dev スキル（`.claude/skills/ralph-autonomous-dev/`）は使わない。** 理由:
- `frankbria/ralph-claude-code` をベースにした別設計（`fix_plan.md` ベース）
- snarktank/ralph（11.7k stars、オリジナル）の `prd.json` パターンがベストプラクティス
- webapp-factory は `prd.json` で US を追跡するため snarktank 版が適合する

```
snarktank/ralph の ralph.sh フロー:

for i in $(seq 1 20):
    │
    ├── claude --dangerously-skip-permissions --print < CLAUDE.md
    │   │
    │   │  Claude Code が prd.json の次タスクを実行:
    │   │  ├─ 実装 + npm run build && npm run lint
    │   │  ├─ git commit + push
    │   │  ├─ progress.txt に学びを追記（append-only）
    │   │  ├─ openclaw system event "iteration N/20: task DONE"
    │   │  └─ prd.json 更新（passes: true）
    │   │
    │   └── 出力に <promise>COMPLETE</promise> があれば EXIT
    │
    ├── 出力を progress.txt に追記
    │
    └── 次のイテレーション（新鮮なコンテキスト）
```

---

## 5. 対話モード vs 非対話モード

**決定: 非対話モード（`--print`）**

| 根拠 | 一次ソース | 検証 |
|------|-----------|------|
| Ralph は `--print` を使う | [ralph.sh](https://github.com/snarktank/ralph/blob/main/ralph.sh) | WebFetch で原文確認済み |
| Anthropic は headless/自動化に `--print` を推奨 | [Claude Code Headless Mode](https://code.claude.com/docs/en/headless) | WebFetch 検証済み |
| OpenClaw coding-agent も `-p` を使う | [coding-agent SKILL.md](https://github.com/openclaw/openclaw/blob/main/skills/coding-agent/SKILL.md) | WebFetch 検証済み |

**PTY は必須**: `exec pty:true`

ソース: [OpenClaw coding-agent](https://github.com/openclaw/openclaw/blob/main/skills/coding-agent/SKILL.md) — 引用: 「Always use pty:true - coding agents need a terminal!」

---

## 6. 一次ソース検証テーブル（全て WebFetch または Mac Mini 実行で検証済み）

| # | ソース | URL | 検証方法 | 結果 |
|---|--------|-----|---------|------|
| S1 | snarktank/ralph | https://github.com/snarktank/ralph | WebFetch | ✅ 11.7k stars |
| S2 | ralph.sh | https://github.com/snarktank/ralph/blob/main/ralph.sh | WebFetch | ✅ `claude --dangerously-skip-permissions --print` 確認 |
| S3 | frankbria/ralph-claude-code | https://github.com/frankbria/ralph-claude-code | WebFetch | ✅ 存在。ただし webapp-factory では使わない |
| S4 | Anthropic Long-Running Agents | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents | WebFetch | ✅ |
| S5 | Claude Code Headless Mode | https://code.claude.com/docs/en/headless | WebFetch | ✅ |
| S6 | OpenClaw coding-agent | https://github.com/openclaw/openclaw/blob/main/skills/coding-agent/SKILL.md | WebFetch | ✅ |
| S7 | 0xAxiom/AppFactory | https://github.com/0xAxiom/AppFactory | WebFetch | ✅ |
| S8 | Macaron Software Factory | https://github.com/macaron-software/software-factory | WebFetch | ✅ 10品質次元。grep パターンは使っていない |
| S9 | Stripe API Products | https://docs.stripe.com/api/products/create | WebFetch | ✅ |
| S10 | Stripe Checkout Quickstart | https://docs.stripe.com/checkout/quickstart?client=next | WebFetch | ✅ |
| S11 | Postiz CLI Managing Posts | https://docs.postiz.com/cli/managing-posts | WebFetch | ✅ `postiz posts:create` |
| S12 | Postiz 公式 | https://postiz.com/ | WebFetch | ✅ |
| S13 | ❌ Postiz usage/cli | https://docs.postiz.com/usage/cli | WebFetch | ❌ **404** |
| S14 | Vercel CLI | https://vercel.com/docs/cli | 一次ソース | ✅ |
| S15 | Next.js Installation | https://nextjs.org/docs/getting-started/installation | WebFetch | ✅ |
| S16 | webapp-testing SKILL.md | `.claude/skills/webapp-testing/SKILL.md` | ローカル Read | ✅ |
| S17 | vercel-deploy SKILL.md | `.claude/skills/vercel-deploy/SKILL.md` | ローカル Read | ✅ platforms: [Claude]（claude.ai 用） |
| S18 | ralph-autonomous-dev SKILL.md | `.claude/skills/ralph-autonomous-dev/SKILL.md` | ローカル Read | ✅ frankbria 版。使わない |
| S19 | Postiz CLI バージョン | `npx postiz --version` | Mac Mini 実行 | ✅ v2.0.12 |
| S20 | Vercel CLI バージョン | `npx vercel --version` | Mac Mini 実行 | ✅ v50.25.4 |
| S21 | Playwright CLI | `/opt/homebrew/bin/playwright` | Mac Mini `which` | ✅ インストール済み |
| S22 | Addy Osmani - Self-Improving Agents | https://addyosmani.com/blog/self-improving-agents/ | WebFetch | ✅ 6-step cycle、progress.txt + AGENTS.md パターン |
| S23 | OpenClaw CLI - system event | https://docs.openclaw.ai/cli/system | WebFetch | ✅ `--text` は free-form text |
| S24 | Ralph prompt.md | https://github.com/snarktank/ralph/blob/main/prompt.md | WebFetch | ✅ progress.txt append-only フォーマット |

---

## 7. TODO（実行手順）

| # | タスク | 詳細 | 依存 | 状態 |
|---|--------|------|------|------|
| 1 | Postiz CLI グローバルインストール | `npm install -g postiz` | なし | ⬜ |
| 2 | `POSTIZ_API_KEY` を `.env` に追加 | Postiz ダッシュボードから API Key を取得 → `~/.openclaw/skills/webapp-factory-orchestrator/.env` に追加 | なし | ⬜ |
| 3 | snarktank/ralph の `ralph.sh` をコピー配置 | `curl -o ~/.openclaw/skills/webapp-factory-orchestrator/ralph.sh https://raw.githubusercontent.com/snarktank/ralph/main/ralph.sh && chmod +x` | なし | ⬜ |
| 4 | SKILL.md 更新 | 起動コマンドを `bash ralph.sh --tool claude 20` に変更 | 3 | ⬜ |
| 5 | prompt.md 更新 | ① 各 US に `openclaw system event` 報告を追加 ② US-005 に webapp-testing スキルの Playwright E2E を追加 ③ US-006 を `npx vercel deploy --prod` に変更 ④ US-007 に `npx postiz posts:create` を追加 | 1, 2 | ⬜ |
| 6 | git push | 全変更を push | 4, 5 | ⬜ |
| 7 | テスト実行 | 一時 cron で1回実行して動作確認 | 6 | ⬜ |

---

## 8. 受け入れ条件

| # | 条件 | 検証方法 |
|---|------|---------|
| AC1 | snarktank/ralph の ralph.sh がコピー配置されている | `ls ~/.openclaw/skills/webapp-factory-orchestrator/ralph.sh` |
| AC2 | ralph.sh 内の Claude コマンドが `--print` モード | `grep "print" ralph.sh` |
| AC3 | SKILL.md の起動コマンドが `bash ralph.sh` になっている | `grep "ralph.sh" SKILL.md` |
| AC4 | prompt.md に `openclaw system event` が書かれている | `grep -c "system event" prompt.md` >= 1 |
| AC5 | prompt.md に webapp-testing スキルの Playwright E2E がある | `grep "with_server.py" prompt.md` |
| AC6 | prompt.md に `npx vercel deploy --prod` がある | `grep "npx vercel deploy" prompt.md` |
| AC7 | prompt.md に `postiz posts:create` がある | `grep "postiz posts:create" prompt.md` |
| AC8 | Postiz CLI がインストール済み | `postiz --version` |
| AC9 | `POSTIZ_API_KEY` が `.env` にある | `grep "POSTIZ_API_KEY" .env` |
| AC10 | prompt.md に `npm run build && npm run lint` がある（L0 grep ではない） | `grep "npm run build" prompt.md` |
| AC11 | prompt.md に progress.txt Learnings 追記指示がある（BLOCKING GATEではない） | `grep "progress.txt" prompt.md` |
| AC12 | Stripe Server Action パターンが prompt.md にある | `grep "use server" prompt.md` |

---

## 9. 境界（やらないこと）

| やらないこと | 理由 |
|------------|------|
| ralph-autonomous-dev スキルを使う | frankbria 版。snarktank/ralph が BP |
| vercel-deploy スキルを使う | claude.ai 用。Claude Code からは `npx vercel` |
| ralph-webapp.sh を自作する | snarktank/ralph の ralph.sh をそのままコピー |
| L1 独立レビュアー（別 LLM） | L0 Gate + Playwright で十分 |
| Customer Portal（Stripe Billing Portal） | サブスク管理 UI 不要 |
| 並列実行 | 1日1本から |
| Embedded Checkout（iframe） | Stripe Hosted Checkout（redirect）で十分 |

---

## 10. OSS 化計画: Slack → Anicca → アプリ出荷 → 公開

### ビジョン

```
┌─ ユーザー（Slack）──────────────────────────────────────────┐
│ 「ポモドーロタイマーアプリ作って、月$5のサブスク付きで」      │
└──────────────┬──────────────────────────────────────────────┘
               │ Slack メッセージ
               ▼
┌─ Anicca（OpenClaw エージェント）────────────────────────────┐
│ intent-router スキルでインテント判定:                        │
│ 「webapp作成リクエスト」→ webapp-factory-orchestrator 発動   │
│                                                              │
│ ① prd.json 生成（ユーザーの要望 → 仕様書）                  │
│ ② ralph.sh 起動（claude --print でビルド開始）              │
│ ③ 進捗を Slack に随時報告                                    │
│ ④ 完成 → Vercel URL を Slack に投稿                          │
│ ⑤ Stripe Product/Price 作成済み → 即日課金可能               │
└─────────────────────────────────────────────────────────────┘
```

### OSS 切り出し TODO

| # | タスク | 詳細 |
|---|--------|------|
| 1 | **スキルを独立リポに切り出す** | `webapp-factory/` として GitHub public リポ作成。SKILL.md + prompt.md + ralph.sh + prd.json.template |
| 2 | **ralph.sh の .env パスを汎用化** | `~/.config/webapp-factory/.env` に変更（[Twelve-Factor App](https://12factor.net/config) 準拠） |
| 3 | **CLAUDE.md テンプレート作成** | Ralph が読むプロンプト。prompt.md をベースに Anicca 固有部分を除去 |
| 4 | **prd.json テンプレート作成** | 最小限の仕様テンプレート: slug, name, features, price |
| 5 | **README.md** | インストール手順 + 必要な環境変数 + 使い方 |
| 6 | **skill.sh に公開** | `npx skills publish webapp-factory` → CC ユーザーが `npx skills install` で使える |
| 7 | **ClawHub に公開** | `clawhub publish webapp-factory` → OpenClaw ユーザーが `clawhub install` で使える |

### 2つの配布先

| プラットフォーム | コマンド | 対象ユーザー | 体験 |
|----------------|---------|-------------|------|
| **skill.sh**（CC用） | `npx skills install webapp-factory` | Claude Code ユーザー | 手動 `bash ralph.sh 20` 実行 |
| **ClawHub**（OpenClaw用） | `clawhub install webapp-factory` | OpenClaw ユーザー | cron で毎日自動実行（24/7） |

ソース: [skill.sh](https://skill.sh) — CC スキル公開プラットフォーム
ソース: [ClawHub](https://clawhub.com) — OpenClaw スキル公開プラットフォーム
