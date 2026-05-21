# screenshot-fix spec（2026-02-24 更新）

## 全体方針

**screenshot-ab の PHASE 4 生成エンジンを XCUITest パイプライン → Pencil MCP（screenshot-creator）に差し替える。**

raw スクリーンショット（XCUITest 撮影の実機 UI）は PhoneMockup の中身として使い続ける。
フレーム・テキスト合成は `pencil_export.py` が担当（`process_screenshots.py` は廃止）。

---

## 実行順序

| # | FIX | 対象ファイル | 状態 |
|---|-----|------------|------|
| 1 | 外枠修正（PhoneMockup ボーダー追加） | `docs/screenshots/scripts/pencil_export.py` | ✅ 完了 |
| 2 | 出力先を `processed/` に統一 | `docs/screenshots/scripts/pencil_export.py` | ✅ 完了 |
| 3 | screenshot-ab PHASE 4 を screenshot-creator に差し替え | `.claude/skills/screenshot-ab/SKILL.md` | ✅ 完了 |
| 4 | screenshot-ab PHASE 6 を slack-approval スキルに統一 | `.claude/skills/screenshot-ab/SKILL.md` | ✅ 完了 |
| 5 | screenshot-creator Step 7 に pencil_export.py 実行を明記 | `.claude/skills/screenshot-creator/SKILL.md` | ✅ 完了 |
| 6 | mobileapp-builder PHASE 9 を screenshot-creator 呼び出しに更新 | `.claude/skills/mobileapp-builder/SKILL.md` | ✅ 完了 |
| 7 | extract_screenshots.py を Xcode 26 新 API 対応に修正 | `docs/screenshots/scripts/extract_screenshots.py` | ✅ 完了（実装済み） |

---

## FIX 1+2: pencil_export.py — 外枠追加 + 出力先変更

**問題 1**: PhoneMockup の境界が分からない（背景色と同化）
**正解**: 角丸に沿った薄いボーダー（`#1A1A1A`, alpha=0.12, 幅 3px）を描画する

**問題 2**: 出力先が `pencil_export/` になっている → `processed/` に統一する
**正解**: OUT を `docs/screenshots/processed/` に変更し、ファイル名も `screen1.png` 形式に合わせる

変更箇所（`pencil_export.py`）:
- `OUT` を `docs/screenshots/pencil_export/` → `docs/screenshots/processed/` に変更
- ファイル名を `ss01_hero.png` → `screen1.png` 形式に統一
- `make_screenshot()` の PhoneMockup 描画後に `rounded_rectangle` でアウトライン追加

---

## FIX 3: screenshot-ab PHASE 4 差し替え

**現状（PHASE 4）**:
```bash
# Step 4-2: l.md パイプラインを走らせる
make generate-store-screenshots
# 内部: XCUITest → extract_screenshots.py → process_screenshots.py
```

**正解（PHASE 4）**:
```
## PHASE 4: スクショ生成（screenshot-creator）

→ .claude/skills/screenshot-creator/SKILL.md を読んで実行する

1. raw スクショ確認: docs/screenshots/raw/screen1~3.png が存在するか確認
   - なければ: `make capture-only` で XCUITest 撮影だけ実行
   - あれば: そのまま次へ

2. screenshots.yaml からヘッドライン・サブテキストを取得

3. pencil_export.py を実行してフレーム合成:
   python3 docs/screenshots/scripts/pencil_export.py

4. 出力確認: docs/screenshots/processed/screen1~3.png が生成されたか確認

出力:
docs/screenshots/processed/
├── screen1.png（780×1688 @2x）
├── screen2.png
└── screen3.png
```

---

## FIX 4: screenshot-ab PHASE 6 を slack-approval に統一

**現状（PHASE 6）**: `references/slack-approval.md` という独自実装でテキスト送信

**正解（PHASE 6）**:
```
## PHASE 6: Slack 承認（ダイスが確認）

1. processed/screen1~3.png を Slack C091G3PKHL2 にアップロード
   （Slack Files v2 API: files.getUploadURLExternal → PUT → files.completeUploadExternal）

2. slack-approval スキルで承認ボタン送信:
   → .claude/skills/slack-approval を読んで requestApproval() を実行
   → title: "📸 App Store スクリーンショット確認"
   → detail: "ヘッドライン: {headline}\nvisual-qa: {score}/50\nPHASE 7（ASCアップロード）に進みますか？"

3. 戻り値で分岐:
   - approved → PHASE 7 へ
   - denied   → PHASE 3（ヘッドライン生成）に戻る
```

---

## FIX 5: screenshot-creator SKILL.md Step 7 更新

**現状（Step 7）**: `.pen` ファイルのフレームID報告で終わっている

**正解（Step 7）**:
```
## Step 7: PNG エクスポートとファイルパス報告

1. mcp__pencil__get_editor_state でファイルパス確認
2. 各フレームの get_screenshot で最終目視確認
3. pencil_export.py を実行して PNG 生成:
   python3 docs/screenshots/scripts/pencil_export.py
4. 出力確認: docs/screenshots/processed/screen1~3.png
5. 報告フォーマット（変更なし）
```

---

## FIX 6: mobileapp-builder PHASE 9 Step 2 更新

**現状（重複・罪）**: `make generate-store-screenshots` を直接呼ぶ独自実装

**正解（1行に変える）**:
```
→ .claude/skills/screenshot-creator/SKILL.md を読んで Step 1〜7 を実行する
  （A/B テストではなく新規生成のため PHASE 1/2 はスキップ）
  → P6 の Slack 承認を必ず通す
  → P7 で ASC アップロード
```

---

## FIX 7: extract_screenshots.py を Xcode 26 新 API 対応に修正

**問題**: `xcresulttool get --format json` は Xcode 26 で deprecated（`--legacy` 必須 + JSON が参照ベース）

**正解**: 新 API `xcresulttool get test-results activities --test-id` を使う

確認済み手順:
```bash
# Step A: test IDs 取得
xcrun xcresulttool get test-results tests \
  --path docs/screenshots/output.xcresult \
  --format json

# Step B: 各テストの attachment 取得
xcrun xcresulttool get test-results activities \
  --path docs/screenshots/output.xcresult \
  --test-id "ScreenshotTests/testCaptureScreen1()" \
  --format json

# Step C: export
xcrun xcresulttool export \
  --path docs/screenshots/output.xcresult \
  --id <payloadId> \
  --output-path docs/screenshots/raw/screen1.png \
  --type file
```

---

## 受け入れ条件

| # | 条件 | 判定方法 |
|---|------|---------|
| 1 | `pencil_export.py` 実行 → `processed/screen1~3.png` 生成される | ファイル存在確認 |
| 2 | PhoneMockup に薄いボーダーが表示される | 目視確認 |
| 3 | `screenshot-ab` 実行時に `make generate-store-screenshots` が呼ばれない | SKILL.md 確認 |
| 4 | PHASE 6 で Slack に ✅/❌ ボタンが届く | Slack 確認 |
| 5 | ✅ 押下 → ASC にアップロードされる | ASC 確認 |
| 6 | ❌ 押下 → PHASE 3 に戻る | ログ確認 |

---

## 境界（やらないこと）

- `ScreenshotTests.swift` は変更しない
- `Makefile` の `capture-only` ターゲットは既存のまま（raw 撮影は XCUITest 継続）
- `process_screenshots.py` は削除しない（旧パイプラインのバックアップとして残す）
