# OpenClaw Workspace Files — 現状の逸脱と修正計画

全てドキュメント原典からの引用。推測ゼロ。

---

## 毎ターン注入されるファイル（Project Context）

Source: `/docs/concepts/system-prompt.md`
> "Bootstrap files are trimmed and appended under **Project Context** so the model sees identity and profile context without needing explicit reads"

| # | ファイル | ドキュメント定義 | Source |
|---|---|---|---|
| 1 | AGENTS.md | "Operating instructions for the agent and how it should use memory. Good place for rules, priorities, and 'how to behave' details." | `agent-workspace.md` |
| 2 | SOUL.md | "Persona, tone, and boundaries." | `agent-workspace.md` |
| 3 | TOOLS.md | "Notes about your local tools and conventions. Does not control tool availability; it is only guidance." | `agent-workspace.md` |
| 4 | IDENTITY.md | "The agent's name, vibe, and emoji. Created/updated during the bootstrap ritual." | `agent-workspace.md` |
| 5 | USER.md | "Who the user is and how to address them." | `agent-workspace.md` |
| 6 | HEARTBEAT.md | "Optional tiny checklist for heartbeat runs. Keep it short to avoid token burn." | `agent-workspace.md` |
| 7 | BOOTSTRAP.md | "One-time first-run ritual. Only created for a brand-new workspace. Delete it after the ritual is complete." | `agent-workspace.md` |
| 8 | MEMORY.md | "Curated long-term memory. Only load in the main, private session (not shared/group contexts)." | `agent-workspace.md` |

※ `bootstrapMaxChars` デフォルト20000で各ファイルを切り詰め（`system-prompt.md`）

---

## 各ファイルの役割と違い

### SOUL.md vs IDENTITY.md
- **IDENTITY.md** = 僕（エージェント）の名刺。Name, Creature, Vibe, Emoji, Avatar
  - テンプレート: "This isn't just metadata. It's the start of figuring out who you are."
- **SOUL.md** = 僕の魂。性格・倫理・境界線・行動原理
  - テンプレート: Core Truths, Boundaries, Vibe, Continuity
- **USER.md** = Dais（ユーザー）の情報。名前・呼び方・TZ・メモ

### AGENTS.md vs MEMORY.md
- **AGENTS.md** = 安定した運用ルール（あまり変わらない）
  - テンプレート内容: Session start手順, Memory管理, Safety, External vs Internal, Group Chat, Heartbeat
- **MEMORY.md** = 流動的な記憶（頻繁に更新）
  - "Decisions, preferences, and durable facts go to MEMORY.md" (Source: `concepts/memory.md`)

---

## 現状の逸脱（5つ）

### 1. ❌ BOOTSTRAP.md が残存している（深刻度: 高）

**ベストプラクティス:**
- `agent-workspace.md`: "One-time first-run ritual. **Delete it after the ritual is complete.**"
- `start/bootstrapping.md`: "Removes BOOTSTRAP.md when finished so it only runs once."

**現状:** 55行・1,470バイトが毎ターン無駄に注入されている。

**Mac Mini移行に必要？:** NO
- `install/migrating.md`: BOOTSTRAP.mdへの言及ゼロ。state dir + workspaceコピーで完結。

**修正:** 夜間に削除。

### 2. ⚠️ AGENTS.md が肥大化している（深刻度: 高）

**ベストプラクティス:**
- `agent-workspace.md`: "Operating instructions for the agent and how it should use memory. Good place for rules, priorities, and 'how to behave' details."
- テンプレート（180行）: Session start, Memory管理, Safety, External vs Internal, Group Chat, Heartbeat

**現状:** 230行・11,959バイト。iOS開発ガイド全体（API一覧、ディレクトリ構造、コンポーネント表、環境変数）が入っている。

**問題:** 技術詳細は「how to behave」ではない。毎ターン12KB注入は重い。

**修正:** 運用ルールに絞る。iOS技術詳細は別ファイル（`docs/ios-guide.md`等）に移動。memory_searchで必要な時だけ引ける。

### 3. ⚠️ SOUL.md に運用ルールが混在（深刻度: 中）

**ベストプラクティス:**
- SOUL.md = "Persona, tone, and boundaries"
- AGENTS.md = "Operating instructions"

**現状:** Daily Rhythm（運用ルール）、ファイル編集禁止事項がSOUL.mdに入っている。

**修正:** SOUL.md = 性格・倫理・無明の教え。デイリーリズム等の運用ルールはAGENTS.mdへ移動。

### 4. ⚠️ HEARTBEAT.md が未活用（深刻度: 中）

**ベストプラクティス:**
- `cron-vs-heartbeat.md`: "The most efficient setup uses both"
- `gateway/heartbeat.md`: "If HEARTBEAT.md exists but is effectively empty, OpenClaw skips the heartbeat run to save API calls."

**現状:** 空（コメントのみ）→ heartbeatスキップされている。

**修正:** 下記「Heartbeat設計」セクション参照。

### 5. ⚠️ MEMORY.md の整理が必要（深刻度: 低）

**ベストプラクティス:**
- テンプレートAGENTS.md: "Periodically review daily files and update MEMORY.md with distilled learnings. Remove outdated info that's no longer relevant."

**現状:** 134行・8,600バイト。増加中。

**修正:** 定期整理。Heartbeatのmemory maintenanceチェックで自動化。

---

## トークン消費の現状

```
AGENTS.md    11,959 bytes  ← 巨大（技術詳細を分離すべき）
MEMORY.md     8,600 bytes  ← 増加中（定期整理必要）
SOUL.md       3,664 bytes  ← 運用ルール分離で軽量化可能
TOOLS.md      2,693 bytes  ← OK
BOOTSTRAP.md  1,470 bytes  ← 削除すべき
USER.md       1,028 bytes  ← OK
IDENTITY.md     820 bytes  ← OK
HEARTBEAT.md    168 bytes  ← 空（OK）
─────────────────────────
合計          30,402 bytes → 毎ターン注入
```

---

## Heartbeat設計（ベストプラクティスからのコピー）

### チェック項目（全て外部ソースから）

| チェック | 頻度 | 時間帯 | 出典1 | 出典2 |
|---|---|---|---|---|
| Email | 30分 | 9AM-9PM | digitalknk runbook: "Email: every 30 min (9 AM - 9 PM only)" | 公式docs: "Check inbox every 30 min → Heartbeat" |
| Calendar | 2時間 | 8AM-10PM | digitalknk runbook: "Calendar: every 2 hours (8 AM - 10 PM only)" | 公式docs: "Monitor calendar for upcoming events → Heartbeat" |
| Tasks | 30分 | いつでも | digitalknk runbook: "Tasks: every 30 min (anytime)" | markaicode: "Check if any tasks in Todoist are overdue" |
| Git status | 24時間 | いつでも | digitalknk runbook: "Git: every 24 hours (anytime)" | "Check workspace for uncommitted changes" |
| System | 24時間 | 3AM | digitalknk runbook: "System: every 24 hours (3 AM only)" | "Check for failed cron jobs and error logs" |
| Memory maintenance | 数日ごと | いつでも | 公式テンプレートAGENTS.md: "Periodically use a heartbeat to review daily files and update MEMORY.md" |

### パターン: Rotating Heartbeat（digitalknk runbook ★408をコピー）

Source: `github.com/digitalknk/openclaw-runbook`

> "a rotating heartbeat pattern where a single heartbeat runs different checks based on cadence instead of firing everything at once"

1回のheartbeat = 最も遅れてる1つのチェックだけ実行
→ トークン節約 + 負荷分散

### コスト最適化（damogallagher dev.toをコピー）

Source: `dev.to/damogallagher`

> "do rule-based checks first, only call a model when there's actual signal"
> "Most heartbeat logic is not 'reasoning.' It's just checking state."

### Config設定

Source: `/docs/gateway/heartbeat.md`
digitalknk: "Use the cheapest model for heartbeat checks"

```json5
{
  agents: {
    defaults: {
      heartbeat: {
        every: "30m",
        model: "anthropic/claude-sonnet-4-20250514",  // 最安で十分
        target: "last",
        activeHours: {
          start: "23:00",  // 8 AM JST = 23:00 UTC前日
          end: "14:00"     // 11 PM JST = 14:00 UTC
        }
      }
    }
  }
}
```

### 既存Cronとの関係

Source: `/docs/automation/cron-vs-heartbeat.md`
> "Does the task need to run at an EXACT time? YES → Cron"

全既存Cron（gmail-digest, gcal-digest, slack-digest, app-metrics, trend-hunter, poster等）は正確な時間が必要 → **Cronのまま維持。正しい。**

Heartbeat = 「何か起きてないかずっと見張る」
Cron = 「定時に特定の仕事をやる」

---

## 修正実行計画（全て夜間に実施）

| 順序 | 修正 | 作業内容 |
|---|---|---|
| 1 | BOOTSTRAP.md削除 | `rm BOOTSTRAP.md` |
| 2 | AGENTS.md スリム化 | 運用ルールだけ残す。iOS技術詳細を `docs/ios-guide.md` に移動 |
| 3 | SOUL.md 整理 | デイリーリズム等の運用ルールをAGENTS.mdへ移動 |
| 4 | HEARTBEAT.md 設定 | 上記Rotating Heartbeatを書き込む |
| 5 | heartbeat-state.json 作成 | 初期state file |
| 6 | Config変更 | heartbeat設定をopenclaw.jsonに追加 |
| 7 | MEMORY.md 整理 | 古い情報削除、最新に整理 |

---

*作成: 2026-02-18 02:49 UTC*
*全てのベストプラクティスはOpenClaw公式ドキュメントおよび外部ソース（digitalknk, markaicode, damogallagher）から引用*
