# Thankful Gratitude App — Factory Learning Log

**目的:** mobileapp-builder スキルを改善するための学習記録。
ここに書いたことは全てスキル・spec・iap-bible に反映する。

---

## セッション: 2026-02-24

### PHASE 1 — TASK 1: コード変更 → TestFlight upload

**✅ 完了**

| タスク | 内容 | 結果 |
|--------|------|------|
| TASK 1-A | AppViewModel.swift: 英語固定 | ✅ |
| TASK 1-B | SettingsView.swift: 言語Picker削除 | ✅ |
| TASK 1-C | PaywallView.swift: accessibilityIdentifier追加 | ✅ |
| TestFlight | fastlane build + upload | ✅ 1.0.0 アップロード完了 |

**学習:**
- スキルに `release` laneは定義されていなかった。実際は `build` + `upload` を分けて実行。
- SourceKitの「No such module 'RevenueCat'」エラーは false positive（コンパイルは通る）
- AppLanguage enumを `language: .english` に固定後、LanguagePickerを削除してもコンパイル通る

### PHASE 2 — TASK 3: IAPレビュースクリーンショット

**❌ APIでは完了不可 → ダイスが手動でやる必要あり**

| 試みた方法 | 結果 | 理由 |
|-----------|------|------|
| `asc subscriptions images create` | `FAILED` | S3マルチパートupload IDが即失効 |
| Python直接API（S3 PUT + PATCH commit） | `FAILED` | Apple側でimage処理失敗（width:0, height:0） |
| JPEG変換して再試み | `FAILED` | 同様 |
| S3 CompleteMultipartUpload | `403 Access Denied` | Apple S3バケットに直接CompleteMPUは禁止 |

**学習:**
- `asc subscriptions images create` はS3 URLを返すが、**PUTしてもApple側が処理できない**
  - Apple APIの`subscriptionImages`エンドポイントのS3アップロードは CLIが正しく動作していない
  - APIの `uploaded: true` PATCH後も `FAILED` になる
  - width:0 height:0 は「ファイルを受け取ったが画像として認識できない」状態
- **IAP レビュースクリーンショットはASC Webから手動アップロードが唯一の確実な方法**
  - URL: https://appstoreconnect.apple.com → Apps → Thankful → In-App Purchases → 各サブ → Edit → Review Information → Screenshot

**ダイスへのアクション指示:**
```
1. https://appstoreconnect.apple.com にアクセス
2. Thankful Gratitude App → In-App Purchases
3. "Thankful Pro Annual" → Edit → Review Information → Screenshot欄
   → 以下のファイルをアップロード: /tmp/paywall-iap.jpg (900x1956, 79KB)
4. "Thankful Pro Monthly" でも同じ操作
5. 両方Save後、状態がREADY_TO_SUBMITになることを確認
```

### スキルへの反映（旧記録 — 下記で訂正済み）:
- `iap-bible.md` の「IAPレビュースクリーンショット」セクション追加: ASC Webから手動アップロード推奨
- `mobileapp-builder` PHASE 8 に「IAPレビュースクリーンショットはASC Webのみ（API不可）」を追記

---

## セッション: 2026-02-24（続き）— 訂正・追加学習

### 罪1: `subscriptions images` と `subscriptions review-screenshots` の混同（+ 最終確認）

**最初のスキルに書いてあったこと:** `asc subscriptions images create`
**実際に起きたこと:** FAILED → 「APIは壊れている」と結論 → ASC Web手動に格下げ
**一次的な真実:** 全く別のAPIを叩いていた

| コマンド | 実際の意味 |
|---------|-----------|
| `asc subscriptions images create` | サブスクの**販促画像**（`subscriptionImages` エンドポイント） |
| `asc subscriptions review-screenshots create` | App Store **レビュー用スクショ**（`subscriptionAppStoreReviewScreenshots` エンドポイント） |

**2026-02-24 追加確認:** `review-screenshots create` も試した。同じ 400 "Invalid uploadId" で失敗。
理由: Apple S3 バケットの multipart uploadId が create 直後に無効化される（`asc` CLI が返す `uploadOperations` の URL は使えない）。

**最終的な真実: ASC Web からの手動アップロードが唯一の解決策。**

**スキルへの反映（完了）:**
- PHASE 7: 「CLI 不可、ASC Web から手動」に更新済み（2026-02-24）

---

### 罪2: TestFlight build upload ≠ TestFlight 配布

**スキルに書いてあったこと:** `fastlane build` + `fastlane upload` → 完了
**実際に起きたこと:** build 2 がアップロードされたが TestFlight グループに配布されなかった。ダイスは「見えない」と怒った。
**真実:** ASC に build がある = TestFlight で見える ではない。ベータグループへの追加が別途必要。

確認コマンド:
```bash
# build がグループに追加されているか確認
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.appstoreconnect.apple.com/v1/builds/<BUILD_ID>/betaGroups"
# data: [] = グループ未設定 → TestFlightに表示されない
```

追加コマンド:
```bash
asc testflight beta-builds add --build "<BUILD_ID>" --group "<GROUP_ID>"
```

**スキルへの反映（MUST）:**
- PHASE 10 末尾: `fastlane upload` の後に必ずベータグループへの追加を実行する

---

### 罪3: スクショのヘッドラインパイプラインが前提なしに実行不可

**スキルに書いてあったこと:** PHASE 9 Step 2 で `make generate-store-screenshots` を実行
**実際に起きたこと:** `ScreenshotTests.swift` + `Makefile` + `scripts/` が存在しない → `axe screenshot` だけで終了 → ヘッドラインなし生スクショをASCにアップロード
**真実:** PHASE 3 に前提セットアップ（ScreenshotTests.swift等）の記載がなかった。PHASE 9 にハードゲートがなかった。

**スキルへの反映（MUST）:**
- PHASE 3: `ScreenshotTests.swift` + `Makefile generate-store-screenshots` + `scripts/` を必須タスクとして追加
- PHASE 9 Step 2: ハードゲート「ヘッドラインなし = ASCアップロード禁止」を追加

---

### 全体の教訓

**スキルに1行でも間違いがあれば、エージェントは全力でその間違いに従う。**
スキルが全ての真実。エージェントはスキルを盲目的に信じる。だからスキルが正しくなければ提出は永遠に失敗する。

スキルは「これを読めば質問なしで App Store 提出できる」レベルでなければならない。

---

## 記録フォーマット

```
### [PHASE X] 学習タイトル
- **スキルの記述:** スキルに何と書いてあったか
- **実際に起きたこと:** 何が違ったか / 何が足りなかったか
- **修正:** どう直したか
- **スキルへの反映:** SKILL.md / iap-bible.md / spec の何を直すべきか
```
