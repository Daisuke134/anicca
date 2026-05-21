# Thankful v1.0.2 Resubmission Spec

## 開発環境

| 項目 | 値 |
|------|-----|
| プロジェクト | `/Users/anicca/anicca-products/mobile-apps/rork-thankful-gratitude-app` |
| App ID | 6759514159 |
| Bundle ID | app.rork.thankful-gratitude-app |
| Team ID | S5U8UH3JLJ |
| 現バージョン | 1.0.1 (REJECTED) |
| 新バージョン | 1.0.2 |
| ASC API Key | D637C7RGFN (Fastfile 記載) |

## リジェクト理由

### 1. Guideline 2.3.3 — iPad スクショが実アプリを映していない

- en-US に iPad 13インチスクショが2枚ある（set_id: `c22f78a2-1109-465a-9b2d-90019b6a62d3`）
- マーケティング素材であり、実際のアプリ画面ではない

### 2. Guideline 4.0 — 読みにくいタイポグラフィ（iPad）

- iPad Air 11-inch (M3) でレビューされた
- iPhone UI がそのまま iPad にスケールされ、フォントが小さすぎる

## 修正方針

**iPad サポートを完全に外す（iPhone のみ）。**

理由:
- iPad 用の UI 最適化は ROI に合わない
- iPad スクショの再撮影も不要になる
- 両方のリジェクト理由が一撃で解決する

## 修正手順

### Step 1: Fastfile に TARGETED_DEVICE_FAMILY=1 を追加

`.pbxproj` を直接編集しない。Fastfile の `build` lane の `xcargs` に追加。

**ファイル**: `fastlane/Fastfile`
**変更箇所**: `build` lane の `build_app` 呼び出し

```ruby
# 変更前
xcargs: "-allowProvisioningUpdates",

# 変更後
xcargs: "-allowProvisioningUpdates TARGETED_DEVICE_FAMILY=1",
```

これでビルド時に UIDeviceFamily = [1]（iPhone のみ）がバイナリに埋め込まれる。

### Step 2: バージョンを 1.0.2 にバンプ

```bash
cd /Users/anicca/anicca-products/mobile-apps/rork-thankful-gratitude-app
fastlane set_version version:1.0.2
```

### Step 3: ビルド番号を 1 にリセット

```bash
# pbxproj の CURRENT_PROJECT_VERSION を確認（現在 1 のはず）
# fastlane で build すれば自動的に現在の値を使う
```

### Step 4: iPad スクショを ASC から削除

en-US の iPad スクショ set（`c22f78a2-1109-465a-9b2d-90019b6a62d3`）内の2枚:
- `ef0010d6-27f2-4c03-b5e2-235d2351b589`
- `43f2dd21-10e2-4e93-a99f-52bd50218948`

```bash
asc screenshots delete --id ef0010d6-27f2-4c03-b5e2-235d2351b589 --confirm
asc screenshots delete --id 43f2dd21-10e2-4e93-a99f-52bd50218948 --confirm
```

ja ロケールには iPad スクショなし（対応不要）。

### Step 5: Keychain unlock + ビルド

```bash
source ~/.config/mobileapp-builder/.env && security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db

cd /Users/anicca/anicca-products/mobile-apps/rork-thankful-gratitude-app
fastlane build
```

### Step 6: アップロード

```bash
cd /Users/anicca/anicca-products/mobile-apps/rork-thankful-gratitude-app
fastlane upload
```

### Step 7: ASC で新バージョン 1.0.2 を作成 & ビルド紐付け

```bash
# 新バージョン作成（1.0.1 が REJECTED なので新バージョンが必要）
asc apps info edit --app 6759514159 --version 1.0.2 --platform IOS

# ビルド紐付け（アップロード後にビルドIDを取得して紐付け）
# asc review submit --app 6759514159 --version 1.0.2 --build BUILD_ID --confirm
```

### Step 8: 再提出

```bash
asc review submit --app 6759514159 --version 1.0.2 --confirm
```

## 価格修正

現在の価格を確認し、$12.99/week + $59.99/year に修正が必要。
（全アプリ共通タスク — 別途対応）

## 検証チェックリスト

| チェック | 方法 |
|---------|------|
| バイナリが iPhone のみ | `xcrun lipo -info` or ビルドログで UIDeviceFamily 確認 |
| iPad スクショ削除済み | `asc screenshots list` で iPad set が空 |
| バージョン 1.0.2 | `asc apps info view` で確認 |
| ビルド紐付け済み | `asc review status` で確認 |
| 提出完了 | state = WAITING_FOR_REVIEW |
