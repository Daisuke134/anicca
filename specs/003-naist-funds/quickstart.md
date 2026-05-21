# Quickstart: naist-funds

**Date**: 2026-02-24

## セットアップ（Mac Mini上）

```bash
# 1. スキルディレクトリ作成
mkdir -p /Users/anicca/.openclaw/skills/naist-funds/{scripts/utils,data,tests}

# 2. package.json 作成・依存インストール
cd /Users/anicca/.openclaw/skills/naist-funds
npm init -y
npm install --save-dev jest

# 3. データファイル初期化
echo '{"notified":[],"lastFetchedAt":null}' > data/cache.json
# guides.json は実装時に生成

# 4. テスト実行（TDD）
npm test

# 5. 手動実行テスト
node scripts/scan.js

# 6. cron 登録（jobs.json）
# "15 9 * * 1,4" で scan.js を実行
```

## 環境変数（Mac Mini .env）

```
SLACK_CHANNEL_ID=C091G3PKHL2  # naist-agentチャンネル
```

## 開発時のみ（DRY RUN）

```bash
DRY_RUN=1 node scripts/scan.js
# → Slackに投稿せず、stdoutに投稿予定内容を出力
```
