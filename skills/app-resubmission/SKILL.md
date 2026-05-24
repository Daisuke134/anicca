# app-resubmission

App Store リジェクト検出 → 理由取得 → CC で修正 → 再提出する自動スキル。

## フロー

```
1. 全アプリの ASC 状態チェック
2. REJECTED 検出 → リジェクト理由取得
3. Slack 通知
4. CC 起動 → リジェクト内容に基づき修正
5. 再 submit
```

## 手順

### Step 1: 全アプリの状態チェック

```bash
# mobile-apps/ 内の全アプリディレクトリを走査
for APP_DIR in /Users/anicca/anicca-project/mobile-apps/20*-app; do
  if [ -f "$APP_DIR/prd.json" ]; then
    APP_ID=$(python3 -c "import json; d=json.load(open('$APP_DIR/prd.json')); print(d.get('appId',''))" 2>/dev/null)
    APP_NAME=$(python3 -c "import json; d=json.load(open('$APP_DIR/prd.json')); print(d.get('appName',''))" 2>/dev/null)
    if [ -n "$APP_ID" ]; then
      echo "Checking $APP_NAME ($APP_ID)..."
      STATE=$(asc apps status --id "$APP_ID" --output json 2>/dev/null | jq -r '.data.attributes.appStoreState // "UNKNOWN"')
      echo "  State: $STATE"
      if [ "$STATE" = "REJECTED" ] || [ "$STATE" = "DEVELOPER_REJECTED" ]; then
        echo "  🔴 REJECTED: $APP_NAME"
        # Step 2 に進む
      fi
    fi
  fi
done
```

### Step 2: リジェクト理由取得

```bash
# ASC Web Review API でリジェクト理由とメッセージを取得
REVIEW_INFO=$(asc web review show --app "$APP_ID" --output json 2>/dev/null)
REJECTION_REASON=$(echo "$REVIEW_INFO" | jq -r '.rejectionReason // "Unknown"')
MESSAGES=$(echo "$REVIEW_INFO" | jq -r '.messages[]?.body // empty')

# rejection.json に保存
cat > "$APP_DIR/rejection.json" << EOF
{
  "appId": "$APP_ID",
  "appName": "$APP_NAME",
  "state": "$STATE",
  "rejectionReason": "$REJECTION_REASON",
  "messages": "$MESSAGES",
  "detectedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
```

### Step 3: Slack 通知

```bash
curl -s -X POST "${SLACK_WEBHOOK_AGENTS}" \
  -H "Content-type: application/json" \
  -d "{\"text\":\"🔴 REJECTED: $APP_NAME ($APP_ID)\\nReason: $REJECTION_REASON\\nMessages: $MESSAGES\"}"
```

### Step 4: CC で修正

```bash
cd "$APP_DIR"
source ~/.config/mobileapp-builder/.env

# リジェクト内容をCLAUDE.mdに追記
cat >> CLAUDE.md << REJECTION_CONTEXT

## ⚠️ REJECTION FIX REQUIRED

This app was rejected by Apple. Fix the issues and resubmit.

**Rejection Reason:** $REJECTION_REASON
**Messages:** $MESSAGES

1. Read rejection.json for full details
2. Fix the issues described
3. Rebuild and resubmit: increment CURRENT_PROJECT_VERSION, archive, upload, submit
REJECTION_CONTEXT

# CC 起動（ralph.sh と同じパターン）
echo "Fix rejection and resubmit" | claude --dangerously-skip-permissions --verbose --print --output-format stream-json --model opus < CLAUDE.md
```

### Step 5: 再 submit 確認

```bash
STATE=$(asc apps status --id "$APP_ID" --output json 2>/dev/null | jq -r '.data.attributes.appStoreState')
if [ "$STATE" = "WAITING_FOR_REVIEW" ]; then
  curl -s -X POST "${SLACK_WEBHOOK_AGENTS}" \
    -H "Content-type: application/json" \
    -d "{\"text\":\"✅ RESUBMITTED: $APP_NAME ($APP_ID) → WAITING_FOR_REVIEW\"}"
fi
```

## 注意事項

- `asc web review show` は 2FA セッションが必要な場合がある
- リジェクト理由が App Privacy 関連の場合、ASC Web で手動設定が必要（WAITING_FOR_HUMAN）
- CC のイテレーション上限は 10（リジェクト修正は通常 1-3 イテレーションで済む）
