# 1.6.2 Required Skills (VPS OpenClaw) — 実装/運用に必要な要素まとめ

最終更新: 2026-02-10

このドキュメントは「VPSのOpenClawで Anicca を回すために必要なスキル群」を、**各スキルごとに**:
- 何をするか
- 必要な要素（env / tools / inputs / outputs / API）
- `SKILL.md` テンプレ

まで落とし込んだもの。

前提:
- 本番運用は VPS (`/home/anicca`) の OpenClaw Gateway 1台のみ（Slack二重返信防止）
- スキル配置: `/home/anicca/.openclaw/skills/<skill-name>/SKILL.md`
- cron正本: `/home/anicca/.openclaw/cron/jobs.json`
- 実行証跡: `/home/anicca/.openclaw/cron/runs/<jobId>.jsonl`

注（OpenClawのSKILL.md制約）:
- `SKILL.md` は YAML frontmatter + Markdown instructions
- `metadata` は **1行JSON** 推奨（複数行にしない）
- frontmatterは単純キーのみに寄せる（複雑な階層は metadata(JSON) に寄せる）

---

## 0. 共通（全スキル）

### 0.1 共通ENV（最低限）
- `API_BASE_URL`（Railway API, 例: `https://anicca-proxy-production.up.railway.app`）
- `ANICCA_AGENT_TOKEN`（Bearer）

### 0.2 共通I/O（推奨）
入力（cron message / payloadで渡す想定）:
- `slot`（`morning|afternoon|evening` など）
- `dry_run`（`true|false`）
- `dedupe_key`（二重実行防止の鍵。API側で冪等化する）

出力（最低限ログに残す）:
- `ok`（true/false）
- `audit_id`（監査ログIDが取れるなら）
- `deduped`（true/false）
- `error_class`（分類）

### 0.3 “二重実行” 原則
- 「送信」系は必ず `dedupe_key` で冪等化（API側でブロックするのが正）
- GitHub Actions / Railway cron / OpenClaw cron が同じ送信を叩かないように、運用を1本化する

---

## 1. ops-heartbeat

### 1.1 何をするか
- Railway の ops 制御プレーンを叩き、`ops_events` を処理して Trigger/Reaction を進める。

### 1.2 必要な要素
- env: `API_BASE_URL`, `ANICCA_AGENT_TOKEN`
- tools: `exec`
- API:
  - `POST /api/ops/heartbeat`

### 1.3 SKILL.md テンプレ
```md
---
name: ops-heartbeat
description: Closed-loop ops の制御プレーン（heartbeat）
metadata: {"openclaw":{"emoji":"💓","requires":{"env":["API_BASE_URL","ANICCA_AGENT_TOKEN"],"tools":["exec"]}}}
---

# ops-heartbeat

## Instructions
Run:
```bash
curl -sS -X POST \
  -H "Authorization: Bearer $ANICCA_AGENT_TOKEN" \
  "$API_BASE_URL/api/ops/heartbeat"
```
```

---

## 2. mission-worker

### 2.1 何をするか
- `GET /api/ops/step/next` で queued step を取り、`step_kind` を実行し、`complete` に output+events を返す。

### 2.2 必要な要素
- env: `API_BASE_URL`, `ANICCA_AGENT_TOKEN`
- tools: `exec`, `web_search`, `slack`, `read`, `write`
- API:
  - `GET /api/ops/step/next`
  - `PATCH /api/ops/step/:id/complete`
- 実装必須 step_kind（少なくとも1.6.2で必要）:
  - `run_trend_scan`（trend-hunterフルパイプライン）
  - `detect_suffering`（苦しみ検知。SAFE‑T）
  - `draft_content`, `verify_content`, `post_x`, `post_tiktok`
  - `draft_nudge`, `send_nudge`
  - （任意/後段）`fetch_metrics`, `analyze_engagement`, `diagnose`, `evaluate_hook`

### 2.3 SKILL.md テンプレ（骨格）
```md
---
name: mission-worker
description: queued step を実行して complete する閉ループ実行エンジン
metadata: {"openclaw":{"emoji":"⚙️","requires":{"env":["API_BASE_URL","ANICCA_AGENT_TOKEN"],"tools":["exec","web_search","slack","read","write"]}}}
---

# mission-worker

## Instructions (loop)
1. `GET $API_BASE_URL/api/ops/step/next` で step を取得
2. step がなければ終了
3. step_kind ごとに実行
4. `PATCH .../complete` で output + events を返す

## SAFE‑T (must)
- `detect_suffering` で severity>=0.9 を含む場合は `crisis:detected` を events に含め、
  Slack通知し、通常フロー中断を促す。
```

---

## 3. trend-hunter

### 3.1 何をするか
- “バズっている話題” を複数ソースから集め、13 ProblemTypeに関連付けて hook候補を生成・保存し、`ops_events` を emit する入口。
- 実行は `mission-worker` の `run_trend_scan` step で完結させる。

### 3.2 必要な要素
- env:
  - `API_BASE_URL`, `ANICCA_AGENT_TOKEN`
  - `APIFY_API_TOKEN`（TikTok trends）
  - `TWITTERAPI_KEY`（twitterapi.io）
  - `REDDAPI_API_KEY`（reddapi.dev）
- tools: `exec`, `web_search`
- API（Railway側）:
  - `POST /api/ops/proposal`（trend-hunterのproposal作成）
  - `GET/POST /api/agent/hooks`（hook候補の取得/保存）※設計上
  - `POST /api/ops/events`（events emit）※設計上
- 外部API（VPS側から叩く）:
  - Apify Actor（TikTok trends）
  - reddapi.dev semantic search
  - twitterapi.io advanced_search

### 3.3 SKILL.md テンプレ（proposal作成型）
```md
---
name: trend-hunter
description: トレンド検出 + hook候補生成（入口: proposalを作る）
metadata: {"openclaw":{"emoji":"🧭","requires":{"env":["API_BASE_URL","ANICCA_AGENT_TOKEN","APIFY_API_TOKEN","TWITTERAPI_KEY","REDDAPI_API_KEY"],"tools":["exec","web_search"]}}}
---

# trend-hunter

## Instructions
POST /api/ops/proposal:
```json
{
  "skillName": "trend-hunter",
  "source": "cron",
  "title": "トレンド検出 + hook生成",
  "payload": {},
  "steps": [
    { "kind": "run_trend_scan", "order": 0 }
  ]
}
```
```

---

## 4. suffering-detector

### 4.1 何をするか
- 苦しみ/危機を検知し `detections[]` を作り、`suffering_detected` / `crisis:detected` を emit する入口。
- 実行は `mission-worker` の `detect_suffering` step。

### 4.2 必要な要素
- env: `API_BASE_URL`, `ANICCA_AGENT_TOKEN`
- tools: `exec`, `web_search`, `slack`
- API:
  - `POST /api/ops/proposal`
  - `PATCH /api/ops/step/:id/complete`（mission-worker側）
- SAFE‑T:
  - severity>=0.9 → `crisis:detected` event
  - Slack通知（ops/approval系）

### 4.3 SKILL.md テンプレ（proposal作成型）
```md
---
name: suffering-detector
description: 苦しみ/危機検知（入口: proposalを作る）
metadata: {"openclaw":{"emoji":"🚨","requires":{"env":["API_BASE_URL","ANICCA_AGENT_TOKEN"],"tools":["exec","web_search","slack"]}}}
---

# suffering-detector

## Instructions
POST /api/ops/proposal:
```json
{
  "skillName": "suffering-detector",
  "source": "cron",
  "title": "苦しみ検知",
  "payload": {},
  "steps": [
    { "kind": "detect_suffering", "order": 0 }
  ]
}
```
```

---

## 5. x-poster

### 5.1 何をするか
- X投稿の Proposal を作る（実投稿は `mission-worker` の `post_x`）。

### 5.2 必要な要素
- env: `API_BASE_URL`, `ANICCA_AGENT_TOKEN`
- tools: `exec`
- inputs: `slot`（morning/evening）
- API:
  - `POST /api/ops/proposal`
- ポリシー:
  - Xは投稿のみ（返信禁止）

### 5.3 SKILL.md テンプレ
```md
---
name: x-poster
description: X投稿（入口: proposalを作る。返信禁止）
metadata: {"openclaw":{"emoji":"🐦","requires":{"env":["API_BASE_URL","ANICCA_AGENT_TOKEN"],"tools":["exec"]}}}
---

# x-poster

## Inputs
- slot: morning|evening

## Instructions
POST /api/ops/proposal:
```json
{
  "skillName": "x-poster",
  "source": "cron",
  "title": "X投稿",
  "payload": { "slot": "<slot>" },
  "steps": [
    { "kind": "draft_content", "order": 0 },
    { "kind": "verify_content", "order": 1 },
    { "kind": "post_x", "order": 2 }
  ]
}
```
```

---

## 6. tiktok-poster

### 6.1 何をするか
- TikTok投稿の Proposal を作る（実投稿は `mission-worker` の `post_tiktok`）。

### 6.2 必要な要素
- env: `API_BASE_URL`, `ANICCA_AGENT_TOKEN`
- tools: `exec`
- inputs: `slot`（morning/evening）
- API:
  - `POST /api/ops/proposal`
- ポリシー:
  - TikTokは投稿のみ

### 6.3 SKILL.md テンプレ
```md
---
name: tiktok-poster
description: TikTok投稿（入口: proposalを作る）
metadata: {"openclaw":{"emoji":"🎥","requires":{"env":["API_BASE_URL","ANICCA_AGENT_TOKEN"],"tools":["exec"]}}}
---

# tiktok-poster

## Inputs
- slot: morning|evening

## Instructions
POST /api/ops/proposal:
```json
{
  "skillName": "tiktok-poster",
  "source": "cron",
  "title": "TikTok投稿",
  "payload": { "slot": "<slot>" },
  "steps": [
    { "kind": "draft_content", "order": 0 },
    { "kind": "verify_content", "order": 1 },
    { "kind": "post_tiktok", "order": 2 }
  ]
}
```
```

---

## 7. app-nudge-sender

### 7.1 何をするか
- iOS向けnudgeの Proposal を作る（実送信は `mission-worker` の `send_nudge`）。

### 7.2 必要な要素
- env: `API_BASE_URL`, `ANICCA_AGENT_TOKEN`
- tools: `exec`
- inputs: `slot`（morning/afternoon/evening）
- API:
  - `POST /api/ops/proposal`
- 下流:
  - iOS側: `pending -> pull -> ack` で閉ループ

### 7.3 SKILL.md テンプレ
```md
---
name: app-nudge-sender
description: iOS向けNudge送信（入口: proposalを作る）
metadata: {"openclaw":{"emoji":"📲","requires":{"env":["API_BASE_URL","ANICCA_AGENT_TOKEN"],"tools":["exec"]}}}
---

# app-nudge-sender

## Inputs
- slot: morning|afternoon|evening

## Instructions
POST /api/ops/proposal:
```json
{
  "skillName": "app-nudge-sender",
  "source": "cron",
  "title": "App Nudge送信",
  "payload": { "slot": "<slot>" },
  "steps": [
    { "kind": "draft_nudge", "order": 0 },
    { "kind": "send_nudge", "order": 1 }
  ]
}
```
```

---

## 8. moltbook-monitor

### 8.1 何をするか
- Moltbookを監視し、返信/介入候補を検出して `ops_events` に残す（shadow mode可）。

### 8.2 必要な要素
- env: `API_BASE_URL`, `ANICCA_AGENT_TOKEN`
- tools: `exec`
- API（例）:
  - `POST /api/admin/jobs/moltbook-shadow-monitor`（現行に合わせる）

### 8.3 SKILL.md テンプレ
```md
---
name: moltbook-monitor
description: Moltbook監視（shadow）
metadata: {"openclaw":{"emoji":"👀","requires":{"env":["API_BASE_URL","ANICCA_AGENT_TOKEN"],"tools":["exec"]}}}
---

# moltbook-monitor

## Instructions
```bash
curl -sS -X POST \
  -H "Authorization: Bearer $ANICCA_AGENT_TOKEN" \
  "$API_BASE_URL/api/admin/jobs/moltbook-shadow-monitor"
```
```

---

## 9. moltbook-poster

### 9.1 何をするか
- Moltbookへ投稿（+返信）する。To‑Beは proposal→mission→step で回すのが筋。

### 9.2 必要な要素
- env:
  - `API_BASE_URL`, `ANICCA_AGENT_TOKEN`
  - `MOLTBOOK_BASE_URL`, `MOLTBOOK_ACCESS_TOKEN`
  - `MOLTBOOK_DRY_RUN`（任意）
- tools: `exec`
- API:
  - `POST /api/admin/jobs/moltbook-poster`（現行のjobがあるならそれを叩く）
  - もしくは `POST /api/ops/proposal` に統一（推奨）
- 未確定事項（ここが実装ブロッカーになりやすい）:
  - Moltbook返信ポリシー（頻度/上限/禁止表現/SAFE‑T時中断）

### 9.3 SKILL.md テンプレ（現行job叩き）
```md
---
name: moltbook-poster
description: Moltbook投稿/返信
metadata: {"openclaw":{"emoji":"📝","requires":{"env":["API_BASE_URL","ANICCA_AGENT_TOKEN","MOLTBOOK_BASE_URL","MOLTBOOK_ACCESS_TOKEN"],"tools":["exec"]}}}
---

# moltbook-poster

## Instructions
```bash
curl -sS -X POST \
  -H "Authorization: Bearer $ANICCA_AGENT_TOKEN" \
  "$API_BASE_URL/api/admin/jobs/moltbook-poster"
```
```

---

## 10. roundtable-standup / memory-extract / initiative-generate

### 10.1 何をするか
- roundtable系の admin endpoint を定時で叩く。

### 10.2 必要な要素（共通）
- env: `API_BASE_URL`, `ANICCA_AGENT_TOKEN`
- tools: `exec`

### 10.3 SKILL.md テンプレ（standup例）
```md
---
name: roundtable-standup
description: Daily standup generator
metadata: {"openclaw":{"emoji":"🗣️","requires":{"env":["API_BASE_URL","ANICCA_AGENT_TOKEN"],"tools":["exec"]}}}
---

# roundtable-standup

## Instructions
```bash
curl -sS -X POST \
  -H "Authorization: Bearer $ANICCA_AGENT_TOKEN" \
  "$API_BASE_URL/api/admin/roundtable/standup"
```
```

---

## 11. autonomy-check

### 11.1 何をするか
- 規約違反（例: X返信禁止）、DLQ滞留、失敗率などの合否判定を行い通知する。

### 11.2 必要な要素
- env: `API_BASE_URL`, `ANICCA_AGENT_TOKEN`
- tools: `exec`, `slack`
- API（例）:
  - `/api/admin/jobs/autonomy-check` のようなjobを用意して叩く（実装に合わせる）

### 11.3 SKILL.md テンプレ（URLは実装に合わせて更新）
```md
---
name: autonomy-check
description: Autonomy pass/fail checks + alerts
metadata: {"openclaw":{"emoji":"✅","requires":{"env":["API_BASE_URL","ANICCA_AGENT_TOKEN"],"tools":["exec","slack"]}}}
---

# autonomy-check

## Instructions
Run the API check endpoint and alert if failed.
```

---

## 12. VPS フォルダ構造（完成形）

```text
/home/anicca/.openclaw/
├── openclaw.json
├── skills/
│   ├── ops-heartbeat/
│   │   └── SKILL.md
│   ├── mission-worker/
│   │   └── SKILL.md
│   ├── trend-hunter/
│   │   └── SKILL.md
│   ├── suffering-detector/
│   │   └── SKILL.md
│   ├── x-poster/
│   │   └── SKILL.md
│   ├── tiktok-poster/
│   │   └── SKILL.md
│   ├── app-nudge-sender/
│   │   └── SKILL.md
│   ├── moltbook-monitor/
│   │   └── SKILL.md
│   ├── moltbook-poster/
│   │   └── SKILL.md
│   ├── roundtable-standup/
│   │   └── SKILL.md
│   ├── roundtable-memory-extract/
│   │   └── SKILL.md
│   ├── roundtable-initiative-generate/
│   │   └── SKILL.md
│   └── autonomy-check/
│       └── SKILL.md
├── cron/
│   ├── jobs.json
│   └── runs/
└── logs/
```

---

## 13. jobs.json（完成形サンプル: コピペ用）

注意:
- OpenClawの実際の jobs.json スキーマはバージョンにより差分があり得る。
- ここでは「設計意図として」`sessionTarget=isolated` を基本、`delivery.mode=none` を基本にしている。
- Aniccaが “実際のCLI” で `openclaw cron add/edit/list` を使うなら、最終的な正本は CLI が生成する JSON とする。

```json
{
  "jobs": [
    { "name": "ops-heartbeat", "cron": "*/5 * * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run ops-heartbeat skill." }, "delivery": { "mode": "none" } },
    { "name": "mission-worker", "cron": "* * * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run mission-worker skill." }, "delivery": { "mode": "none" } },

    { "name": "trend-hunter", "cron": "0 */4 * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run trend-hunter skill (proposal for run_trend_scan)." }, "delivery": { "mode": "none" } },
    { "name": "suffering-detector", "cron": "*/5 * * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run suffering-detector skill (proposal for detect_suffering)." }, "delivery": { "mode": "none" } },

    { "name": "x-poster-morning", "cron": "0 9 * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run x-poster slot=morning (proposal)." }, "delivery": { "mode": "none" } },
    { "name": "x-poster-evening", "cron": "0 21 * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run x-poster slot=evening (proposal)." }, "delivery": { "mode": "none" } },

    { "name": "tiktok-poster-morning", "cron": "0 9 * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run tiktok-poster slot=morning (proposal)." }, "delivery": { "mode": "none" } },
    { "name": "tiktok-poster-evening", "cron": "0 21 * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run tiktok-poster slot=evening (proposal)." }, "delivery": { "mode": "none" } },

    { "name": "app-nudge-morning", "cron": "0 9 * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run app-nudge-sender slot=morning (proposal)." }, "delivery": { "mode": "none" } },
    { "name": "app-nudge-afternoon", "cron": "0 14 * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run app-nudge-sender slot=afternoon (proposal)." }, "delivery": { "mode": "none" } },
    { "name": "app-nudge-evening", "cron": "0 20 * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run app-nudge-sender slot=evening (proposal)." }, "delivery": { "mode": "none" } },

    { "name": "moltbook-monitor", "cron": "*/5 * * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run moltbook-monitor skill." }, "delivery": { "mode": "none" } },
    { "name": "moltbook-poster", "cron": "30 20 * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run moltbook-poster skill." }, "delivery": { "mode": "none" } },

    { "name": "roundtable-standup", "cron": "0 9 * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run roundtable-standup." }, "delivery": { "mode": "none" } },
    { "name": "roundtable-memory-extract", "cron": "55 8 * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run roundtable-memory-extract." }, "delivery": { "mode": "none" } },
    { "name": "roundtable-initiative-generate", "cron": "5 9 * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run roundtable-initiative-generate." }, "delivery": { "mode": "none" } },

    { "name": "autonomy-check", "cron": "0 3 * * *", "sessionTarget": "isolated", "payload": { "kind": "agentTurn", "message": "Run autonomy-check skill." }, "delivery": { "mode": "none" } }
  ]
}
```

