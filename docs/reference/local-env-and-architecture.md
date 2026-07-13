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

## （CLAUDE.md から移動）参照先（必要時に Read）

| ファイル | いつ読む |
|---|---|
| `.cursor/plans/reference/secrets.md` | デプロイ・Secret 設定時 |
| `.cursor/plans/reference/infrastructure.md` | インフラ・Railway 作業時 |
| `agent_docs/openclaw_integration.md` | OpenClaw 作業時 |
