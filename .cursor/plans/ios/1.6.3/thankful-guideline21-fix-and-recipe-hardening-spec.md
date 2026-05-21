# Thankful Gratitude App — Guideline 2.1 Fix + Recipe Hardening Spec

**作成日:** 2026-03-01
**ステータス:** 実装中
**App ID:** `6759514159`
**Version ID:** `69420438-dcfc-4946-a37a-ea8ca4dee6b0`

---

## 1. 概要（What & Why）

| 目標 | 内容 |
|------|------|
| **PART A: BUILD** | Thankful Gratitude App の新 IPA をビルドして ASC にアップロード |
| **PART C: SUBMIT** | `asc workflow` でサブスクを含めた正しい審査提出 |
| **PART D: HARDEN** | mobileapp-builder SKILL.md を正確な情報で修正 |
| **PART E: POST** | X（Twitter）で mobileapp-builder スキル更新を投稿 |

---

## 2. 根本原因（確定）

```
前回の提出コマンド:
  asc submit create --app 6759514159 --version-id <ID> --build <ID> --confirm
      ↓
  アプリバイナリのみ提出。サブスクは READY_TO_SUBMIT だったが審査に含まれなかった
      ↓
  Apple 審査: 「課金機能があるのに課金商品が提出されていない」
      ↓
  Guideline 2.1: "products have not been submitted for review"
```

### CLI 調査で判明した事実（2026-03-01 確認済み）

| 事実 | ソース | 結論 |
|------|--------|------|
| `asc publish appstore --submit` はサブスクを自動包含しない | `asc publish appstore --help` の Steps 一覧にサブスク処理なし | `--submit` を使ってもサブスクは含まれない |
| `asc review items-add` でサブスクは追加できない | `--item-type` の有効値: `appStoreVersions`, `appCustomProductPages`, `appEvents`, `appStoreVersionExperiments`, `appStoreVersionExperimentTreatments` のみ | CLI でサブスクを review item として追加不可 |
| サブスク選択は ASC GUI のみ | [Apple 公式](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/submit-an-in-app-purchase/) 「scroll down to In-App Purchases and Subscriptions section. Click Select In-App Purchases or Subscriptions」 | GUI 手動作業が必須（CLI 代替なし） |
| REJECTED version には新 submission を作れない | `asc review submissions-create` が即 REJECTED を返す（実機確認 2026-03-01） | 新 IPA で version state をリセット必須 |

---

## 3. 状態確認（2026-03-01 CLI）

| 項目 | 状態 |
|------|------|
| アプリバージョン | `REJECTED` |
| 全提出 | `COMPLETE`（キャンセル済み）|
| Monthly sub（6759519935） | `READY_TO_SUBMIT` ✅ |
| Annual sub（6759519847） | `READY_TO_SUBMIT` ✅ |

---

## 4. 完了済み手動作業（ダイス実施済み）

| # | 作業 | 状態 |
|---|------|------|
| B-1 | ASC GUI: Monthly + Annual サブスク選択（version ページ） | ✅ 完了済み |
| B-2 | ASC GUI: App Privacy 確認・提出 | ✅ 完了済み |

---

## 5. 実装 TODO リスト（順序厳守）

### PART A: ビルド＆アップロード

| # | タスク | コマンド | 完了条件 |
|---|--------|---------|---------|
| A-1 | `rork-thankful-gratitude-app/fastlane/Fastfile` を作成 | Write ツール | ファイル存在 |
| A-2 | `fastlane build` で IPA 生成 | `FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_CRASH_REPORTING=1 fastlane build` | `build/ThankfulGratitudeApp.ipa` が存在 |
| A-3 | ASC に IPA をアップロード（submit しない） | `asc publish appstore --app 6759514159 --ipa build/ThankfulGratitudeApp.ipa --wait` | processingState = VALID |

### PART C: 審査提出

| # | タスク | コマンド | 完了条件 |
|---|--------|---------|---------|
| C-1 | `.asc/workflow.json` を作成 | Write ツール | ファイル存在 |
| C-2 | `asc workflow run release` で審査提出 | `asc workflow run release` | コマンド成功 |
| C-3 | 状態確認 | `asc review submissions-list --app 6759514159` | state = WAITING_FOR_REVIEW |

### PART D: SKILL.md 修正

| # | タスク | 対象 | 完了条件 |
|---|--------|------|---------|
| D-1 | SKILL.md 修正（詳細は §8 参照） | `.claude/skills/mobileapp-builder/SKILL.md` | 目視確認 |
| D-2 | git add -A && commit && push | — | push 完了 |

### PART E: X 投稿

| # | タスク | 詳細 | 完了条件 |
|---|--------|------|---------|
| E-1 | Postiz/Blotato で X 投稿 | Blotato ID: 11820 / Postiz channel: `cmm6d7m5703rwpr0yr5vtme3w` / aniccaxxx JP アカウント / 英語 | 投稿完了 |

---

## 6. Fastfile 定義（A-1）

**パス:** `rork-thankful-gratitude-app/fastlane/Fastfile`

```ruby
default_platform(:ios)

platform :ios do
  desc "Build IPA for App Store submission"
  lane :build do
    gym(
      scheme: "ThankfulGratitudeApp",
      output_directory: "build",
      output_name: "ThankfulGratitudeApp.ipa",
      export_method: "app-store"
    )
  end
end
```

---

## 7. .asc/workflow.json 定義（C-1）

**パス:** `rork-thankful-gratitude-app/.asc/workflow.json`
（または プロジェクトルート直下 `.asc/workflow.json`）

```json
{
  "env": {
    "APP_ID": "6759514159",
    "VERSION_ID": "69420438-dcfc-4946-a37a-ea8ca4dee6b0"
  },
  "workflows": {
    "release": {
      "description": "Submit Thankful app version for App Store review",
      "steps": [
        {
          "name": "validate_subscriptions",
          "run": "asc validate subscriptions --app $APP_ID"
        },
        {
          "name": "create_submission",
          "run": "SUBMISSION_ID=$(asc review submissions-create --app $APP_ID --output json | python3 -c \"import sys,json;d=json.load(sys.stdin);print(d['data']['id'])\") && echo $SUBMISSION_ID"
        },
        {
          "name": "add_version_to_submission",
          "run": "asc review items-add --submission $SUBMISSION_ID --item-type appStoreVersions --item-id $VERSION_ID"
        },
        {
          "name": "submit",
          "run": "asc review submissions-submit --id $SUBMISSION_ID --confirm"
        },
        {
          "name": "verify",
          "run": "asc review submissions-list --app $APP_ID"
        }
      ]
    }
  }
}
```

**注意:** `asc workflow` の JSON 構文が `SUBMISSION_ID` の動的取得をサポートするか要確認。サポートしない場合は手動でステップを分割して実行。

---

## 8. SKILL.md 修正内容（D-1）

### 修正①: CRITICAL RULE 40（誤情報削除）

**Before（誤）:**
```
asc publish appstore --submit でサブスクが自動的に含まれる
```

**After（正）:**
```
| 40 | **提出前に GUI でサブスク選択必須。CLI でサブスクを review item として追加不可**。
       `asc review items-add --item-type` の有効値にサブスクは含まれない（CLI 確認済み）。
       サブスク選択は ASC GUI のみ。Version ページ → In-App Purchases and Subscriptions → Select。
       Apple 公式: https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/submit-an-in-app-purchase/ |
```

### 修正②: PHASE 12 コマンド

**Before（誤）:**
```
asc submit create --app ... --version-id ... --build ... --confirm
```

**After（正）:**
```
# Step 1: IPA アップロード（--submit しない）
asc publish appstore --app $APP_ID --ipa build/<AppName>.ipa --wait

# Step 2: workflow で submission 作成・提出
asc workflow run release
```

### 修正③: CRITICAL RULE 43（REJECTED 回復フロー）

**After（正）:**
```
| 43 | **REJECTED 後の回復フロー**:
       (1) asc review submissions-cancel → 全提出をキャンセル
       (2) fastlane build → 新 IPA 生成
       (3) asc publish appstore --ipa build/<app>.ipa --wait → 新 build VALID
       (4) ASC GUI: Version ページ → In-App Purchases and Subscriptions → サブスクを選択（手動必須）
       (5) ASC GUI: App Privacy 確認（手動必須）
       (6) asc workflow run release → submission 作成・appStoreVersions 追加・submit
       (7) asc review submissions-list → WAITING_FOR_REVIEW 確認 |
```

### 追加: 「ユーザー手動作業必須」パターン

**mobileapp-builder の新セクションに追加:**
```
## ユーザー手動作業が必須な ASC 操作

| 操作 | CLI 代替 | ASC GUI 手順 |
|------|---------|-------------|
| App Privacy 設定・提出 | なし | App Privacy ページ → 質問回答 → 提出 |
| IAP / サブスク の review 含有 | なし | Version ページ → In-App Purchases and Subscriptions → Select |
| テスター / Beta Group 設定 | `asc testflight beta-groups` で部分可 | — |

→ これらは自動化不可。Spec に「ユーザー手動作業」セクションとして明記すること。
```

---

## 9. X 投稿内容（E-1）

**投稿先:** aniccaxxx JP アカウント（Blotato ID: 11820 / Postiz: `cmm6d7m5703rwpr0yr5vtme3w`）
**言語:** 英語

**下書き:**
```
Just pushed a major update to mobileapp-builder — our AI agent skill for building iOS apps 🚀

It can now handle the full loop autonomously:
research → plan (SDD) → build (TDD + E2E) → submit to App Store → diagnose rejection → revise → iterate

Two steps still require manual work in ASC GUI:
• App Privacy
• Adding subscription groups to the submission

Hey @rudrank — any chance the latter can already be done via the asc CLI?
If there's a way, I'd love to know. Asking because it's the last thing blocking full automation.

#ASCcli #iOSdev #AppStoreConnect
```

---

## 10. 受け入れ条件

| # | 条件 | 確認コマンド |
|---|------|------------|
| A1 | build/ThankfulGratitudeApp.ipa が存在 | `ls rork-thankful-gratitude-app/build/*.ipa` |
| A2 | 新ビルドが VALID | `asc builds list --app 6759514159 --sort -uploadedDate --limit 1` |
| C1 | WAITING_FOR_REVIEW | `asc review submissions-list --app 6759514159` |
| D1 | SKILL.md に正しいコマンド | `grep "publish appstore" SKILL.md` |
| D2 | git push 完了 | `git log --oneline -1` |
| E1 | X 投稿完了 | 目視確認 |

---

## 11. 境界（やらないこと）

| 禁止 | 理由 |
|------|------|
| アプリ機能の変更 | 対象外 |
| RevenueCat Offerings 変更 | 不要 |
| `asc submit create` を使う | サブスクが含まれない古いコマンド |
| B-1/B-2 を再実行 | ダイスが完了済み |

---

## 12. E2E 判定

| 項目 | 値 |
|------|-----|
| UI 変更 | なし |
| 結論 | Maestro E2E 不要（ASC CLI 操作のみ） |
