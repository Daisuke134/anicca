# Research: naist-deadline

**Date**: 2026-02-23
**Branch**: `002-naist-deadline`

## Decision 1: ランタイム / 言語

| 項目 | 決定 |
|------|------|
| **Decision** | Node.js 18+ |
| **Rationale** | 既存のnaist-calendar・naist-papers・naist-onboardingが全てNode.js。`@slack/web-api`の利用実績あり。統一することで保守コスト最小化。 |
| **Alternatives considered** | Python（標準的だが既存スキルと乖離）、Bash（複雑なJSON操作に不向き） |

ソース: 既存スキル（naist-calendar/scripts/, naist-onboarding/scripts/）

---

## Decision 2: データストレージ

| 項目 | 決定 |
|------|------|
| **Decision** | JSONファイル（`/Users/anicca/.openclaw/skills/naist-deadline/data/deadlines.json`） |
| **Rationale** | 単一エージェント実行環境（Mac Mini）のため、DBやロック機構は不要。Node.js native JSON操作で完結。原子性は「一時ファイル + `fs.renameSync()`」で確保。 |
| **Alternatives considered** | SQLite（ファイルDBだが依存追加が不要な分JSONで十分）、PostgreSQL（Railway DBはあるがオーバーエンジニアリング） |

ソース: [nodebestpractices - file operations](https://github.com/goldbergyoni/nodebestpractices)

---

## Decision 3: Cron スケジュール

| 項目 | 決定 |
|------|------|
| **Decision** | `0 * * * *`（毎時0分）+ `0 8 * * *`（毎朝8時ダイジェスト） |
| **Rationale** | 毎時スキャンで「1時間前」「前日」のリマインドを確実に検出。毎朝8時ダイジェストで当日締切の全件を通知。最大59分の遅延許容。 |
| **Alternatives considered** | `*/15 * * * *`（15分毎は過剰）、1日1回（粒度が低すぎ） |

ソース: [OpenClaw Cron Jobs ドキュメント](https://docs.openclaw.ai/automation/cron-jobs)

---

## Decision 4: リマインドタイミング

| 項目 | 決定 |
|------|------|
| **Decision** | 前日18:00（1日前）/ 当日8:00（当日朝）/ 1時間前 |
| **Rationale** | spec.md のAssumptionsに記載されたデフォルト値（前日18:00・当日8:00）に加え、1時間前のアラートを追加。学術締切は深夜23:59が多いため1時間前通知が有効。 |
| **Alternatives considered** | 15分前のみ（見落としリスク高）、カスタム設定（初期実装ではスコープ外） |

---

## Decision 5: テストフレームワーク

| 項目 | 決定 |
|------|------|
| **Decision** | Jest |
| **Rationale** | Node.js 標準的なテストフレームワーク。モック・タイマー操作（`jest.useFakeTimers()`）が充実しており、締切日時のテストに最適。 |
| **Alternatives considered** | Mocha（設定が多い）、Vitest（新しいが実績が少ない） |

---

## Decision 6: スキル構造

既存naistスキルのパターンを踏襲:

| ファイル | 役割 |
|---------|------|
| `SKILL.md` | OpenClaw スキル定義（YAML frontmatter + 実行手順） |
| `scripts/register.js` | 締切を追加する |
| `scripts/list.js` | 締切一覧を表示する |
| `scripts/complete.js` | 締切を完了にする |
| `scripts/scan.js` | cronから呼ばれる。期限チェック→Slack通知 |
| `scripts/utils/storage.js` | JSON読み書き（原子的書き込み） |
| `scripts/utils/date.js` | 自然言語日付パース |
| `data/deadlines.json` | 永続ストレージ |
| `tests/` | Jest テスト |
