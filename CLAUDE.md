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
| Build/Verify | `vcsdd:vcsdd-init` → `vcsdd:vcsdd-spec` → `vcsdd:vcsdd-spec-review` → `vcsdd:vcsdd-tdd` → `vcsdd:vcsdd-impl` → `vcsdd:vcsdd-adversary` → `vcsdd:vcsdd-harden` → `vcsdd:vcsdd-converge` | EARS要件→fresh-context adversary が spec review PASS→RED→GREEN/refactor→実装レビュー→formal hardening→4次元収束確認。**実コマンドを呼んで `.vcsdd/features/<name>/state.json` の phase を進める**（SPEC本文への手書き追記だけでは進捗とみなさない）。小規模タスクは `mode: lean` でよいがフェーズは飛ばさない。**★token 上限（HARD）= `~/.claude/CLAUDE.md`「VCSDD の token 上限」節が正本: spec レビューの adversary は1ラウンドのみ／spec は1ページ（不変条件の箇条書き、EARS大全禁止）／subagent の resume 禁止／本当のゲートは negative test／3回 FAIL で handover★** codex-review をどこに挟むかは `.claude/rules/dev-workflow.md` 参照 |
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

products working tree = `~/anicca-project/`（→ anicca-products public）、`~/.openclaw/`（→ anicca-dais private, cron正本）、`~/anicca/`（→ anicca OSS public）。詳細表・push規約 → CLAUDE.local.md「ローカル + push 先マップ（詳細）」。

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

正本 → `.claude/rules/worktree.md`。原則 worktree、ドキュメント変更のみ dev 直接可。同じブランチで複数エージェントが作業しない。詳細コマンド → CLAUDE.local.md「並列開発（Git Worktrees、詳細）」。

## ツール優先順位（このプロジェクト固有分）

| タスク | 使うツール | 禁止 |
|---|---|---|
| ドキュメント/SDK/API の実装方法を調べる | Context7 CLI: `npx ctx7@latest library <name>` → `npx ctx7@latest docs <libraryId> <query>` | 古い知識での実装、docs 当て推量 |
| iOS E2E | `mcp__maestro__*` | maestro CLI 直接 |
| ビルド/テスト | `cd aniccaios && fastlane <lane>` | xcodebuild 直接 |

Web検索/コード内シンボル操作/ブラウザ/Mac操作の既定は `~/.claude/CLAUDE.md` 参照。

## プロジェクト概要

**Anicca** = プロアクティブ行動変容エージェント（iOS Swift/SwiftUI + Node/Express API + PostgreSQL/Prisma + RevenueCat + OpenClaw agent）。スタック詳細表・folder tree・アーキテクチャ図・write制限・fuel確認 → CLAUDE.local.md「プロジェクト概要」「ミニマム folder tree」「Anicca Architecture」。

## 技術 gotcha

iOS/SwiftUI/RevenueCat/Xcode/App Store Connect 固有の既知の問題と回避策 → `.claude/rules/platform-gotchas.md`。FK 制約安全パターン（Prisma upsert 前の存在チェック）→ `.claude/rules/coding-style.md`。codex-review を VCSDD フェーズのどこに挟むか → `.claude/rules/dev-workflow.md`。git commit/PR 詳細 → `.claude/rules/git-workflow.md`。

## 参照先（必要時に Read）

デプロイ/Secret時→`.cursor/plans/reference/secrets.md`、インフラ/Railway時→`.cursor/plans/reference/infrastructure.md`、OpenClaw作業時→`agent_docs/openclaw_integration.md`。一覧 → CLAUDE.local.md「参照先」。

## 言語

回答は常に日本語。

@.claude/active-team.md
