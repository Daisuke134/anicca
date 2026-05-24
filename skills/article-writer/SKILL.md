---
name: article-writer
description: Writes and publishes daily tech articles to Zenn (Japanese) and dev.to (English) based on today's diary. Use when article-writer cron fires or user asks to write and publish articles.
---

# article-writer SKILL

## 概要

毎日のAnicca開発活動を技術記事にして、Zenn（日本語）とdev.to（英語）に自動投稿する。

**Sources:**
- [Copyblogger: 22 Best Headline Formulas](https://copyblogger.com/10-sure-fire-headline-formulas-that-work/) — "8 out of 10 people will read the headline"
- [daily.dev: How to write viral stories for developers](https://daily.dev/blog/how-to-write-viral-stories-for-developers) — "Write from expertise. Developers hate clickbait."

---

## 実行手順

### Step 1: 環境設定

```bash
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
source /Users/anicca/.openclaw/.env
TODAY=$(TZ=Asia/Tokyo date +%Y-%m-%d)
WORKSPACE="/Users/anicca/.openclaw/workspace/article-writer/${TODAY}"
mkdir -p "$WORKSPACE"
```

### Step 2: diaryを読む

```bash
DIARY_PATH="/Users/anicca/.openclaw/workspace/daily-memory/diary-${TODAY}.md"
# diaryがない場合は昨日のものをフォールバック
if [ ! -f "$DIARY_PATH" ]; then
  YESTERDAY=$(TZ=Asia/Tokyo date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
  DIARY_PATH="/Users/anicca/.openclaw/workspace/daily-memory/diary-${YESTERDAY}.md"
fi
```

### Step 3: テーマ選定（優先順）

Source: [daily.dev: Write about your expertise](https://daily.dev/blog/how-to-write-viral-stories-for-developers)

| 優先 | 基準 | 例 |
|------|------|-----|
| 1位 | 他のエンジニアが同じ問題で詰まりそうなこと | cronジョブがサイレント失敗する原因 |
| 2位 | 「こうすればよかった」という失敗からの学び | API エンドポイントが変わっていた |
| 3位 | 初めて使ったツール・パターンの使い方 | dev.to APIへのPythonでの投稿方法 |
| 4位 | 設計判断とトレードオフ | VPS vs Mac Miniのどちらを使うべきか |

### Step 4: タイトル決定（Copyblogger公式 — 必須）

Source: [Copyblogger headline formula](https://copyblogger.com/10-sure-fire-headline-formulas-that-work/)

| 公式 | 例 | いつ |
|------|-----|------|
| `How to [動詞] [具体的対象]` | "How to Migrate OpenClaw from VPS to Mac Mini" | 手順・移行・設定系（最優先） |
| `How to [動詞] [対象] Without [デメリット]` | "How to Migrate Your AI Agent Without Breaking 43 Cron Jobs" | バグ回避系 |
| `How I [具体的成果] in [条件]` | "How I Fixed All 43 Broken Cron Jobs in 30 Minutes" | 自分の体験談系 |
| `[数字] [対象] That [結果]` | "5 OpenClaw Settings That Break All Your Cron Jobs" | リスト系 |

**NG タイトル:**

| NG | 理由 |
|----|------|
| "I Migrated My AI Agent..." | 発見の描写で終わり。読者に「で？」と思わせる |
| "Mac Mini移行してみた" | 何が得られるか不明 |
| "In today's fast-paced world..." | フィラー。即削除 |

### Step 5: JP記事を書く（Zenn向け）

**記事タイプを選ぶ:**

| タイプ | 構成 | いつ |
|--------|------|------|
| Tutorial / How-To | TL;DR → 前提条件 → Step 1〜N（コード込み）→ まとめ | **最優先。手順があれば必ずこれ** |
| Postmortem | TL;DR → 症状 → 根本原因 → Fix → 教訓 | バグ修正・失敗した日 |
| Architecture | TL;DR → 問題 → 制約 → 検討 → 採用 → トレードオフ | 設計判断した日 |

**JP記事フォーマット（Zenn frontmatter必須）:**

```markdown
---
title: "How to OpenClawをVPS→Mac Miniに移行する（cronジョブを壊さずに）"
emoji: "💻"
type: "tech"
topics: ["openclaw", "macos", "devops"]
published: true
---

## TL;DR
（2〜3行で結論。何を学べるか・何が解決するかを先に言い切る）

## 前提条件
（環境・バージョン・必要なもの）

## Step 1: ...
（コマンドは全部コピペで動く状態で書く）

## まとめ
| 教訓 | 詳細 |
|------|------|
| ... | ... |
```

**文字数:** 1200〜1800字

### Step 6: EN記事を書く（dev.to向け）

```markdown
---
title: "How to Migrate OpenClaw from VPS to Mac Mini"
published: true
tags: devops, macos, openclaw, migration
---

## TL;DR
（2〜3 sentences. Conclusion first.）

## Prerequisites

## Step 1: ...

## Key Takeaways
| Lesson | Detail |
|--------|--------|
| ... | ... |
```

**文字数:** 800〜1200 words

**禁止フレーズ:**
- "In today's fast-paced world..."
- "Simply do X" / "It's easy to..."
- 「大幅に改善」（数値で書く: 800ms → 90msに削減）

### Step 7: 記事ファイルを保存

```bash
# JP記事
cat > "${WORKSPACE}/jp.md" << 'ARTICLE'
（Step 5の記事内容）
ARTICLE

# EN記事
cat > "${WORKSPACE}/en.md" << 'ARTICLE'
（Step 6の記事内容）
ARTICLE
```

### Step 7.5: textlint校正（MANDATORY — 投稿前に必ず実行）

Source: [textlint: Integrations](https://textlint.org/docs/integrations/) — "Automated linting can complement human proofreading by detecting issues that can be easily missed"
Source: [Zenn記事 dev-github-vscode](https://zenn.dev/yuta28/articles/dev-github-vscode) — textlint + reviewdog で文書校正を自動化

```bash
ARTICLE_DIR="/Users/anicca/.openclaw/workspace/article-writer"

# EN記事の校正
npx --prefix "$ARTICLE_DIR" textlint --config "$ARTICLE_DIR/.textlintrc.json" "${WORKSPACE}/en.md" 2>&1 || true

# JP記事の校正
npx --prefix "$ARTICLE_DIR" textlint --config "$ARTICLE_DIR/.textlintrc.json" "${WORKSPACE}/jp.md" 2>&1 || true
```

**textlintが指摘した問題は全て修正してからStep 8に進む。**

| ルール | 対象 | 内容 |
|--------|------|------|
| `common-misspellings` | EN | スペルミス検出 |
| `write-good` | EN | 冗長表現・曖昧語の検出 |
| `preset-japanese` | JP | 日本語の一般的な文法ミス |
| `preset-jtf-style` | JP | JTF日本語標準スタイルガイド準拠 |

### Step 8: Zennに投稿

```bash
TOPIC_KEYWORD="<記事の1〜2語キーワード>"  # 例: openclaw-mac-mini
SLUG="${TODAY}-${TOPIC_KEYWORD}"
ZENN_DIR="/Users/anicca/.openclaw/workspace/zenn-articles"

cd "$ZENN_DIR"
npx zenn-cli new:article --slug "$SLUG" --type tech 2>/dev/null || true
cp "${WORKSPACE}/jp.md" "articles/${SLUG}.md"

# GITHUB_TOKENをgit remote URLに埋め込んでpush
git remote set-url origin "https://Daisuke134:${GITHUB_TOKEN}@github.com/Daisuke134/zenn-articles.git"
git add "articles/${SLUG}.md"
git commit -m "article: ${SLUG}"
for attempt in 1 2 3; do
  git pull --rebase origin main && git push origin main && break
  sleep 15
  if [ "$attempt" -eq 3 ]; then
    exit 1
  fi
done

ZENN_URL="https://zenn.dev/anicca/articles/${SLUG}"
echo "Zenn published: $ZENN_URL"
```

### Step 8.5: Zenn反映確認（MANDATORY）

```bash
for attempt in 1 2 3; do
  sleep 60
  HTTP_CODE=$(curl -sS --retry 3 --retry-delay 5 -o /dev/null -w "%{http_code}" "$ZENN_URL" || echo "000")
  if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Zenn記事が公開されている (HTTP $HTTP_CODE)"
    break
  fi
  echo "⚠️ Zenn反映待ち (HTTP $HTTP_CODE), retry ${attempt}/3"
  if [ "$attempt" -eq 3 ]; then
    echo "❌ Zenn記事がまだ公開されていない"
    echo "URL: $ZENN_URL"
    echo "対処: https://github.com/settings/installations でZenn Connect権限を確認"
    exit 1
  fi
done
```

### Step 9: dev.toに投稿（GitHub管理）

Source: [Zenn yuta28: dev.toの記事もGitHubで管理してみた](https://zenn.dev/yuta28/articles/dev-github-vscode) — "GitHub Actionsで自動投稿できる"

**フロー: MDファイル作成 → git push → GitHub Actions が自動で dev.to に投稿**

```bash
DEVTO_DIR="/Users/anicca/.openclaw/workspace/dev-to-articles"
TOPIC_KEYWORD="<記事の1〜2語キーワード>"
POST_DIR="${DEVTO_DIR}/blog-posts/${TODAY}-${TOPIC_KEYWORD}"
mkdir -p "${POST_DIR}/assets"

# 記事をコピー
cp "${WORKSPACE}/en.md" "${POST_DIR}/${TODAY}-${TOPIC_KEYWORD}.md"

# dev-to-git.json に記事を登録（dev-to-git が使う）
cd "$DEVTO_DIR"
python3 -c "
import json
with open('dev-to-git.json') as f: data = json.load(f)
entry = {'id': 0, 'relativePathToArticle': 'blog-posts/${TODAY}-${TOPIC_KEYWORD}/${TODAY}-${TOPIC_KEYWORD}.md'}
# id=0 means new article (dev-to-git will create it)
data.append(entry)
with open('dev-to-git.json', 'w') as f: json.dump(data, f, indent=2)
"

# git push → GitHub Actions が自動で dev.to に投稿
git add -A
git commit -m "article: ${TODAY}-${TOPIC_KEYWORD}"
git pull --rebase origin main
git push origin main

DEVTO_URL="https://dev.to/anicca_301094325e/${TODAY}-${TOPIC_KEYWORD}"
echo "dev.to published (via GitHub Actions): $DEVTO_URL"
```

### Step 10: Slack #metrics に報告（MANDATORY・絶対スキップ禁止）

<!-- FIX by skill-fixer 2026-04-02:
  原因: openclaw message send CLI は isolated session で失敗 → "Message failed" エラー
  修正: message ツールを直接使う（shell CLIではない）
-->

`message` ツール（ビルトイン）を使って報告する。shell の `openclaw message send` コマンドは **絶対に使わない**。

```
message tool:
  action: send
  channel: slack
  target: {{profile.channels.reportChannel}}
  message: |
    📝 article-writer 実行完了
    🇯🇵 Zenn: {ZENN_URL}
    🇺🇸 dev.to: {DEVTO_URL}
    テーマ: {TOPIC_KEYWORD}
```

---

## よくある失敗と対処（手動テストで確認済み）

| 失敗 | 原因 | 対処 |
|------|------|------|
| `npx zenn` が失敗 | package name は `zenn-cli` | `npx zenn-cli` を使う |
| git push 認証エラー | GITHUB_TOKEN未設定 or remote URLにtoken未埋め込み | `git remote set-url origin "https://Daisuke134:${GITHUB_TOKEN}@..."` |
| dev.to 403 Forbidden | User-Agentヘッダーなし | `post_devto.py` を使えば自動付与 |
| dev.to 422 "Title has already been used" | 同じタイトルが既に存在 | タイトルを変えて再実行 |
| delivery.mode "silent" | 無効な値 | `"none"` を使う（"announce"か"none"のみ有効） |

---

## ファイルパス

| 項目 | パス |
|------|------|
| diary（入力） | `/Users/anicca/.openclaw/workspace/daily-memory/diary-YYYY-MM-DD.md` |
| JP記事 | `/Users/anicca/.openclaw/workspace/article-writer/YYYY-MM-DD/jp.md` |
| EN記事 | `/Users/anicca/.openclaw/workspace/article-writer/YYYY-MM-DD/en.md` |
| dev.to投稿スクリプト | `/Users/anicca/.openclaw/workspace/article-writer/post_devto.py`（レガシー、GitHub Actions移行済み） |
| dev.toリポジトリ | `/Users/anicca/.openclaw/workspace/dev-to-articles/` → [GitHub](https://github.com/Daisuke134/dev-to-articles) |
| Zennリポジトリ | `/Users/anicca/.openclaw/workspace/zenn-articles/` → [GitHub](https://github.com/Daisuke134/zenn-articles) |

---

## 絶対禁止

| 禁止 | 理由 |
|------|------|
| Shell inline JSONでdev.to投稿 | 改行・特殊文字で壊れる（手動テスト確認済み） |
| `I Migrated...` 形式のタイトル | Copyblogger "How to" formula に反する |
| Slack報告をスキップ | MANDATORY |
| exec claude を使う | Aniccaが自分でやる |

---

## v0.2.0 追加（2026-05-07）— scripts/ + cross-link + 週末ローテ

### ウィザード（初回起動時）

| フィールド | デフォルト | 説明 |
|-----------|-----------|------|
| `DEVTO_API_KEY` | (.env) | dev.to API key |
| `article.zenn_repo` | `~/.openclaw/workspace/zenn-articles` | Zenn fork のローカルパス |
| `article.zenn_ssh_key` | `~/.ssh/id_ed25519` | git push 用 deploy key |
| `article.devto_tags` | `["agi","opensource","ai","automation"]` | dev.to タグ |
| `article.word_target` | `1500` | EN 記事の目標 word count |
| `article.tweet_account_en` | `cmm6d7m5703rwpr0yr5vtme3w` (@aniccaxxx) | cross-link 用 X integration |

### スクリプト

| スクリプト | 役割 | cron |
|-----------|------|------|
| `scripts/draft.py` | 40% diary / 30% codebase / 30% backlog から題材選び、EN+JA skeleton 生成 | `article-writer-draft` 06:00 JST |
| `scripts/post-devto.py` | EN を `https://dev.to/api/articles` に POST（header: `api-key`） | `article-writer-publish` 08:30 JST |
| `scripts/post-zenn.py` | JA を `Daisuke134/zenn-content` fork に commit + push（SSH deploy key） | `article-writer-publish` 08:30 JST |
| `scripts/cross-link.py` | "Just published <url>" を Postiz 経由でツイート | `article-writer-tweet` 12:00 JST |

### 週末ローテ（dev.to anti-spam 回避）

| 曜日 | cadence | word target |
|------|---------|------------|
| 月-金 | daily-deep-dive | 1500 |
| 土・日 | weekly-summary | 1200（軽め、過去5日のまとめ） |

`draft.py` が `datetime.weekday() >= 5` を判定して frontmatter コメントに `cadence: weekly-summary` を埋める。

### 出力

| 項目 | パス |
|------|------|
| Draft (EN) | `~/.openclaw/workspace/article-writer/drafts/YYYY-MM-DD/en.md` |
| Draft (JA) | `~/.openclaw/workspace/article-writer/drafts/YYYY-MM-DD/ja.md` |
| 公開履歴 | `~/.openclaw/workspace/article-writer/published.json` |
| backlog | `~/.openclaw/workspace/article-writer/backlog.md`（手動 / 別 cron で投入） |
| RSS | `~/.openclaw/workspace/article-writer/rss.xml`（後段で生成） |
| ログ | `~/.openclaw/logs/article-writer/` |
