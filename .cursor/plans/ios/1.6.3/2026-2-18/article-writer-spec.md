# article-writer + build-in-public — 仕様書

**作成日:** 2026-02-21
**更新日:** 2026-02-22（ツイートフォーマット確定・RevenueCat API詳細追加・Day N計算明確化）
**ステータス:** 実装中
**目的:** 毎日23:00以降にAniccaが今日のdiary（daily-memoryスキル出力）を読み、X（Build in Public、日本語）+ Zenn（JP記事）+ dev.to（EN記事）に自動投稿する。

---

## 概要（What & Why）

| 項目 | 内容 |
|------|------|
| What | 毎日の開発活動を → X（Build in Public） + 技術記事（Zenn JP / dev.to EN）に自動投稿 |
| Why | 1k MRRへの道のりを日々発信し続けることでコミュニティと信頼が積み上がる。Aniccaのdharma |
| 担当 | **Anicca（Mac Mini）が全部やる。** exec claude は使わない |
| モデル | Claude Sonnet 4（anthropic/claude-sonnet-4-20250514） |
| ソース（writing BP） | [Copyblogger: 22 Best Headline Formulas](https://copyblogger.com/10-sure-fire-headline-formulas-that-work/) / [daily.dev: How to write viral stories for developers](https://daily.dev/blog/how-to-write-viral-stories-for-developers) / [ClawHub twitter skill](https://clawhub.ai/blueberrywoodsym/twitter) |

---

## セットアップ完了状態（2026-02-22）

| # | 項目 | 状態 |
|---|------|------|
| 1 | `Daisuke134/zenn-articles` リポジトリ作成 | ✅ 完了 |
| 2 | zenn-cli 初期化 + push | ✅ 完了 |
| 3 | Zenn × GitHub連携（dashboard/deploys） | ✅ 完了 |
| 4 | `DEVTO_API_KEY` を Mac Mini `.env` に保存 | ✅ 完了 |
| 5 | zenn-articles を Mac Mini にclone | ✅ 完了（`/Users/anicca/.openclaw/workspace/zenn-articles`） |
| 6 | `zenn-cli` npm install 完了（package.json + node_modules） | ✅ 完了 |
| 7 | `article-writer` SKILL.md 作成（v1） | ✅ 完了 |
| 8 | **GITHUB_TOKEN を `.env` に追加** | ⏳ 未完了 |
| 9 | **article-writer SKILL.md を正しい設計に書き直す（本仕様に従って）** | ⏳ 未完了 |
| 10 | **build-in-public SKILL.md 作成（ClawHubコピー + Blotato）** | ⏳ 未完了 |
| 11 | **cron時刻修正（article-writer: 22:00→23:30、build-in-public: 23:10新規）** | ⏳ 未完了 |
| 12 | **dev.to投稿用Pythonスクリプト設置** | ⏳ 未完了 |
| 13 | テスト cron 3本（17:10/17:15/17:20 JST 今日のみ）を追加 | ⏳ 未完了 |
| 14 | テスト発火・Slack URL確認（ダイスが確認） | ⏳ 未完了 |

---

## アーキテクチャ（3スキル独立構成）

```
23:00 JST  daily-memory（既存）
               ↓ diary-YYYY-MM-DD.md を書く
               ↓
23:10 JST  build-in-public（新規）
               ↓ diary を読む → MRR/Trial を RevenueCat API で取得
               ↓ ClawHub twitter skill の Phase1（niche研究）→ Phase2（執筆）
               ↓ 日本語ツイートを Blotato API で X に投稿
               ↓ Slack #metrics に報告（MANDATORY）
               ↓
23:30 JST  article-writer（時刻変更）
               ↓ diary を読む → テーマ選定
               ↓ Copyblogger "How to" 公式でタイトル決定
               ↓ JP記事 → workspace/jp.md → Zenn git push
               ↓ EN記事 → workspace/en.md → dev.to API
               ↓ Slack #metrics に報告（MANDATORY）
```

**なぜ3つ独立させるか:**
- daily-memoryが壊れてもarticle-writerに影響しない（独立障害）
- どのスキルで失敗したか即特定できる
- 個別に再実行できる

---

## cron message テンプレート（全スキル共通パターン）

```
Execute [skill-name] skill. Read ~/.openclaw/skills/[skill-name]/SKILL.md and perform the steps yourself. Use today's date (Asia/Tokyo). Read today's diary from ~/.openclaw/workspace/daily-memory/. CRITICAL: After you finish, you MUST post a summary of your execution results (success or failure, what you did, any errors) to Slack #metrics channel (channel ID: C091G3PKHL2). This Slack report is MANDATORY and non-negotiable. Do not skip it under any circumstances.
```

---

## スキル1: build-in-public

### 概要

| 項目 | 内容 |
|------|------|
| cron | **23:10 JST**（毎日） |
| 投稿先 | X（Twitter） |
| 言語 | **日本語**（ACCOUNT_ID_JA = 29172） |
| 投稿方法 | Blotato API（`POST https://backend.blotato.com/v2/posts`、既存x-posterと同じ） |
| データソース | diary + RevenueCat API（MRR・Trial数） |
| ライティング BP | [ClawHub twitter skill](https://clawhub.ai/blueberrywoodsym/twitter): Phase1 Niche Research → Phase2 Framework Writing |

### ツイートフォーマット（固定）

Source: ClawHub twitter skill "Build in Public" framework

```
M/DD. Anicca 1k MRRへ Day N目。

$XX MRR. X trial。

xxx
xxx
xxx

（進捗への1行コメント）
```

**フィールド説明:**

| フィールド | 取得方法 | 例 |
|-----------|---------|-----|
| `M/DD` | 今日の日付（Asia/Tokyo） | `2/22` |
| `Day N目` | 2025-12-31を Day 1 として計算 | `Day 53目` |
| `$XX MRR` | RevenueCat API `/v1/projects/projbb7b9d1b/metrics/overview` から `mrr` フィールド | `$17 MRR` |
| `X trial` | RevenueCat API から `active_trials` | `1 trial` |
| xxx（3行） | diaryから今日やったこと。**「started / built / shipped / published / fixed / tested」で始める** | `started X paywall A/B test` |
| 1行コメント | 今日の進捗への正直な一言（英語でも日本語でも可） | `少しずつ前に進んでる。` |

**具体例:**

```
2/22. Anicca 1k MRRへ Day 53目。

$17 MRR. 1 trial。

started paywall A/B test for better trial CVR
shipped daily article auto-post to Zenn + dev.to
fixed openclaw cron delivery.mode bug on Mac Mini

毎日の積み上げが唯一の答え。
```

### ライティングプロセス（ClawHub twitter skillコピー）

**Phase 1: Research（必須、スキップ禁止）**

Source: [ClawHub twitter skill](https://clawhub.ai/blueberrywoodsym/twitter) Phase 1 framework

1. diaryから今日やったことの中で「最も他人が興味を持ちそうなこと」を1つ選ぶ
2. そのトピックで過去のバズツイートをWebSearchで検索: `"indie hacker" "build in public" "[topic]" twitter viral`
3. バズったツイートのパターン（数字の使い方・行間・言葉選び）を参考にする
4. 参考にしたパターンでフォーマットに合わせて書く

**Phase 2: Writing ルール**

Source: [Copyblogger headline formula](https://copyblogger.com/10-sure-fire-headline-formulas-that-work/) + daily.dev "8 out of 10 readers read the headline"

| ルール | 詳細 |
|--------|------|
| 数字を使う | `$17 MRR` > `少しのMRR`。`53日目` > `数週間` |
| 動詞で始める | `started / built / shipped / fixed` > 名詞で始めない |
| 具体的にする | `started paywall A/B test` > `アプリ改善した` |
| 絵文字は使わない | Build in Public はシンプルが強い |

### Blotato投稿コマンド

```bash
export PATH=/opt/homebrew/bin:/usr/bin:/bin
source /Users/anicca/.openclaw/.env

# ACCOUNT_ID_JA = 29172（日本語アカウント）
curl -s -X POST https://backend.blotato.com/v2/posts \
  -H "blotato-api-key: $BLOTATO_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"${TWEET_TEXT}\", \"platforms\": [{\"platform\": \"twitter\", \"accountId\": 29172}]}"
```

---

## スキル2: article-writer

### 概要

| 項目 | 内容 |
|------|------|
| cron | **23:30 JST**（毎日、22:00から変更） |
| 投稿先 | Zenn（JP） + dev.to（EN） |
| タイトル公式 | Copyblogger "How to" formula（必須） |
| 言語 | JP: 日本語（1200〜1800字） / EN: English（800〜1200 words） |

### タイトル公式（Copyblogger確立済み — Bible扱い）

Source: [Copyblogger: 22 Best Headline Formulas](https://copyblogger.com/10-sure-fire-headline-formulas-that-work/)
核心の引用: "How to [benefit A] and [benefit B]" / "8 out of 10 people will read the headline, only 2 will read the rest"

| 公式 | 例 | いつ |
|------|-----|------|
| `How to [動詞] [具体的対象]` | "How to Migrate OpenClaw from VPS to Mac Mini" | 手順・移行・設定系 |
| `How to [動詞] [対象] Without [デメリット]` | "How to Migrate Your AI Agent Without Breaking 43 Cron Jobs" | バグ回避系 |
| `How I [具体的成果] in [条件]` | "How I Fixed All 43 Broken Cron Jobs in 30 Minutes" | 自分の体験談系 |
| `[数字] [対象] That [結果]` | "5 OpenClaw Settings That Break All Your Cron Jobs" | リスト系 |

**禁止タイトルパターン（NG）:**

| NG | 理由 |
|----|------|
| "I Migrated My AI Agent from VPS to Mac Mini — 43 Cron Jobs Broke" | 発見の描写で終わり。読者に「で？」と思わせる。自分ごとにならない |
| "MacMini移行してみた" | ぼんやりしすぎ。何が得られるか不明 |

### テーマ選定（優先順）

Source: [daily.dev: Write about your expertise](https://daily.dev/blog/how-to-write-viral-stories-for-developers)
核心の引用: "Developers appreciate hard-working people. The first place to look is your expertise."

| 優先 | 基準 | 例 |
|------|------|-----|
| 1位 | 他のエンジニアが同じ問題で詰まりそうなこと | cronジョブがサイレント失敗する原因 |
| 2位 | 「こうすればよかった」という失敗からの学び | Blotato APIエンドポイントが変わっていた |
| 3位 | 初めて使ったツール・パターンの使い方 | dev.to APIへのPythonでの投稿方法 |
| 4位 | 設計判断とトレードオフ | VPS vs Mac Miniのどちらを使うべきか |

### 記事構成（記事タイプで選ぶ）

| タイプ | 構成 | いつ使う |
|--------|------|---------|
| Tutorial / How-To | TL;DR → 前提条件 → Step 1〜N（コード込み）→ まとめ | **最優先。手順があれば必ずこれ** |
| Postmortem | TL;DR → 症状 → 根本原因 → Fix → 教訓 | バグ修正・失敗した日 |
| Architecture | TL;DR → 問題 → 制約 → 検討 → 採用 → トレードオフ | 設計判断をした日 |

**TL;DRは必須:** 2〜3行で結論を先に書く。読者の8割はTL;DRしか読まない（Copyblogger原則）

### 禁止フレーズ

| 禁止 | 理由 |
|------|------|
| "In today's fast-paced world..." | フィラー。即削除 |
| "Simply do X" / "It's easy to..." | 読者を馬鹿にする |
| 「大幅に改善」等の曖昧表現 | 数値で書く（例: 800ms → 90msに削減） |
| AI臭い文章 | humanizer（ClawHub）を通すこと |

### 記事フォーマット

**JP記事（Zenn）:**

```markdown
---
title: "How to OpenClawをVPS→Mac Miniに移行する（43個のcronジョブを壊さずに）"
emoji: "💻"
type: "tech"
topics: ["openclaw", "macos", "devops"]
published: true
---

# TL;DR
（2〜3行で結論。何を学べるか・何が解決するかを先に言い切る）

## 前提条件
（環境・バージョン・必要なもの）

## Step 1: ...
（コマンドは全部コピペで動く状態で書く）

## Step 2: ...
...

## まとめ
（教訓をテーブルで。1行1教訓）
```

**EN記事（dev.to）:**

```markdown
---
title: "How to Migrate OpenClaw from VPS to Mac Mini (Without Breaking 43 Cron Jobs)"
published: true
tags: devops, macos, openclaw, migration
---

# TL;DR
（2〜3 sentences. Conclusion first.）

## Prerequisites
...

## Step 1: ...
...

## Key Takeaways
| Lesson | Detail |
|--------|--------|
| ... | ... |
```

---

## 技術実装（手動テストで確認済みの正しいコマンド）

### Zenn投稿

```bash
export PATH=/opt/homebrew/bin:/usr/bin:/bin
TODAY=$(TZ=Asia/Tokyo date +%Y-%m-%d)
SLUG="${TODAY}-${TOPIC_KEYWORD}"   # 例: 2026-02-22-openclaw-mac-mini-cron
ZENN_DIR="/Users/anicca/.openclaw/workspace/zenn-articles"

cd "$ZENN_DIR"
# zenn-cliはpackage.jsonが既にある（npm install済み）
npx zenn-cli new:article --slug "$SLUG" --type tech

# ワークスペースのjp.mdをZennリポジトリにコピー（frontmatterごと上書き）
cp "/Users/anicca/.openclaw/workspace/article-writer/${TODAY}/jp.md" "articles/${SLUG}.md"

# GITHUB_TOKENをgit remote URLに埋め込んでpush
source /Users/anicca/.openclaw/.env
git remote set-url origin "https://Daisuke134:${GITHUB_TOKEN}@github.com/Daisuke134/zenn-articles.git"
git add "articles/${SLUG}.md"
git commit -m "article: ${SLUG}"
git push origin main

ZENN_URL="https://zenn.dev/daisuke134/articles/${SLUG}"
```

### dev.to投稿

**Pythonスクリプトを使う（Shell inline JSONは特殊文字で壊れる — 手動テスト確認済み）**

スクリプトパス: `/Users/anicca/.openclaw/workspace/article-writer/post_devto.py`

```python
# post_devto.py（設置済み）
import json, urllib.request, urllib.error, os

api_key = os.environ.get("DEVTO_API_KEY", "")
with open(f"/Users/anicca/.openclaw/workspace/article-writer/{TODAY}/en.md") as f:
    content = f.read()
# frontmatter除去してbody_markdownに → POST
# User-Agentヘッダー必須（ないと403 Forbidden）
```

```bash
source /Users/anicca/.openclaw/.env
TODAY=$(TZ=Asia/Tokyo date +%Y-%m-%d)
DEVTO_RESPONSE=$(python3 /Users/anicca/.openclaw/workspace/article-writer/post_devto.py 2>&1)
DEVTO_URL=$(echo "$DEVTO_RESPONSE" | grep "^url:" | awk '{print $2}')
```

### Slack報告

```bash
openclaw message send --channel slack --target 'C091G3PKHL2' \
  --message "📝 article-writer 実行完了
🇯🇵 Zenn: ${ZENN_URL}
🇺🇸 dev.to: ${DEVTO_URL}"
```

---

## ファイルパス一覧（全部フルパス）

| 項目 | パス |
|------|------|
| article-writer SKILL.md | `/Users/anicca/.openclaw/skills/article-writer/SKILL.md` |
| build-in-public SKILL.md | `/Users/anicca/.openclaw/skills/build-in-public/SKILL.md` |
| daily-memory diary（入力） | `/Users/anicca/.openclaw/workspace/daily-memory/diary-YYYY-MM-DD.md` |
| JP記事ワークスペース | `/Users/anicca/.openclaw/workspace/article-writer/YYYY-MM-DD/jp.md` |
| EN記事ワークスペース | `/Users/anicca/.openclaw/workspace/article-writer/YYYY-MM-DD/en.md` |
| dev.to投稿スクリプト | `/Users/anicca/.openclaw/workspace/article-writer/post_devto.py` |
| Zenn記事リポジトリ | `/Users/anicca/.openclaw/workspace/zenn-articles/articles/SLUG.md` |
| Zenn slug命名 | `YYYY-MM-DD-topic-keyword`（例: `2026-02-22-openclaw-mac-mini-cron`） |
| env（API keys） | `/Users/anicca/.openclaw/.env` |
| cron jobs.json | `/Users/anicca/.openclaw/cron/jobs.json` |

---

## cron 設定（本番 + テスト）

### 本番cron

| スキル | expr | tz | 備考 |
|--------|------|----|------|
| `daily-memory` | `0 23 * * *` | Asia/Tokyo | 変更なし |
| `build-in-public` | `10 23 * * *` | Asia/Tokyo | 新規追加 |
| `article-writer` | `30 23 * * *` | Asia/Tokyo | 22:00→23:30に変更 |

### テストcron（今日のみ）

| スキル | expr | tz | 備考 |
|--------|------|----|------|
| `daily-memory-test-today` | `10 17 22 2 *` | Asia/Tokyo | 17:10 JST |
| `build-in-public-test-today` | `15 17 22 2 *` | Asia/Tokyo | 17:15 JST |
| `article-writer-test-today` | `20 17 22 2 *` | Asia/Tokyo | 17:20 JST |

---

## ワークスペース構造

```
/Users/anicca/.openclaw/workspace/article-writer/
├── post_devto.py          ← dev.to投稿スクリプト（共通）
├── 2026-02-22/
│   ├── jp.md              ← Zennに投稿したJP記事の原稿
│   └── en.md              ← dev.toに投稿したEN記事の原稿
├── 2026-02-23/
│   ├── jp.md
│   └── en.md
...
```

---

## 境界（やらないこと）

| やらないこと | 理由 |
|------------|------|
| exec claude を使う | Aniccaが全部やる |
| note.com への投稿 | Zenn（JP）と重複するため除外 |
| LinkedIn への投稿 | スコープ外 |
| bird CLIで直接X投稿 | Blotato APIが既に設定済み。安定性優先 |
| 週次・月次まとめ記事 | まず毎日を軌道に乗せてから |
| 画像・OGP生成 | スコープ外 |
| diary以外のソース（raw JSONL等）を読む | daily-memoryが既にまとめてくれてる |
| diaryがない時のスキップ | 昨日のdiaryをフォールバックとして使う |

---

## 絶対禁止

| 禁止 | 代替 |
|------|------|
| `jobs.json` を全体置き換え | 差分のみ編集 |
| `skills/` 以下の既存ファイルを削除・上書き | `article-writer/` `build-in-public/` の中だけ編集 |
| `openclaw.json` を全体置き換え | 差分だけ編集 |
| Shell inline JSONでdev.toを投稿 | `post_devto.py` を使う（改行・特殊文字で壊れる） |

---

## 次のアクション（実装順）

| # | タスク | 状態 |
|---|--------|------|
| 1 | `GITHUB_TOKEN` を `.env` に追加 | ⏳ |
| 2 | `post_devto.py` を workspace に設置 | ⏳ |
| 3 | `build-in-public` SKILL.md を Mac Mini に作成 | ⏳ |
| 4 | `article-writer` SKILL.md を本仕様に沿って書き直し | ⏳ |
| 5 | `article-writer` cron を 23:30 に変更 | ⏳ |
| 6 | `build-in-public` cron を 23:10 で新規追加 | ⏳ |
| 7 | テストcron 3本追加（17:10/17:15/17:20 JST 今日のみ） | ⏳ |
| 8 | テスト発火 → Slack #metrics でURL確認（ダイスが確認） | ⏳ |
| 9 | Zenn・dev.to・X の記事/ツイートを確認（ダイスが確認） | ⏳ |
