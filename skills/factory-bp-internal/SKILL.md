---
name: factory-bp-internal
description: "過去のビルドエラーから学び、スキルにCRITICAL RULEを追加する。Use when triggered by factory-bp-internal cron or told to 'learn from build errors'."
---

# factory-bp-internal

BP-1: 「Keep each skill focused on one job」
Source: OpenClaw Skills Guide (https://openclaw-ai.online/skills/)

Source: Addy Osmani — Self-Improving Coding Agents (https://addyosmani.com/blog/self-improving-agents/)
Quote: 「By resetting its memory each iteration, the agent avoids accumulating confusion」

## 役割

過去のビルドエラーから学び、繰り返しエラーをCRITICAL RULEとしてスキルに追加する。
**CCは使わない。Anicca（OpenClaw）が直接実行する。**

## 手順

### 1. エラーログ読み込み

```bash
# 全アプリの ERRORS.md を読む
find /Users/anicca/anicca-project/mobile-apps/ -name "ERRORS.md" -path "*/.learnings/*"

# 全アプリの LEARNINGS.md を読む
find /Users/anicca/anicca-project/mobile-apps/ -name "LEARNINGS.md" -path "*/.learnings/*"
```

各ファイルを `read` ツールで読む。

### 2. パターン分析

- 全エラーを集約
- 同じエラーが3回以上（Recurrence-Count >= 3）繰り返されているものを抽出
- 繰り返しエラーがない場合: 「繰り返しエラーなし」と報告して終了

### 3. 原因調査 + レシピ修正

繰り返しエラーごとに以下を実行:

1. **エラーメッセージを読む**
   例: "validate.sh: found RevenueCatUI in docs/"

2. **レシピ(SKILL.md)の該当箇所を探す**
   mobileapp-builder/SKILL.md を read で開く
   エラーに関連するセクションを見つける

3. **正しいやり方を調べる**
   web_search で原因と修正方法を検索

4. **レシピの該当箇所を直接修正する**
   edit tool でSKILL.mdの問題行を直す
   ★ルール追記ではなく、元のレシピの間違い/古い記述を書き換える
   ★修正には必ずSource + URL + 引用を付ける:
   ```
   # FIX by factory-bp-internal YYYY-MM-DD
   # Source: [URL]
   # Quote: "[原文]"
   # Recurrence: N回
   ```

5. **ralph.shの設定も必要なら修正する**

### 4. git commit

```bash
cd /Users/anicca/anicca-project && git add -A && git commit -m "factory-bp-internal: [日付] [追加したルール数]"
```

### 5. Slack報告

Slack #metrics ({{profile.channels.reportChannel}}) に以下を投稿（**短く保つこと**）:
```
🧠 internal-bp完了 | エラーファイル:N | 繰り返し:N | ルール追加:N
```

**重要**: メッセージは100文字以内に抑える。長いサマリーはファイルに保存し、Slackには最小限の報告のみ。
