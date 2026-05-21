# Quickstart: x402 Factory Skill テスト手順

**Branch**: `005-x402-factory`

---

## User Story 1 独立テスト（P1: produce モード）

**前提**: `skill_name=emotion-detector` を使ってエンドツーエンドで確認する。

### Step 1: エンドポイントが動くことを確認

```bash
# staging で awal テスト
npx awal@2.0.3 x402 pay https://anicca-proxy-staging.up.railway.app/api/x402/emotion-detector \
  -X POST \
  -d '{"text": "I feel really anxious about my presentation tomorrow"}'

# 期待: HTTP 200 OK + JSON { emotion_id: "...", primary_emotion: "...", intensity: "...", ... }
```

### Step 2: ClawHub 掲載確認

```bash
ssh anicca@100.99.82.95 "clawhub search emotion-detector"
# 期待: emotion-detector が結果に表示される
```

### Step 3: Moltbook 投稿確認

Moltbook の自分の feed を確認 → `emotion-detector` の宣伝投稿が存在すること。

### Step 4: to-agents-learning.md 確認

```bash
ssh anicca@100.99.82.95 "grep 'emotion-detector' /Users/anicca/.openclaw/workspace/to-agents/to-agents-learning.md"
# 期待: emotion-detector の Run エントリが存在する
```

### Step 5: Slack #metrics 確認

Slack `#metrics` を確認 → 完了報告メッセージ（endpoint URL + ClawHub ID + Moltbook post ID）が存在すること。

---

## User Story 2 独立テスト（P2: discover モード）

```bash
# Anicca に discover mode を実行させる（手動トリガー）
ssh anicca@100.99.82.95 "openclaw agent --message 'Execute to-agents-skill. mode=discover.' --deliver"

# 期待1: Slack #metrics に提案メッセージが1件届く（エンドポイント未作成）
# 期待2: proposals.json に status=pending エントリが追加される
# 期待3: 承認（✅）なしにエンドポイントは作成されない
```

---

## User Story 3 独立テスト（P3: measure モード）

```bash
# measure モード実行
ssh anicca@100.99.82.95 "openclaw agent --message 'Execute to-agents-skill. mode=measure.' --deliver"

# 期待: Slack #metrics に未達スキル（0コール）の改善提案が届く
```

---

## Mac Mini インストール確認

```bash
ssh anicca@100.99.82.95 "ls /Users/anicca/.openclaw/skills/to-agents-skill/"
# 期待: SKILL.md が存在する

ssh anicca@100.99.82.95 "cat /Users/anicca/.openclaw/cron/jobs.json | grep to-agents-skill"
# 期待: to-agents-skill の cron エントリが存在し enabled=true
```
