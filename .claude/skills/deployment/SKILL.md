---
name: deployment
description: Covers device deployment, Landing Page (Netlify) deployment, App Store submission gates, release procedures, and error recovery for Anicca. Use when deploying to device, simulator, Netlify, or App Store.
disable-model-invocation: true
---

# Deployment Rules

## 1. Device Deploy

```bash
ios-deploy --detect                    # 接続確認
cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_CRASH_REPORTING=1 fastlane build_for_device
# 未接続 → fastlane build_for_simulator
```

**デプロイ前にユーザー確認必須。** テスト完了後「実機/シミュレータ/スキップ」を提示。

## 2. Landing Page (Netlify)

**dev push = 自動デプロイ。** Worktreeの場合:
```bash
cd apps/landing && npx netlify deploy --build   # プレビュー
# OK → dev マージ → 自動デプロイ
```

## 3. App Store Link

直接URL禁止。`https://aniccaai.com/app` リダイレクトを使う。

## 4. App Store 提出ゲート（全通過必須）

| # | Gate | Command | Pass |
|---|------|---------|------|
| 1 | Greenlight | `greenlight preflight .` | CRITICAL=0 |
| 2 | PrivacyInfo | aniccaios/PrivacyInfo.xcprivacy確認 | UserDefaults+CA92.1申告あり |
| 3 | ローカライズ | jest i18nテスト | T-L1〜T-L8 PASS |
| 4 | 日本語メタデータ | ASC確認 | ja-JP設定済み |

**Greenlight未インストール時:** `cd /tmp && git clone https://github.com/RevylAI/greenlight.git && cd greenlight && make build`

## 5. Release手順

```bash
git checkout main && git pull && git checkout -b release/X.Y.Z
cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_CRASH_REPORTING=1 fastlane set_version version:X.Y.Z
cd .. && git add -A && git commit -m "chore: bump version to X.Y.Z" && git push -u origin release/X.Y.Z
cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_CRASH_REPORTING=1 fastlane full_release
cd .. && git checkout dev && git merge release/X.Y.Z && git push origin dev
```

## Error Recovery

| Error | Fix |
|-------|-----|
| Invalid Pre-Release Train | `fastlane set_version` で修正 |
| CFBundleShortVersionString | バージョン番号を上げる |
| upload失敗 | `fastlane upload` 再実行 |
| submit失敗 | ASC確認 → `submission_information` 修正 |
