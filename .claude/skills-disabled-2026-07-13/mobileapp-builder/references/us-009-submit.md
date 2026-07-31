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

## Step 1: App Privacy 確認（検証のみ — US-005a Step 5.3 で設定済み）

```bash
source ~/.config/mobileapp-builder/.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db 2>/dev/null || true

PRIVACY_CHECK=$(ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web privacy pull --app "$APP_ID" --apple-id "$APPLE_ID" 2>&1)
echo "$PRIVACY_CHECK" | grep -q '"published":true' && echo "✅ App Privacy confirmed" || echo "⚠️ App Privacy not published — US-005a Step 5.3 を再実行"
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
