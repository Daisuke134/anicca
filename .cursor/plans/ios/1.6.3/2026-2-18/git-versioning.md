# Git Versioning — OpenClaw Workspace + Skills

## ベストプラクティス

Source: `/docs/concepts/agent-workspace.md`
> "Treat the workspace as private memory. Put it in a **private** git repo so it is backed up and recoverable."

> "Do not commit secrets. Even in a private repo, avoid storing secrets:
> - API keys, OAuth tokens, passwords, or private credentials
> - Anything under ~/.openclaw/
> - Raw dumps of chats or sensitive attachments"

## リポジトリ構成

| リポ | 公開/非公開 | 内容 |
|---|---|---|
| `Daisuke134/anicca.ai` | private（既存） | iOSアプリ + Backend |
| `Daisuke134/openclaw-workspace` | **private**（新規） | workspace（記憶・設定・出力） |
| `Daisuke134/anicca-skills` | **public/OSS**（新規） | skills（誰でもインストール可能） |

## workspace リポ（private）

### 含めるもの
- AGENTS.md, SOUL.md, TOOLS.md, IDENTITY.md, USER.md, HEARTBEAT.md, MEMORY.md
- memory/*.md
- daily-memory/*.md（memory/に統合後は不要）
- スキル出力ディレクトリ（app-metrics/, suffering/, etc.）

### 含めないもの（.gitignore）
Source: `agent-workspace.md` suggested .gitignore:
```gitignore
.DS_Store
.env
**/*.key
**/*.pem
**/secrets*
node_modules/
```

追加で除外:
```gitignore
# OpenClaw internal
.clawhub/
```

### 初回セットアップ手順
Source: `agent-workspace.md`
```bash
cd ~/.openclaw/workspace
git add AGENTS.md SOUL.md TOOLS.md IDENTITY.md USER.md HEARTBEAT.md memory/
git commit -m "Add agent workspace"

# GitHub CLI
gh repo create openclaw-workspace --private --source . --remote origin --push
```

## skills リポ（OSS）

### 含めるもの
- 各スキルのSKILL.md + スクリプト + 設定
- README.md（スキル一覧と使い方）

### 含めないもの
- APIキー、認証情報
- 出力データ（JSONファイル等）

### 構成
```
anicca-skills/
├── README.md
├── app-metrics/SKILL.md
├── app-nudge-sender/SKILL.md
├── app-reviews/SKILL.md
├── suffering-detector/SKILL.md
├── trend-hunter/SKILL.md
├── x-poster/SKILL.md
├── tiktok-poster/SKILL.md
├── ...
```

### インストール方法（他の人が使う場合）
```bash
# 個別スキル
clawhub install anicca-skills/<skill-name> --dir ~/.openclaw/skills

# または直接clone
git clone https://github.com/Daisuke134/anicca-skills.git ~/.openclaw/skills/anicca
```

## 実行手順（夜間）

1. workspace内の `.gitignore` 作成
2. 不要ファイル掃除（node_modules等）
3. 初回コミット
4. GitHub private repo作成 + push
5. skills用の別リポ作成
6. skills初回コミット + push

---

*作成: 2026-02-18 06:39 UTC*
*Source: `/docs/concepts/agent-workspace.md`*
