# Research: naist-funds

**Date**: 2026-02-24
**Branch**: `003-naist-funds`

## Decision 1: ランタイム / 言語

| 項目 | 決定 |
|------|------|
| **Decision** | Node.js 18+ |
| **Rationale** | 既存のnaist-deadline・naist-calendar・naist-papers・naist-onboardingが全てNode.js。統一で保守コスト最小化。`@slack/web-api`利用実績あり。 |
| **Alternatives considered** | Python（既存スキルと乖離）、Bash（JSON操作・HTTP取得に不向き） |

ソース: 既存スキル（naist-deadline, naist-calendar, naist-papers）

---

## Decision 2: スクレイピング手段

| 項目 | 決定 |
|------|------|
| **Decision** | Firecrawl CLI（`/opt/homebrew/bin/firecrawl scrape <url> markdown`） |
| **Rationale** | CLAUDE.md・tool-usage.mdに「WebFetch禁止、Firecrawl CLIを使う」と明記。Mac Miniにインストール済み。JavaScriptレンダリング対応。フルMarkdown返却で構造化しやすい。 |
| **Alternatives considered** | Puppeteer（重い）、Playwright（テスト向き）、axios+cheerio（JSレンダリング不可） |

ソース: `.claude/rules/tool-usage.md` / 「WebFetchは内容が不完全・要約される。Firecrawlはフルマークダウンで返す」

---

## Decision 3: 対象ソース

| ソース | URL | 情報カテゴリ |
|--------|-----|------------|
| JSPS（日本学術振興会） | https://www.jsps.go.jp/j-grantsinaid/ | 科研費 |
| JST（科学技術振興機構） | https://www.jst.go.jp/boshu.html | 研究助成・公募情報 |
| 日本財団助成金 | https://www.jfund.or.jp/ | 研究助成金 |

**Rationale**: spec.md FR-002に明記。NAIST学生が実際に申請する主要3ソース。

---

## Decision 4: データストレージ

| 項目 | 決定 |
|------|------|
| **Decision** | JSONファイル（2ファイル: `cache.json` + `guides.json`） |
| **Rationale** | 単一エージェント実行環境（Mac Mini）のため、DBは不要。naist-deadlineと同じパターンを踏襲。原子性は `tmp + renameSync()` で確保。 |
| **Alternatives considered** | SQLite（オーバーエンジニアリング）、PostgreSQL（さらに過剰） |

| ファイル | 内容 |
|---------|------|
| `data/cache.json` | 通知済みGrantのIDキャッシュ（重複防止） |
| `data/guides.json` | 申請手順ナレッジ（keyword + steps + officialUrl） |

---

## Decision 5: Cron スケジュール

| 項目 | 決定 |
|------|------|
| **Decision** | `15 9 * * 1,4`（月曜・木曜09:15 JST） |
| **Rationale** | spec.md FR-001に明記。NAIST学生が午前中に確認する習慣に合わせた。週2回で情報鮮度を保つ。 |
| **Alternatives considered** | 週1回（情報更新が遅すぎ）、毎日（過剰） |

ソース: naist-agent-spec.mdの設計方針

---

## Decision 6: Slack 投稿方法

| 項目 | 決定 |
|------|------|
| **Decision** | `exec` ツール + `openclaw message send --channel slack --target <CHANNEL_ID> --message "..."` |
| **Rationale** | naist-deadline・naist-calendar等の既存スキルが全て同じパターンを使用。CLAUDE.mdに「OpenClawはexec + CLIで投稿」と明記。 |
| **Alternatives considered** | @slack/web-api直接呼び出し（SLACK_BOT_TOKENの環境変数参照が必要で既存パターンと異なる） |

---

## Decision 7: テストフレームワーク

| 項目 | 決定 |
|------|------|
| **Decision** | Jest |
| **Rationale** | naist-deadlineと同じ。モック（`jest.fn()`）でFirecrawl CLI呼び出しとSlack送信をモック化。 |
| **Alternatives considered** | Mocha（設定が多い）、Vitest（新しいが実績少） |

---

## Decision 8: スキル構造

naist-deadlineのパターンを踏襲:

| ファイル | 役割 |
|---------|------|
| `SKILL.md` | OpenClaw スキル定義（YAML frontmatter + 実行手順） |
| `scripts/fetch.js` | Firecrawlで3ソースからGrant情報を取得 |
| `scripts/notify.js` | 取得したGrantをSlackに投稿（重複フィルタ込み） |
| `scripts/guide.js` | 申請手順を検索・回答する |
| `scripts/scan.js` | cronエントリポイント。fetch → notify を実行 |
| `scripts/utils/storage.js` | JSON読み書き（原子的書き込み） |
| `scripts/utils/slack.js` | openclaw message send ラッパー |
| `data/cache.json` | 通知済みGrantキャッシュ |
| `data/guides.json` | 申請手順ナレッジ |
| `tests/` | Jestテスト |
