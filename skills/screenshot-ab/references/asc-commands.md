# ASC CLI 0.48.0 — PPO コマンドリファレンス

## PHASE 0: アプリ情報取得

```bash
# App ID 取得
asc apps list --output json

# バージョン一覧
asc versions list --app $APP_ID --output json

# ロケール一覧
asc localizations list --version-id $VERSION_ID --output json

# スクショサイズ一覧
asc screenshots sizes        # デフォルト（IPHONE_65 + IPAD）
asc screenshots sizes --all  # 全デバイス
```

## PHASE 1: 実験状態確認

```bash
# v2 実験一覧（アプリレベル）
asc product-pages experiments list --v2 --app $APP_ID --output json --pretty

# 特定実験の詳細
asc product-pages experiments view --experiment-id $EXP_ID --v2 --output json --pretty

# Treatment 一覧（CVR 確認）
asc product-pages experiments treatments list --experiment-id $EXP_ID --output json --pretty

# Treatment 詳細
asc product-pages experiments treatments view --treatment-id $TREAT_ID --output json --pretty

# Treatment localization 一覧
asc product-pages experiments treatments localizations list --treatment-id $TREAT_ID --output json --pretty

# 実験停止
asc product-pages experiments update --experiment-id $EXP_ID --started false --v2
```

## PHASE 7: 実験作成 + アップロード + 開始

```bash
# 7-1: 実験作成
asc product-pages experiments create \
  --v2 --app $APP_ID --platform IOS \
  --name "screenshot-ab-vYYYYMMDD" \
  --traffic-proportion 50 \
  --output json

# 7-2: Treatment 作成
asc product-pages experiments treatments create \
  --experiment-id $EXP_ID \
  --name "New Screenshots YYYYMMDD" \
  --output json

# 7-3: Treatment localization 作成
asc product-pages experiments treatments localizations create \
  --treatment-id $TREAT_ID --locale en-US --output json

asc product-pages experiments treatments localizations create \
  --treatment-id $TREAT_ID --locale ja --output json

# 7-4: スクショアップロード（--replace で既存全削除 + アップロード）
asc screenshots upload \
  --version-localization $EN_LOC \
  --path ./export/en/ \
  --device-type IPHONE_65 \
  --replace

asc screenshots upload \
  --version-localization $JA_LOC \
  --path ./export/ja/ \
  --device-type IPHONE_65 \
  --replace

# 7-5: 実験開始（★ ASC CLI 0.48.0 NEW）
asc product-pages experiments update \
  --experiment-id $EXP_ID \
  --started true \
  --v2
```

## クリーンアップ

```bash
# 実験削除（PREPARE_FOR_SUBMISSION 状態のみ）
asc product-pages experiments delete --experiment-id $EXP_ID --confirm

# Treatment 削除
asc product-pages experiments treatments delete --treatment-id $TREAT_ID --confirm

# Treatment localization 削除
asc product-pages experiments treatments localizations delete --localization-id $LOC_ID --confirm

# 個別スクショ削除
asc screenshots delete --id $SCREENSHOT_ID --confirm
```

## スクショダウンロード（現行スクショ確認用）

```bash
asc screenshots list --version-localization $VERSION_LOC_ID --output json --pretty
asc screenshots download --version-localization $VERSION_LOC_ID --output-dir ./downloaded/
```

## JSON パース パターン

```bash
# ID 抽出
... --output json | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['id'])"

# 配列から ID 一覧
... --output json | python3 -c "
import json,sys
for d in json.load(sys.stdin)['data']:
    print(f'{d[\"id\"]}  {d[\"attributes\"].get(\"name\",\"\")}')"

# bundleId でフィルタ
... --output json | python3 -c "
import json,sys
for a in json.load(sys.stdin)['data']:
    if a['attributes']['bundleId']=='ai.anicca.app.ios':
        print(a['id']); break"
```
