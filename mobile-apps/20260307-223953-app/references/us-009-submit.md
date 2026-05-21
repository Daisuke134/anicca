# US-009: App Store Submission

## Step -1: Dependency Check (MANDATORY)

Source: Microsoft Azure Pipelines — Stages
https://learn.microsoft.com/en-us/azure/devops/pipelines/process/stages
> "a stage runs if all of the stages that it depends on have completed and succeeded"

**US-001~008 全てが passes:true でないと US-009 は実行しない:**

```bash
INCOMPLETE=$(jq -r '.userStories[] | select(.passes == false and .id != "US-009") | .id' prd.json)
if [ -n "$INCOMPLETE" ]; then
  echo "❌ Cannot proceed: $INCOMPLETE still passes:false"
  echo "US-009 requires all prior US to be completed."
  exit 0  # passes:false のまま終了
fi
echo "✅ All dependencies passed"
```

## Step 0: apple-appstore-reviewer Audit (MANDATORY)

Source: apple-appstore-reviewer SKILL.md
> "You are the review gatekeeper"
> "P0 (Blocker): Very likely to cause rejection"

**提出前に apple-appstore-reviewer スキルを実行し、P0/P1 = 0 までループ:**

1. apple-appstore-reviewer スキルを実行（コードベース全体をレビュー）
2. Risk Register を取得
3. P0/P1 がある → 修正 → 再実行
4. P0/P1 = 0 になるまでループ

### PROHIBITED
- ⛔ P0/P1 > 0 で提出するな
- ⛔ レビューをスキップするな



Source: rshankras WORKFLOW.md Phase 6 + rudrankriyam asc-release-flow

## Source Skills (参考のみ — 読み込み不要。コマンドは下記に全てインライン)
元ネタ: asc-submission-health, asc-release-flow

## Quality Gate (MANDATORY — US-008e 検証)
```bash
# asc validate must have passed
asc validate --app "$APP_ID" --version-id "$VERSION_ID" --platform IOS 2>&1 | grep -q "Errors: 0" \
  || { echo "GATE FAIL: validation errors exist"; exit 1; }
```

## Step 1: App Privacy（自動）

⛔ **自動実行する。人間に確認を求めない。** セッションキャッシュが効いている限り 2FA は不要。

### 1.1: Privacy 宣言 + 公開
```bash
source ~/.config/mobileapp-builder/.env

echo '{"schemaVersion":1,"dataUsages":[{"dataProtections":["DATA_NOT_COLLECTED"]}]}' > /tmp/privacy.json

APPLY_RESULT=$(ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web privacy apply \
  --app "$APP_ID" --file /tmp/privacy.json --apple-id "$APPLE_ID" 2>&1)

if echo "$APPLY_RESULT" | grep -q '"applied":true'; then
  ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web privacy publish \
    --app "$APP_ID" --confirm --apple-id "$APPLE_ID"
  echo "✅ App Privacy published"
else
  # セッション切れの場合のみここに来る（通常は来ない）
  echo "WAITING_FOR_HUMAN: 2FA code needed"
  cat >> progress.txt << 'MSG'
⏸️ セッションキャッシュ切れ。
iPhone に届く 6 桁のコードを Slack で返信してください。
エージェントが --two-factor-code 付きで再実行します。
MSG
  exit 1
fi
```

### 1.2: 収集データありの場合
```bash
cat > /tmp/privacy.json << 'EOF'
{
  "schemaVersion": 1,
  "dataUsages": [
    {
      "category": "USAGE_DATA",
      "purposes": ["ANALYTICS"],
      "dataProtections": ["DATA_NOT_LINKED_TO_YOU"]
    }
  ]
}
EOF

ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web privacy apply \
  --app "$APP_ID" --file /tmp/privacy.json --apple-id "$APPLE_ID"
ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web privacy publish \
  --app "$APP_ID" --confirm --apple-id "$APPLE_ID"
```

### セッション管理
- セッションキャッシュ: `~/.asc/web/`（`ASC_WEB_SESSION_CACHE_BACKEND=file` が .env に設定済み）
- 通常運用: セッションが生きている限り完全自動（2FA 不要）
- 期限切れ時のみ WAITING_FOR_HUMAN（Slack で 6桁コード返すだけ）

### 1.3: 検証
```bash
ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web privacy pull --app "$APP_ID"
# published: true を確認
```

## Step 2: Submit for Review
```bash
asc review submissions-create --app $APP_ID
asc review items-add --submission-id $SUBMISSION_ID --version-id $VERSION_ID
asc review submissions-submit --submission-id $SUBMISSION_ID
```
Source: CRITICAL RULE 22
> 「提出の正解コマンドは submissions-create + items-add + submissions-submit」

## Step 3: Confirm
```bash
asc review submissions-list --app $APP_ID
# state = WAITING_FOR_REVIEW を確認
```

## Acceptance Criteria
- .app-privacy-done exists
- asc review submissions-submit succeeds
- State = WAITING_FOR_REVIEW
- Slack #metrics notified: 「🎉 WAITING_FOR_REVIEW」
