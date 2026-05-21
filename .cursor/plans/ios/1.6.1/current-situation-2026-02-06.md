# Anicca 現状まとめ（2026-02-06）

**このファイルは「今どうなっているか」を記録する。忘れたらここを読め。**

---

## 1. OpenClaw の状態

### 今どこで動いている？

| 項目 | 状態 |
|------|------|
| **動いている場所** | ローカル Mac（あなたのパソコン） |
| **Hetzner VPS** | セットアップ済みだが、まだ接続されていない |
| **設定ファイル** | `~/.openclaw/openclaw.json` で `mode: "local"` になっている |

### VPS に移行するには？

1. `mode: "local"` → `mode: "remote"` に変更
2. VPS で OpenClaw Gateway を起動
3. ローカル Mac の LaunchAgent を停止

### 今動いている Cron ジョブ

| ジョブ | 時刻 | 状態 |
|--------|------|------|
| daily-metrics-reporter | 5:00 JST | ✅ OpenClaw で動作中 |
| sunday-reminder | 日曜 21:00 | ✅ OpenClaw で動作中 |
| monday-reminder | 月曜 11:25 | ✅ OpenClaw で動作中 |

### まだ GHA で動いているもの（OpenClaw に移行すべき）

| 機能 | 現在の場所 | 移行先 |
|------|-----------|--------|
| TikTok 投稿 (朝/夜) | GitHub Actions | OpenClaw |
| X 投稿 (朝/夜) | GitHub Actions | OpenClaw |

---

## 2. OpenAI の使い方

### パッケージ

| パッケージ | インストール | 使用 |
|-----------|-------------|------|
| `openai` (基本API) | ✅ | ✅ 使っている |
| `@openai/agents` (Agent SDK) | ✅ インストール済み | ❌ 使っていない |

### Commander Agent（apps/api/src/agents/commander.js）

**これは何？** 1日分のNudgeを生成するLLMエージェント

**何を使っている？**
- `openai` パッケージ（基本API）
- Structured Outputs（JSON Schema で出力形式を強制）
- ツール呼び出しは使っていない
- Agent SDK は使っていない

**処理フロー:**
```
ユーザー情報（grounding）
    ↓
OpenAI API (gpt-4o + Structured Outputs)
    ↓
JSON出力（5個のNudge + TikTok投稿 + X投稿）
    ↓
Guardrails適用（夜間禁止、30分間隔など）
    ↓
DB保存
```

---

## 3. ローカル vs VPS（超シンプル説明）

### ローカル（今の状態）

```
あなたの Mac
    │
    └── OpenClaw Gateway (port 18789)
            │
            ├── Cron ジョブ（5:00に metrics 投稿）
            ├── Slack 連携（@anicca で応答）
            └── Skills（daily-metrics-reporter など）
```

**問題:**
- Mac がスリープしたら止まる
- Mac が壊れたら全部止まる
- 24/7 動かすには Mac をずっと起動しておく必要がある

### VPS（目指す状態）

```
Hetzner VPS（クラウドのサーバー）
    │
    └── OpenClaw Gateway (Docker で動く)
            │
            ├── Cron ジョブ
            ├── Slack 連携
            └── Skills
                    │
あなたの Mac ─────────┘ (Tailscale で安全に接続)
```

**メリット:**
- 24/7 動く（あなたが寝ていても）
- Mac がなくても動く
- $5/月

---

## 4. OpenAI Agent SDK を使うべきか？

### 今の Commander Agent

**やっていること:** 1回のAPI呼び出しでNudgeを生成

**Agent SDK が必要？** → **不要**

理由:
- 1回で完結する
- ツール呼び出しのループがない
- Structured Outputs で十分

### Agent SDK が必要になる場面

| 機能 | なぜ必要 |
|------|---------|
| Wisdom（深掘り会話） | ユーザーと何度もやり取り → 洞察を生成 |
| 自律的なタスク | エラー時に自動リトライ、複数ステップ |
| Guardrails（品質保証） | 危険なコンテンツを自動ブロック |

---

## 5. 次にやるべきこと

| 優先度 | タスク | 理由 |
|--------|--------|------|
| 1 | VPS に OpenClaw を移行 | 24/7 動くようにする |
| 2 | TikTok/X 投稿を OpenClaw に移行 | GHA を減らす |
| 3 | （将来）Agent SDK を検討 | Wisdom 機能で必要になったら |

---

最終更新: 2026-02-06 10:30 JST
