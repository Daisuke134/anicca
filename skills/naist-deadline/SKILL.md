---
name: naist-deadline
description: [DEPRECATED v1 — replaced by ~/.openclaw/skills/naist/ unified v2; this stub is kept for ledger continuity] {{profile.education.institution}}の課題・締切・提出期限を管理しSlackで通知する。Use when user says 「締切確認して」「締切追加して」「提出済みにして」「完了にして」「いつまで」「課題登録」「リマインド」or similar deadline/task management requests.
---

# naist-deadline

{{profile.education.institution}}の課題・締切・提出期限をJSONで管理し、Slackで登録・確認・完了・自動リマインドを行う。

## 締切一覧を確認する

```bash
export PATH=/opt/homebrew/bin:$PATH
node /Users/anicca/.openclaw/skills/naist-deadline/scripts/list.js
```

## 締切を追加する

```bash
export PATH=/opt/homebrew/bin:$PATH
node /Users/anicca/.openclaw/skills/naist-deadline/scripts/register.js "<課題名>" "<締切日>"

# 例
node /Users/anicca/.openclaw/skills/naist-deadline/scripts/register.js "機械学習レポート" "2026-03-10"
node /Users/anicca/.openclaw/skills/naist-deadline/scripts/register.js "輪講スライド" "明日"
```

## 締切を完了にする

```bash
export PATH=/opt/homebrew/bin:$PATH
node /Users/anicca/.openclaw/skills/naist-deadline/scripts/complete.js "<課題名>"
```

## Slack出力フォーマット

### 一覧
```
📋 締切一覧（直近順）

🔴 今日  — 輪講スライド提出（2026/02/23）
🟡 明日  — プログラミング課題（2026/02/24）
🟢 あと15日  — 機械学習レポート（2026/03/10）
```

### 登録完了
```
✅ 登録しました

📌 機械学習レポート
🗓 2026/03/10
```

## データ保存場所

```
/Users/anicca/.openclaw/skills/naist-deadline/data/deadlines.json
```

## 状態ファイル（cron `naist-deadline-reminder` 用）

cron 実行時は以下の状態を読む（無ければ `#metrics` に "naist not yet onboarded" を投稿して終了）:

- 投稿先 Slack channel ID: `~/.openclaw/state/naist/<slug>/slack_channel.txt`
- `<slug>` は `~/.openclaw/state/naist/` 直下のディレクトリを列挙して全ユーザー分実行

毎日 18:00 JST に、明日 (`tomorrow`) と今日 (`today`) 締切の課題を `~/.openclaw/skills/naist-deadline/data/deadlines.json` から抽出して投稿する。
