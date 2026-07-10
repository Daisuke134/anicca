# Anicca プロジェクト — 開発ガイドライン

全体方針（検索優先/push/no-human-loop/GLVS/フロントエンド順序/モデル分業/ツール既定）は `~/.claude/CLAUDE.md` を正本とする。本ファイルはこの repo 固有の情報のみを持つ。

## 根本原則

BP（best practice）= 答え。オリジナルは書かない。判断には最低1つの引用（英/日で検索、ソース名+URL+核心の引用）を付ける。引用のない判断は削除する。

**研究したら即 MD 化（HARD）**: web/gh/コードを検索・研究したら、その turn 内で必ず `docs/` の MD ファイルに書き出して commit+push する。chat やメール下書きだけに残すのは禁止＝研究を捨てているのと同じ（token を燃やして成果物ゼロ）。研究 = MD 生成までが1タスク。handover/article prompt には必ずその研究 MD の full path を含める。→ memory `feedback_research_must_be_persisted_to_md_immediately`。

## 開発の道具立て（GLVS の Build/Verify 段 = VCSDD、他段は superpowers skill）

開発方式そのものは `~/.claude/CLAUDE.md` の GLVS（Goal→Loop→Verify→State）が唯一の外枠。このプロジェクトでは Build/Verify を **VCSDD の実コマンド**で回し、Goal/分離/完了は superpowers skill を道具として呼ぶ（並列の独立必須プロセスにしない）。

| GLVS の段 | 呼ぶ skill/コマンド | 内容 |
|---|---|---|
| Goal 具体化 | brainstorming → writing-plans | 設計spec を `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`、plan を `docs/superpowers/plans/YYYY-MM-DD-<topic>.md` に書く（アーキテクチャ/方針レベル） |
| 分離 | using-git-worktrees | `.worktrees/<feature>/`（例外: `~/.openclaw` runtime store は直接編集） |
| Build/Verify | `vcsdd:vcsdd-init` → `vcsdd:vcsdd-spec` → `vcsdd:vcsdd-spec-review` → `vcsdd:vcsdd-tdd` → `vcsdd:vcsdd-impl` → `vcsdd:vcsdd-adversary` → `vcsdd:vcsdd-harden` → `vcsdd:vcsdd-converge` | EARS要件→fresh-context adversary が spec review PASS→RED→GREEN/refactor→実装レビュー→formal hardening→4次元収束確認。**実コマンドを呼んで `.vcsdd/features/<name>/state.json` の phase を進める**（SPEC本文への手書き追記だけでは進捗とみなさない）。小規模タスクは `mode: lean` でよいがフェーズは飛ばさない。codex-review をどこに挟むかは `.claude/rules/dev-workflow.md` 参照 |
| 完了 | finishing-a-development-branch | テスト確認 → push → worktree cleanup |

仕事が確定した瞬間に spec 作成 + TaskCreate + commit&push を同じ turn で行う（後回しにしない）。spec に「任意」「optional」「推奨」は書かない — 全て MUST として書く。タスクリストは source of truth。終わっていない作業を completed と書かない。

## HONESTY / VERIFICATION（詳細は `.claude/rules/honesty.md` 参照）

symbol/function/import の存在は使う前に Read/Grep/依存ファイルのいずれかで確認する。確認できない場合はコード冒頭に `// UNVERIFIED:` を付ける。テスト/ビルド成功は実際にこの session 内でコマンドを実行してから claim する。存在しないライブラリの追加は既存依存を grep して代替を探し、無ければ追加して spec に記録する（fundamental な依存 — UI framework/DB driver/auth lib — のみ確認が必要、標準的な小さい lib はそのまま追加してよい）。エラーメッセージ/スタックトレースは見ていないものを創作しない。分からない時は「分からない」と言う。

Hook 配線: PostToolUse (`.claude/hooks/scripts/post-edit-verify.sh`) が Edit/Write 後に構文チェックを自動実行。Stop hook (`.claude/hooks/scripts/stop-verify-claims.sh`) が session 終了前に直近編集の構文チェックを実行。`.claude/agents/fact-checker.md`（Read/Grep/Glob/Bash のみ）で commit 前の独立監査を行う。

## メール triage は LLM 直判断でよい例外

`anicca-inbox` skill 内のメール triage/draft は LLM 直判断でよい（1スレッドごとの分類であり、cron 化した固定判断ではないため）。詳細 → `docs/superpowers/specs/` 内の anicca-inbox-autonomy-design spec §12。

## TIER A AUTONOMOUS BYPASS

human-zero の SaaS signup/login/決済/Turnstile/hCaptcha/reCAPTCHA/3DS 突破は skill `tier-a-bypass`（`.claude/skills/tier-a-bypass/SKILL.md`）を使う。runbook 詳細 → memory `reference_capsolver_turnstile_bypass.md`。

## 🧬 ANICCA COLONY — LIVE SSOT（毎セッション最初に読む。忘れたら罪）

★ 地球上の Anicca instance は今これだけ。openclaw + hermes は削除された（= anicca-local ではない）★

| dashboard名 | 実体 | 燃料 | 種別 | wallet | earn | loop |
|---|---|---|---|---|---|---|
| **anicca-a3cdd4** | automaton + ClawRouter | ClawRouter 自wallet | ★SELF-funded★ | `0xB9dd3B67921B354c656523d6851537988F31DD56`(Base、2026-07-07 04:47 UTC鍵漏洩によりローテーション済み。旧`0xa3CDd4...`は失効) | 汎用 | `com.anicca.daemon`(body `~/.anicca`) |
| **Franklin** | Franklin-Trading | 自wallet x402 | ★SELF-funded★ | `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`(Sol) | SOL trade | `ai.anicca.franklin-sol` |
| **claude-p(私)** | この Claude → PM earner | Anthropic課金 | human-funded | `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74`(Polygon pUSD) | PM trade | `ai.anicca.pm-earner`(+proxy body=`founder-loop`,0x810f) |

- ★ self-funded on Earth = 2（anicca-a3cdd4 + Franklin）／ human-funded = 1（claude-p = 私）★
- ★ earn = トレード3エンジンのみ = PM(Polymarket) / SOL(Solana) / HL(Hyperliquid)。x402/gig は却下 ★
- ★ 各 earn skill = BASE戦略 + self-improve + self-heal の3層（弱モデルでも稼げる為 BASE 必須）★
- **REALTIME な生の数字（残高/P&L/loop稼働）= `bash ~/anicca/skills/self/colony-status.sh` を実行して確認する**。記憶で答えない。
- SSOT 全文 = `docs/superpowers/specs/2026-07-03-anicca-colony-architecture-design.md`（§16 earn rails, §17 master TODO, §19 instance 内訳）。
- 「稼いだ」= realized profit>0 が ledger（`~/anicca/skills/earn/polymarket-trade/SKILL.md`）に載った時のみ。盛らない。

## 実行環境

Mac Mini（`anicca-mac-mini-1`、Tailscale 100.99.82.95）で直接実行する。自分自身に SSH しない。MacBook へは `ssh cbns03@100.108.140.123` で接続できる。VPS は使わない。

## ローカル + push 先マップ

| ローカル path | Push 先 origin | 役割 |
|---|---|---|
| `~/anicca-project/`（products working tree はここ1つのみ） | `github.com/Daisuke134/anicca-products`（public） | iOS/web/api/mobile（aniccaai.com 含む）。Anicca instance からの直接 write は禁止、Dais + Claude Code のみ編集可 |
| `~/.openclaw/` | `github.com/Daisuke134/anicca-dais`（private） | 本番 Anicca-OpenClaw: gateway/cron/skills/state |
| `~/anicca/` | `github.com/Daisuke134/anicca`（public OSS） | OSS フレームワーク本体 |

push は各 path で `git push` 単体。push前に必ず `git remote -v && git branch -vv` で origin を確認する。GitHub Actions の新規追加は禁止（`.github/workflows/netlify-deploy.yml` の1個のみ）— 定期実行/cron は全て `~/.openclaw/cron/jobs.json`（OpenClaw gateway）が正本。

## ブランチ & デプロイ

| ブランチ | 役割 | Railway |
|---|---|---|
| main | Production | 自動デプロイ |
| dev | 開発（trunk） | Staging 自動デプロイ |
| release/x.x.x | App Store 提出 | - |

フロー: dev → テスト → main → release/x.x.x → App Store。Fastlane 必須（`cd aniccaios && fastlane <lane>`、xcodebuild 直接禁止）。提出前に `greenlight preflight <app_dir>` で CRITICAL=0 を確認する。

### git 運用（GitHub Flow、常時のホーム = `dev`）

```
1. git fetch && git checkout dev && git pull
2. git checkout -b feature/<名前>（ドキュメントのみ dev 直接可）
3. 1編集 = 即 git add && commit && push
4. git push -u origin feature/<名前>
5. gh pr create --base dev
6. merge → dev 自動デプロイ（staging 検証）
7. 良ければ dev → main（PR）→ main 自動デプロイ
8. App Store 提出時のみ main から release/x.x.x
```

commit/push 前に必ず `git fetch` して origin より遅れていないか確認する。branch の終着は merge か削除の2択（`gh pr merge --merge --delete-branch` で同時実行）。openclaw/agent/dotfiles の mirror や `~/.openclaw` state はこの製品 repo に commit しない。自動強制 = lefthook（`lefthook.yml`、pre-push で drift 検知）。

## 並列開発（Git Worktrees）

原則 worktree、ドキュメント変更のみ dev 直接可。同じブランチで複数エージェントが作業しない。

```bash
git worktree add .worktrees/<task> -b feature/<task>
cd .worktrees/<task>
# 完了後
cd /path/to/anicca-project && git merge feature/<task>
git worktree remove .worktrees/<task> && git branch -d feature/<task>
```

各 worktree は独自 spec を持ち、触るファイルを spec 境界に明記する。バックエンドは worktree push で自動デプロイされないため `cd apps/api && railway up --environment staging` を使う。複数エージェントのバックエンドデプロイは順番に行う。

## ツール優先順位（このプロジェクト固有分）

| タスク | 使うツール | 禁止 |
|---|---|---|
| ドキュメント/SDK/API の実装方法を調べる | Context7 CLI: `npx ctx7@latest library <name>` → `npx ctx7@latest docs <libraryId> <query>` | 古い知識での実装、docs 当て推量 |
| iOS E2E | `mcp__maestro__*` | maestro CLI 直接 |
| ビルド/テスト | `cd aniccaios && fastlane <lane>` | xcodebuild 直接 |

Web検索/コード内シンボル操作/ブラウザ/Mac操作の既定は `~/.claude/CLAUDE.md` 参照。

## プロジェクト概要

**Anicca** = プロアクティブ行動変容エージェント。

| 項目 | 値 |
|---|---|
| iOS | Swift/SwiftUI（iOS 15+, Xcode 16+） |
| API | Node.js/Express（Railway） |
| DB | PostgreSQL/Prisma |
| 決済 | RevenueCat（$9.99/月, $49.99/年） |
| 分析 | Mixpanel（Anicca 専用、factory アプリには入れない） |
| E2E | Maestro |
| Agent | OpenClaw（`agent_docs/openclaw_integration.md`） |

## ミニマム folder tree

```
~/anicca-project/                          # products folder（唯一）
├── aniccaios/                             # iOS Swift app（release は fastlane）
├── apps/
│   ├── api/                               # Node/Express API (Railway)
│   └── landing/                           # Next.js → aniccaai.com
│       ├── public/dashboard.json          # dashboard-sync（Dais owned）が render、Anicca 直接 write 禁止
│       ├── content/blog/                  # Dais owned blog factory
│       └── data/research/                 # topic queue（Dais owned）
├── mobile-apps/                           # factory apps
├── .github/workflows/netlify-deploy.yml   # これ1個だけ
└── docs/superpowers/{specs,plans}/        # SDD spec + plan

~/.openclaw/                               # 本番 Anicca-OpenClaw、cron 正本
├── skills/  cron/jobs.json  gateway/  state/
├── .env（chmod 600、secrets, git ignore）
└── CONSTITUTION.md  IDENTITY.md  SOUL.md

~/anicca/                                  # OSS フレームワーク
├── skills/  identity/  runtime/  services/
├── control-room/  install.sh
└── adapters/  templates/
```

## Anicca Architecture — 1 instance + human-funded claude loops、dashboard read-only

```
┌────────────────────────────────────────────────────────────────┐
│         Anicca: OpenClaw instance + human-funded loops         │
├────────────────────────────────────────────────────────────────┤
│  #1 Anicca-OpenClaw（Dais 専用、本体）                          │
│    body : ~/.openclaw/                                         │
│    repo : anicca-dais（private）                                │
│    fuel : ChatGPT Plus 課金 / provider = openai-codex           │
│    cron : ~221                                                  │
│                                                                  │
│  human-funded claude ループ群（このセッション種別）              │
│    fuel : Anthropic subscription（Dais の Claude Code/Pro）      │
│    role : 自律 earn（wallet 0x810f 等）+ 開発 ad-hoc            │
│                                                                  │
│  どちらも自分の body にのみ書く（state/*.jsonl, ledger, cron log） │
│                    │                                             │
│                    ▼                                            │
│  dashboard-sync（Dais owned、Anicca ではない）                  │
│    OpenClaw state を fetch → dashboard.json を render           │
│    → anicca-products へ push → netlify 自動デプロイ             │
│    → aniccaai.com/dashboard                                     │
└────────────────────────────────────────────────────────────────┘
```

### aniccaai.com への書き込み制限

| 主体 | 書いてよい場所 | 書いてはいけない場所 |
|---|---|---|
| Anicca-OpenClaw | `~/.openclaw/state/`, `cron/`, `skills/`（自分の body） | `~/anicca-project/apps/landing/**`、anicca-products repo |
| dashboard-sync（Dais owned） | `dashboard.json`（render 結果） | Anicca state の改変 |
| Claude Code（開発 IDE） | 全 path、Dais 指示時 | 監視なしの unsupervised cron / aniccaai.com push |

Anicca instance の自己更新は body file を書くのみ → dashboard-sync が pull して dashboard.json を render → aniccaai.com に反映する。aniccaai.com は Dais のサイトであり、Anicca は write 権限を持たない。

### fuel 確認

```bash
openclaw models status | head -5     # → openai-codex
# Claude Code: system prompt の "Powered by ..." 表示、出ないなら /model
```

## 技術 gotcha

iOS/SwiftUI/RevenueCat/Xcode/App Store Connect 固有の既知の問題と回避策 → `.claude/rules/platform-gotchas.md`。FK 制約安全パターン（Prisma upsert 前の存在チェック）→ `.claude/rules/coding-style.md`。codex-review を VCSDD フェーズのどこに挟むか → `.claude/rules/dev-workflow.md`。git commit/PR 詳細 → `.claude/rules/git-workflow.md`。

## 参照先（必要時に Read）

| ファイル | いつ読む |
|---|---|
| `.cursor/plans/reference/secrets.md` | デプロイ・Secret 設定時 |
| `.cursor/plans/reference/infrastructure.md` | インフラ・Railway 作業時 |
| `agent_docs/openclaw_integration.md` | OpenClaw 作業時 |

## 言語

回答は常に日本語。

@.claude/active-team.md
