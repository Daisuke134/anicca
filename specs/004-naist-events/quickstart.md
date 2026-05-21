# Quickstart: naist-events テストシナリオ

## 前提条件
- Mac Mini SSH接続: `ssh anicca@100.99.82.95`
- OpenClaw PATH: `export PATH=/opt/homebrew/bin:$PATH`
- スキルパス: `/Users/anicca/.openclaw/skills/naist-events/`

## Scenario 1: DRY_RUNでのスキャン確認

```bash
ssh anicca@100.99.82.95
export PATH=/opt/homebrew/bin:$PATH
cd /Users/anicca/.openclaw/skills/naist-events
DRY_RUN=1 node scripts/scan.js
# 期待: [naist-events] スキャン完了: 新着N件 / スキップN件
```

## Scenario 2: ユニットテスト全件実行

```bash
ssh anicca@100.99.82.95
cd /Users/anicca/.openclaw/skills/naist-events
export PATH=/opt/homebrew/bin:$PATH
npx jest --no-coverage 2>&1 | tail -20
# 期待: Tests: N passed, N total
```

## Scenario 3: カレンダー追加のドライラン

```bash
ssh anicca@100.99.82.95
export PATH=/opt/homebrew/bin:$PATH
cd /Users/anicca/.openclaw/skills/naist-events
DRY_RUN=1 node scripts/add-to-calendar.js "テストイベント" "2026-03-02" "14:00" "15:00" "D207"
# 期待: [DRY_RUN] カレンダー追加スキップ: テストイベント
```

## Scenario 4: 重複防止テスト

```bash
# 1回目実行（DRY_RUN=0）
DRY_RUN=0 node scripts/scan.js
# 2回目実行（同じイベントはスキップされる）
DRY_RUN=1 node scripts/scan.js
# 期待: 新着0件 / スキップN件
```

## Scenario 5: cronジョブ確認

```bash
ssh anicca@100.99.82.95
cat /Users/anicca/.openclaw/cron/jobs.json | python3 -m json.tool | grep -A5 naist-events
# 期待: "id": "naist-events-scan" が存在する
```
