# CLAUDE.local.md — Personal Overrides (gitignored)
# Add personal preferences that should NOT be committed to the repo.
# Example:
# - Custom model preferences
# - Local file paths
# - Personal workflow tweaks

## Autonomy / Permissions

Run with full autonomous execution by default. Do not stop for human permission
unless an action is irreversible and outside the user's standing instructions.
Prefer doing the work, verifying it, and reporting the result.

## （CLAUDE.md から移動）ローカル + push 先マップ（詳細）

| ローカル path | Push 先 origin | 役割 |
|---|---|---|
| `~/anicca-project/`（products working tree はここ1つのみ） | `github.com/Daisuke134/anicca-products`（public） | iOS/web/api/mobile（aniccaai.com 含む）。Anicca instance からの直接 write は禁止、Dais + Claude Code のみ編集可 |
| `~/.openclaw/` | `github.com/Daisuke134/anicca-dais`（private） | 本番 Anicca-OpenClaw: gateway/cron/skills/state |
| `~/anicca/` | `github.com/Daisuke134/anicca`（public OSS） | OSS フレームワーク本体 |

push は各 path で `git push` 単体。push前に必ず `git remote -v && git branch -vv` で origin を確認する。GitHub Actions の新規追加は禁止（`.github/workflows/netlify-deploy.yml` の1個のみ）— 定期実行/cron は全て `~/.openclaw/cron/jobs.json`（OpenClaw gateway）が正本。

## （CLAUDE.md から移動）並列開発（Git Worktrees、詳細）

原則 worktree、ドキュメント変更のみ dev 直接可。同じブランチで複数エージェントが作業しない。

```bash
git worktree add .worktrees/<task> -b feature/<task>
cd .worktrees/<task>
# 完了後
cd /path/to/anicca-project && git merge feature/<task>
git worktree remove .worktrees/<task> && git branch -d feature/<task>
```

各 worktree は独自 spec を持ち、触るファイルを spec 境界に明記する。バックエンドは worktree push で自動デプロイされないため `cd apps/api && railway up --environment staging` を使う。複数エージェントのバックエンドデプロイは順番に行う。

## （CLAUDE.md から移動）プロジェクト概要

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

## （CLAUDE.md から移動）ミニマム folder tree

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

## （CLAUDE.md から移動）Anicca Architecture — 1 instance + human-funded claude loops、dashboard read-only

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

## Fleet全体の現状（2026-07-21、cold reader向け。詳細は各 spec/doc へ）

このセクションは Mac Mini 上で Fable(Claude)+Sol(Codex) が完走した infra 作業の要約。新しい machine/cloud session/Codex session がゼロから読んでも全体像が分かるように書く。詳細な実測値・手順は各リンク先の spec/doc が正本（このセクションは要約のみ、重複させたら古い方を消す）。

### 1. Context floor 削減（Claude Code）
起動時固定費 179.3k/200k(90%) → 実測 86.8k/200k(43%)。手段: `ENABLE_TOOL_SEARCH=true`（MCP tool 遅延ロード）/ 未使用 builtin tool の bare-deny / 未使用 plugin 7本 disable / project agents 15→4体 / Serena excluded_tools / `includeGitInstructions:false` / CLAUDE.md の path分割（`.claude/rules/*.md`）。詳細 → `docs/superpowers/specs/2026-07-20-context-floor-and-handover-simplify-spec.md`。`/handover` は「spec+handover path だけ含む Start/Go 2 プロンプト」形式に変更済み（`.claude/commands/handover.md`）。

### 2. Skills 単一実体化（Claude/Codex 共有）
**正本 = `~/.agents/skills`**（実体66、Codex 公式 user scope）。`~/.claude/skills/<name>` は per-skill symlink（11本、whole-dir symlink は禁止）。GitHub 双方向 sync は既存 launchd `ai.anicca.agents-skills-sync`（private repo `Daisuke134/anicca-agents-skills`）— 新規 sync は作らない。

### 3. Claude/Codex ツール parity
両者とも `crwl`(crawl4ai CLI)/`ctx7`/`x-search-cdp`/`gh` を既定にし、`WebSearch`/`WebFetch` 禁止で揃える。Codex 側は repo root `AGENTS.md`（40行、この上のセクション）+ global `~/.codex/AGENTS.md`。rulesync ツールは rule 生成用途では棄却（493行への全concat化で floor 悪化）、変換部分のみ `codex-parity/` に保存。

### 4. Global rules / secrets 単一化（chezmoi、Phase 2）
`~/.claude/CLAUDE.md`（Dais 規律の正本）と `~/.codex/AGENTS.md`（Codex 側、同内容を template から生成）はどちらも `~/.config/ai/common-rules.md` を共有元にする。Claude は `@~/.config/ai/common-rules.md` import、Codex は chezmoi の `.chezmoitemplates/common-rules.md` から生成。
管理ツール = **chezmoi**、source = private repo `Daisuke134/ai-config`。secret混在ファイル（`settings.json`/`config.toml`/`.zshrc`）は age 暗号化（private key は `~/.config/chezmoi/key.txt` mode 600、**local-only**＝この machine を失うと復号不能という残余リスクを受容中。1Password バックアップは要件から外した）。
新 machine/cloud VM 再現 = `chezmoi init --apply https://github.com/Daisuke134/ai-config` 1コマンド。gate = `chezmoi diff`(空) + `chezmoi doctor`(exit 0) + gitleaks(0 leaks)。実装ログ・修正履歴 → `docs/loop-engineering/49-single-source-ai-config-2026-07-20.md`。

### 5. Cloud/Mobile 移行
`~/.openclaw` `~/anicca` `~/anicca-project/docs` を30分毎に gateway cron（openclaw 側、cron id `a4577898-...`）が GitHub へ auto-sync（`cloud-migration/auto-sync.sh`、gitleaks staged-diff scan付き）。`docs/STATUS-live.md` が phone から見える colony 状態の窓。Phone 側の接続手順（Claude iOS Code tab の GitHub App 連携、Termius+Tailscale SSH、緊急コマンド集）→ `docs/reference/phone-runbook.md`。全体 spec → `docs/superpowers/specs/2026-07-20-cloud-mobile-migration-spec.md`。

### 6. vcsdd は Claude 専用（Codex には無い、意図的）
`vcsdd`(spec/adversary/harden 等の phase gate) は Claude Code の marketplace plugin であり、Codex CLI には同等の仕組みがない（Codex 側の対応物は `~/.codex/prompts` だが未導入）。これはバグではなく設計: GLVS の Verify(vcsdd phase 管理) は常に Fable(Claude側) が担当し、Sol(Codex, `codex exec`)は brief を渡された実装 doer に徹する。Codex に vcsdd を移植する必要はない。

### 7. 分業（2026-07-20 Dais 裁定）
Fable = plan・spec 作成・**最終検証のみ**。Sol(`codex exec -m gpt-5.6-sol`) = build も execute も全部（実装・実走・cron登録・fix loop・spec更新・commit+push）。research subagent = 検索調査のみ。Fable は Sol の自己申告を信じず、必ず実 tool_result（cron実在/remote head/launchctl/on-chain 等）で独立検証してから完了とする。

## （CLAUDE.md から移動）参照先（必要時に Read）

| ファイル | いつ読む |
|---|---|
| `.cursor/plans/reference/secrets.md` | デプロイ・Secret 設定時 |
| `.cursor/plans/reference/infrastructure.md` | インフラ・Railway 作業時 |
| `agent_docs/openclaw_integration.md` | OpenClaw 作業時 |
