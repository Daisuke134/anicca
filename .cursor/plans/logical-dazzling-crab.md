# mobileapp-builder v2 実装プラン

## Context

`github.com/Daisuke134/mobileapp-builder` を OSS として誰でも使えるレベルに改善する。
現状は prerequisites が不明で、サブスキルの API Keys が何が必要か書いていない。
Pencil MCP / Maestro MCP のインストール手順もない。

**ゴール:** `npx skills add Daisuke134/mobileapp-builder -g -y` → README の Setup セクションを読む → 全設定完了 → 動く。

---

## 変更ファイル（4ファイルのみ）

| ファイル | 場所 | 変更内容 |
|---------|------|---------|
| `SKILL.md` | リポジトリルート | description 更新 + STOP 1/2/3 明示 + サブスキル install 確認を PHASE 0 冒頭に追加 |
| `README.md` | リポジトリルート | Prerequisites セクション全面改訂 |
| `SETUP.md`（新規） | リポジトリルート | ゼロから動かすための完全セットアップガイド |
| `scripts/check-prerequisites.sh`（新規） | `scripts/` | 必要ツール自動チェック + 不足時コマンド案内 |

**14 PHASE のロジックには一切触らない（実証済み・変更禁止）。**

---

## 1. SKILL.md の変更

### description 更新（現状 → 変更後）

```yaml
# 変更後（1024文字以内）
description: Builds and ships a Swift/SwiftUI iOS app to the App Store from a natural language idea.
Handles all phases autonomously: trend research (X + TikTok + App Store) → SDD spec → Xcode scaffold →
SwiftUI implementation → landing page → ASC subscription setup → IAP 175-territory pricing →
app icon + App Store screenshots → build → TestFlight → App Store submission.
Three human stops: (1) spec approval before build, (2) TestFlight testing before submission,
(3) App Privacy manual setup. Use when told to "build an app", "ship an iOS app",
"make money with apps", or when triggered by app-factory cron.
```

### PHASE 0 冒頭にサブスキル確認を追加

```
### PHASE 0: PRE-FLIGHT（新規 — 既存 PHASE 0 の前に実行）

# 必要なサブスキルが入っているか確認して、なければ install
required_skills=(x-research tiktok-research apify-trend-analysis ralph-autonomous-dev screenshot-creator slack-approval)
for skill in "${required_skills[@]}"; do
  if ! npx skills list | grep -q "$skill"; then
    npx skills add Daisuke134/anicca-products@$skill -g -y
  fi
done
```

### STOP 1 / STOP 2 / STOP 3 の明示

各 STOP の前後に以下のフレームを追加：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛑 STOP 1 — Spec 承認（PHASE 0.5 完了）
━━━━━━━━━━━━━━━━━━━━━━━━━━━
[slack-approval スキルで承認待ち]
承認 → PHASE 1 / 拒否 → PHASE 0.5 再実行
━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛑 STOP 2 — TestFlight テスト（PHASE 10 完了）
━━━━━━━━━━━━━━━━━━━━━━━━━━━
[slack-approval スキルで承認待ち]
承認 → PHASE 11 / 修正 → PHASE 3 再実行
━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛑 STOP 3 — App Privacy 手動設定（PHASE 11.5）
━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ユーザーが「完了」と言ったら PHASE 12 即実行]
━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 2. SETUP.md（新規 — 最重要ファイル）

構成（初心者がゼロから読んで全部設定できる）：

### Section 1: 必須アカウント（作るだけ）

| # | アカウント | URL | 費用 |
|---|-----------|-----|------|
| 1 | Apple Developer Program | developer.apple.com/enroll | $99/年 |
| 2 | App Store Connect API Key | ASC → Users and Access → Keys → + | 無料 |
| 3 | RevenueCat | app.revenuecat.com | 無料（$2.5k MRR まで） |
| 4 | Mixpanel | mixpanel.com/register | 無料（20M events/月） |
| 5 | X Developer Portal | developer.twitter.com | Basic $100/月 or Free tier |
| 6 | Apify | apify.com | 無料($5クレジット付き) |
| 7 | Google Cloud（Gemini） | cloud.google.com | 無料枠あり |
| 8 | OpenAI | platform.openai.com | 使った分だけ |
| 9 | Slack workspace | slack.com | 無料 |

### Section 2: 環境変数（.env に追記）

```bash
# ~/.config/mobileapp-builder/.env に保存

# Apple / ASC
ASC_KEY_ID=D637C7RGFN            # ASC → Users and Access → Keys
ASC_ISSUER_ID=f53272d9-...       # 同上
ASC_KEY_PATH=~/Downloads/AuthKey_D637C7RGFN.p8

# RevenueCat
REVENUECAT_API_KEY=sk_...        # RC Dashboard → Project Settings → API Keys

# Mixpanel
MIXPANEL_TOKEN=abc123            # Mixpanel → Project Settings

# X (Twitter) Research
X_BEARER_TOKEN=AAAA...           # developer.twitter.com → App → Keys

# Apify（TikTok + Trend Analysis 共通）
APIFY_TOKEN=apify_api_...        # apify.com → Settings → Integrations

# Gemini（TikTok Research の分析に使用）
GEMINI_API_KEY=AIza...           # console.cloud.google.com → APIs → Gemini

# OpenAI（アイコン生成）
OPENAI_API_KEY=sk-...            # platform.openai.com → API keys

# Slack（承認通知）
SLACK_BOT_TOKEN=xoxb-...         # api.slack.com → app → OAuth
SLACK_APP_TOKEN=xapp-...         # api.slack.com → app → App-Level Tokens
SLACK_CHANNEL_ID=C...            # 通知を受け取るチャンネルID
```

### Section 3: CLIツール（1コマンドずつ）

```bash
# 1. asc（App Store Connect CLI）
brew install nickvdyck/tap/asc

# 2. fastlane
brew install fastlane

# 3. greenlight（提出前チェック）
cd /tmp && git clone https://github.com/RevylAI/greenlight.git \
  && cd greenlight && make build \
  && sudo cp build/greenlight /usr/local/bin/

# 4. imagemagick（アイコン背景合成）
brew install imagemagick

# 5. snapai（AI アイコン生成）
npm install -g snapai
npx snapai config --openai-api-key $OPENAI_API_KEY

# 6. Python 依存ライブラリ
pip3 install Pillow requests PyJWT

# 7. ios-deploy
brew install ios-deploy

# 8. 全部確認
bash ~/.claude/skills/mobileapp-builder/scripts/check-prerequisites.sh
```

### Section 4: MCP のインストール（Claude Code）

```jsonc
// ~/Library/Application Support/Claude/claude_desktop_config.json に追記

{
  "mcpServers": {
    "pencil": {
      "command": "npx",
      "args": ["-y", "@pencil-so/mcp"]
    },
    "maestro": {
      "command": "npx",
      "args": ["-y", "@maestro-org/mcp-server"]
    }
  }
}
```

追記後に Claude Code を再起動して確認：
- `mcp__pencil__get_editor_state` が使えるか
- `mcp__maestro__list_devices` が使えるか

### Section 5: Claude Code サブスキルのインストール

```bash
npx skills add Daisuke134/mobileapp-builder -g -y
npx skills add Daisuke134/anicca-products@x-research -g -y
npx skills add Daisuke134/anicca-products@tiktok-research -g -y
npx skills add Daisuke134/anicca-products@apify-trend-analysis -g -y
npx skills add Daisuke134/anicca-products@ralph-autonomous-dev -g -y
npx skills add Daisuke134/anicca-products@screenshot-creator -g -y
npx skills add Daisuke134/anicca-products@slack-approval -g -y
npx skills add code-with-beto/skills@app-icon -g -y
```

### Section 6: Fastlane の設定（Xcode プロジェクト側）

```ruby
# Fastfile の必須変数（各アプリの Fastfile に設定）
API_KEY_ID     = "D637C7RGFN"
API_ISSUER_ID  = "f53272d9-c12d-4d9d-811c-4eb658284e74"
API_KEY_PATH   = "#{ENV['HOME']}/Downloads/AuthKey_D637C7RGFN.p8"
```

---

## 3. scripts/check-prerequisites.sh（新規）

確認項目と動作：

```bash
#!/bin/bash
# mobileapp-builder prerequisites checker

PASS=0; FAIL=0

check() {
  local name="$1"; local cmd="$2"; local install="$3"
  if eval "$cmd" &>/dev/null; then
    echo "✅ $name"
    ((PASS++))
  else
    echo "❌ $name → install: $install"
    ((FAIL++))
  fi
}

# CLI ツール
check "asc"         "asc --version"                    "brew install nickvdyck/tap/asc"
check "fastlane"    "fastlane --version"                "brew install fastlane"
check "greenlight"  "greenlight --version"              "cd /tmp && git clone https://github.com/RevylAI/greenlight.git && cd greenlight && make build && sudo cp build/greenlight /usr/local/bin/"
check "imagemagick" "convert --version"                 "brew install imagemagick"
check "snapai"      "npx snapai --version"              "npm install -g snapai"
check "Python PIL"  "python3 -c 'import PIL'"           "pip3 install Pillow"
check "PyJWT"       "python3 -c 'import jwt'"           "pip3 install PyJWT"
check "ios-deploy"  "ios-deploy --version"              "brew install ios-deploy"

# 環境変数
env_check() {
  local name="$1"
  [ -n "${!name}" ] && echo "✅ $name" && ((PASS++)) || { echo "❌ $name → ~/.config/mobileapp-builder/.env に設定"; ((FAIL++)); }
}
env_check X_BEARER_TOKEN
env_check APIFY_TOKEN
env_check GEMINI_API_KEY
env_check OPENAI_API_KEY
env_check SLACK_BOT_TOKEN

# ASC API Key ファイル
if ls ~/Downloads/AuthKey_*.p8 &>/dev/null; then
  echo "✅ ASC API Key (.p8)"
  ((PASS++))
else
  echo "❌ ASC API Key (.p8) → ASC → Users and Access → Keys からダウンロード"
  ((FAIL++))
fi

echo ""
echo "Result: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && echo "🚀 All prerequisites met. Ready to build!" || echo "🔧 Fix the above items and re-run."
```

---

## 4. README.md の変更

### Prerequisites セクションを以下に全面改訂

```markdown
## Prerequisites

Run the checker first:
\`\`\`bash
bash ~/.claude/skills/mobileapp-builder/scripts/check-prerequisites.sh
\`\`\`

For full setup instructions → **[SETUP.md](./SETUP.md)**

Short summary of what you need:
- Apple Developer account ($99/yr) + ASC API Key
- RevenueCat account (free)
- Apify account (free) + X Developer account
- OpenAI API key (icon generation)
- Slack workspace (approvals)
- Pencil MCP + Maestro MCP installed in Claude Code
```

---

## Spec ファイルへの追記事項

既存 spec `.cursor/plans/ios/1.6.3/mobileapp-builder-v2-spec.md` の
「Prerequisites 定義」セクションを以下で**置き換える**：

### 環境変数（.env）

| 変数名 | 用途 | 取得先 |
|--------|------|--------|
| `ASC_KEY_ID` | App Store Connect API | ASC → Users and Access → Keys |
| `ASC_ISSUER_ID` | ASC API | 同上 |
| `ASC_KEY_PATH` | ASC API p8ファイルパス | 同上（ダウンロード） |
| `REVENUECAT_API_KEY` | RevenueCat 操作 | RC Dashboard → Project Settings |
| `MIXPANEL_TOKEN` | イベント送信 | Mixpanel → Project Settings |
| `X_BEARER_TOKEN` | x-research スキル | developer.twitter.com → App → Keys |
| `APIFY_TOKEN` | tiktok-research + apify-trend-analysis | apify.com → Settings |
| `GEMINI_API_KEY` | tiktok-research の AI 分析 | Google Cloud → Gemini API |
| `OPENAI_API_KEY` | アイコン生成（snapai） | platform.openai.com |
| `SLACK_BOT_TOKEN` | slack-approval（承認通知） | api.slack.com → app |
| `SLACK_APP_TOKEN` | slack-approval（Socket Mode） | api.slack.com → app |
| `SLACK_CHANNEL_ID` | slack-approval（通知チャンネル） | Slack チャンネルの ID |

### MCP インストール（claude_desktop_config.json）

```jsonc
{
  "mcpServers": {
    "pencil": { "command": "npx", "args": ["-y", "@pencil-so/mcp"] },
    "maestro": { "command": "npx", "args": ["-y", "@maestro-org/mcp-server"] }
  }
}
```

---

## 受け入れ条件（最終確認）

| # | 条件 | 確認方法 |
|---|------|---------|
| AC1 | `npx skills add Daisuke134/mobileapp-builder -g -y` 1コマンドで完了 | `npx skills list \| grep mobileapp-builder` |
| AC2 | `check-prerequisites.sh` が全項目 ✅ を出す | スクリプト実行 |
| AC3 | STOP 1: spec.md 生成後に Slack 承認待ちで停止 | 手動テスト |
| AC4 | STOP 2: TestFlight プッシュ後に Slack 承認待ちで停止 | 手動テスト |
| AC5 | STOP 3: App Privacy 手順を案内して「完了」待ちで停止 | 手動テスト |
| AC6 | SETUP.md の手順だけで全設定が完了する | 別の人間が読んで実行できるか確認 |
| AC7 | README の Prerequisites が SETUP.md へ誘導している | 目視確認 |

---

## 実施順序

1. `SETUP.md` 新規作成（最優先 — 全設定の起点）
2. `scripts/check-prerequisites.sh` 新規作成
3. `SKILL.md` の description 更新 + STOP 1/2/3 追加
4. `README.md` の Prerequisites セクション更新

---

## 検証方法

```bash
# 1. README を読んで SETUP.md を開く
open https://github.com/Daisuke134/mobileapp-builder/blob/main/SETUP.md

# 2. check-prerequisites.sh を実行して全 ✅ を確認
bash ~/.claude/skills/mobileapp-builder/scripts/check-prerequisites.sh

# 3. Claude Code で「アプリ作って」と言って STOP 1 が出るか確認
# → Slack に承認メッセージが届くか確認
```
