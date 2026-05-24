---
name: grok-x-research
description: "xAI/Grok経由でXを検索し、3テーマのトレンドレポートを生成してX投稿する"
---

# grok-x-research

## 目的

x_search（OpenClawビルトインツール、xAI/Grok経由）でXを検索し、
3テーマのトレンドレポートを生成。最もエンゲージメントが高いものを1ツイート投稿する。

## 実行手順

### Step 1: x_searchで3テーマ検索

x_search（OpenClawビルトインツール）を使う。bun run x-search.tsではない。

```
x_search query="AI agent autonomous tool 2026" from_date="3日前"
x_search query="mental health anxiety healing app" from_date="3日前"
x_search query="suffering mindfulness meditation" from_date="3日前"
```

各結果: Grokが引用URL付きの詳細レポートを返す。

### Step 2: トレンドレポート生成

3テーマの結果を統合:
- 各テーマTOP3投稿（URL + 要約 + エンゲージメント数）

保存先: `~/.openclaw/workspace/grok-x-research/report-YYYY-MM-DD.json`

### Step 3: X投稿1つ（Postiz → @aniccaxxx）

最もエンゲージメントが高いトレンドを1ツイートにまとめる。
- 元ツイートURL引用 + ハッシュタグ
- Postiz API: integration cmm6d7m5703rwpr0yr5vtme3w
- **1投稿のみ。複数投稿禁止。**

### Step 4: Slack報告（100文字以内）

"🔬 grok-x-research | 3テーマ | TOP:9 | X投稿:1"
