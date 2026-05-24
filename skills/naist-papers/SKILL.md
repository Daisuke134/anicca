---
name: naist-papers
description: [DEPRECATED v1 — replaced by ~/.openclaw/skills/naist/ unified v2; this stub is kept for ledger continuity] arXivから論文を検索・要約する。Use when user says 「論文調べて」「arXivで検索して」「最新の論文は？」「研究教えて」「この論文まとめて」or similar paper search/summary requests in #ai-<name> channels. Also handles arxiv URLs pasted by user.
---

# naist-papers

arXivから論文を検索し、日本語で要約する。PDFダウンロード→テキスト抽出→詳細要約も可能。

## 状態ファイル（cron実行時）

cron `naist-papers-daily` から起動された場合、以下の状態を読む（存在しなければ #metrics に "naist not yet onboarded" を投稿して終了）:

- 検索キーワード: `~/.openclaw/state/naist/<slug>/research_topic.json` の `topic` と `categories`
- 投稿先 Slack channel ID: `~/.openclaw/state/naist/<slug>/slack_channel.txt`
- `<slug>` は `~/.openclaw/state/naist/` 直下に存在するディレクトリを列挙して全 user 分実行（複数ユーザー対応）

オンデマンドの場合（ユーザーが Slack でキーワードを指定）はそのキーワードを優先する。

## 1. 論文検索

ユーザーのメッセージからキーワードを抽出し、フレーズ検索する。

```bash
bash scripts/search_arxiv.sh "<phrase>" <count> <field>
# field: ti (title, default), abs (abstract), all (all fields)
# Example: bash scripts/search_arxiv.sh "mind wandering" 5 ti
```

- スペースを含むキーワードはフレーズ検索（自動で引用符付与）
- 結果が0件 → field を `all` に変更して再検索
- それでも0件 → キーワードを英語に変換して再検索

### 検索結果のSlack出力フォーマット

```
📄 arXiv検索: "{query}"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. *タイトル*
   著者名 et al. | 公開日
   https://arxiv.org/abs/XXXX.XXXXX

   要約: 3-4行で内容を日本語で説明

2. ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
計 N件ヒット（上位{count}件表示）
```

## 2. 論文詳細まとめ

ユーザーが特定の論文の詳細を求めた場合（番号指定、URL貼付、「まとめて」等）:

```bash
bash scripts/fetch_paper.sh <arxiv_id> /tmp
# → /tmp/<arxiv_id>.txt にテキスト抽出
```

抽出されたテキストを読み、以下のフォーマットで日本語要約:

```
📝 論文まとめ: *タイトル*
著者 | 公開日 | https://arxiv.org/abs/XXXX.XXXXX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 研究の目的
（2-3行）

📊 手法
（3-5行、具体的に）

💡 主な結果
（3-5行、数値があれば含める）

🔍 限界・今後の課題
（1-2行）

⚡ 一言で
（1行で核心をまとめる）
```

## 3. 依存

- `curl` — API呼び出し・PDF取得
- `pdftotext`（poppler）または `PyMuPDF` — PDF→テキスト変換
- インストール: `brew install poppler` or `pip3 install PyMuPDF`

## 注意

- abstractは日本語で要約する（原文が英語でも）
- arxiv IDは `XXXX.XXXXX` 形式（例: `2602.09904`）
- PDF抽出が失敗した場合はabstractのみで要約する
