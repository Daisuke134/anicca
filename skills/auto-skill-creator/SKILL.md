---
name: auto-skill-creator
description: スキルを探して見つかればインストール、なければ新規ビルド方法を案内する。Use when user says 「このスキルを作って」「毎日Xするスキルが欲しい」「〜を自動化するスキルはある？」or any skill creation/discovery request.
---

# Auto Skill Creator

skill.sh を検索 → 見つかればインストール → 見つからなければ skill-creator を案内する。

## 実行コマンド

```bash
export PATH=/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:$PATH
cd /Users/anicca/.openclaw/skills/auto-skill-creator

# 実行（Slack投稿）
node scripts/creator.js "毎日arXiv論文を要約するスキルを作って"

# DRY_RUN（Slack投稿なし）
DRY_RUN=1 node scripts/creator.js "Hacker Newsをまとめるスキル"

# テスト
npm test
```

## スクリプト構成

| ファイル | 役割 |
|---------|------|
| `scripts/search.js` | `npx skills find` 実行・出力パース |
| `scripts/creator.js` | エントリーポイント。検索→インストール or 案内 |
| `scripts/utils/slack.js` | openclaw message send ラッパー |

## 動作フロー

```
ユーザー依頼
    ↓
skill.sh で検索（npx skills find）
    ↓
  見つかった → インストール（npx skills add）→ 完了を報告
    ↓
  見つからない → skill-creator の使い方を案内
```

## Cronなし（オンデマンドのみ）

Aniccaが「〜するスキルを作って」等のSlackメッセージを受信したとき自動実行。
