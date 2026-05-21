# Spec: screenshot-ab — App Store スクリーンショット A/B テスト

**Status:** E2E 実行完了 → スキル修正待ち
**Date:** 2026-04-01（E2E 完了: 2026-04-01）
**Author:** Claude Code + ダイス
**ファイルパス:** `.cursor/plans/screenshot-ab-spec.md`

---

## 1. 概要

App Store の Product Page Optimization (PPO) 実験を完全自動で回すクローズドループ。
前回結果チェック → ヘッドライン生成 → スクショ生成 → QA → 承認 → アップロード → 実験開始。

| 項目 | 値 |
|------|-----|
| App | Daily Self Care - Anicca (`6755129214`) |
| Bundle ID | `ai.anicca.app.ios` |
| ロケール | `en-US` + `ja` |
| 画面数 | 4画面 × 2言語 = 8スクリーン |
| cron | `0 10 * * 1`（毎週月曜 10:00 JST） |
| ASC CLI | **0.48.0** — `--started true` は直接使えない。reviewSubmissions API 必須 |
| スクショ生成 | ParthJadhav/app-store-screenshots（Next.js + html-to-image） |
| iPhone フレーム | ParthJadhav 同梱 `mockup.png`（1022x2082, 透明スクリーン領域） |
| デザインサイズ | **1320x2868 (6.9")** でデザイン → 4サイズに自動スケール |
| ASC upload device-type | **APP_IPHONE_67** |
| 実行環境 | Mac Mini（OpenClaw cron） |

---

## 2. 4画面の定義 — 現在の App Store スクショ（= Control）

| # | 画面 | EN ヘッドライン | JA ヘッドライン | アプリ画面の内容 |
|---|------|---------------|---------------|----------------|
| 1 | Nudge カード（自己慈悲系） | "Gentle Words For Your Hardest Moments" | "一番辛い時に優しい言葉を" | SELF-COMPASSION / 自分を許せ カード |
| 2 | 悩み選択（Onboarding） | "What weighs on you? We'll be there." | "何が苦しい？そばにいるよ" | Struggle Selection 画面 |
| 3 | My Path | "Your pain. We get it." | "一人で抱え込まなくていい" | My Path 課題一覧画面 |
| 4 | Nudge カード（就寝系） | "Protecting tomorrow's you." | "明日のあなたを守る" | BEDTIME / スマホを置け カード |

---

## 3. 素材テーブル — 8枚の raw スクショ

| # | 画面 | EN raw | JA raw | 状態 |
|---|------|--------|--------|------|
| 1 | Nudge カード | `assets/card-screenshots/en/self_loathing_0.png` (780x1688) | `assets/card-screenshots/ja/self_loathing_0.png` (780x1688) | **あるからコピーするだけ** |
| 2 | 悩み選択 | `raw/02-struggle-selection.png` (1206x2622) | **なし → simctl で撮る** | EN あり / JA なし |
| 3 | My Path | **なし → simctl で撮る** | **なし → simctl で撮る** | EN/JA 両方なし |
| 4 | Nudge カード | `assets/card-screenshots/en/staying_up_late_0.png` (780x1688) | `assets/card-screenshots/ja/staying_up_late_0.png` (780x1688) | **あるからコピーするだけ** |

**結論: 8枚中 5枚は既存。simctl で撮るのは 3枚（Screen 2 JA、Screen 3 EN、Screen 3 JA）。**

### simctl での raw キャプチャ方法（Maestro 不使用）

```bash
# 1. シミュレータ起動
xcrun simctl boot 1D9F5D85-7C93-447F-A62E-1DA07A490E93  # iPhone16ProMax-69

# 2. アプリをビルド＆インストール
cd /Users/anicca/anicca-project/aniccaios
xcodebuild build -scheme aniccaios -configuration Debug \
  -destination "id=1D9F5D85-7C93-447F-A62E-1DA07A490E93" \
  -derivedDataPath ./build/DerivedData ONLY_ACTIVE_ARCH=YES -quiet
xcrun simctl install 1D9F5D85-7C93-447F-A62E-1DA07A490E93 \
  ./build/DerivedData/Build/Products/Debug-iphonesimulator/aniccaios.app

# 3. EN 用: アプリ起動 → 手動で画面遷移 → スクショ
xcrun simctl launch 1D9F5D85-7C93-447F-A62E-1DA07A490E93 ai.anicca.app.ios -UITESTING true
# → Simulator.app で手動操作: Welcome → Struggle選択 → Next → LiveDemo → Skip → My Path
xcrun simctl io booted screenshot /tmp/screen3-en.png  # My Path 画面

# 4. JA 用: 言語変更 → アプリ再起動 → 手動で画面遷移 → スクショ
xcrun simctl spawn booted defaults write -g AppleLanguages -array ja
xcrun simctl terminate booted ai.anicca.app.ios
xcrun simctl launch booted ai.anicca.app.ios -UITESTING true
# → Simulator.app で手動操作: 同じフロー（日本語 UI）
xcrun simctl io booted screenshot /tmp/screen2-ja.png  # 悩み選択画面
xcrun simctl io booted screenshot /tmp/screen3-ja.png  # マイパス画面

# 5. EN に戻す
xcrun simctl spawn booted defaults write -g AppleLanguages -array en
```

**出力サイズ:** 1320x2868（iPhone16ProMax-69 シミュレータ = 6.9" 相当）

---

## 4. ParthJadhav スキルの仕組み — 完成品の作り方

### スキルの範囲

```
┌─────────────────────────────────────────────┐
│ スキルがやること:                             │
│  raw スクショ → mockup.png にはめ込み        │
│  → ヘッドライン追加 → 背景追加               │
│  → 完成品 PNG 出力                           │
│                                              │
│ スキルがやらないこと:                         │
│  - アプリのスクショ撮影（自分でやる）        │
│  - ASC へのアップロード（asc CLI でやる）    │
│  - A/B テスト作成（asc CLI でやる）          │
└─────────────────────────────────────────────┘
```

### 完成品 1枚の構造（1320x2868）

```
┌──────────────────────────────────────────────┐
│               背景グラデーション                │
│            (#4FC3F7 → #0288D1)               │
│                                              │
│         ┌──────────────────────┐             │
│         │   ヘッドラインテキスト  │             │
│         │  "Gentle Words For   │             │
│         │   Your Hardest       │             │
│         │     Moments"         │             │
│         └──────────────────────┘             │
│                                              │
│       ┌──────────────────────────┐           │
│       │  mockup.png (iPhone枠)   │           │
│       │  ┌────────────────────┐  │           │
│       │  │                    │  │           │
│       │  │  raw スクショ       │  │           │
│       │  │  (カード or         │  │           │
│       │  │   アプリ画面)       │  │           │
│       │  │                    │  │           │
│       │  │  object-fit:cover  │  │           │
│       │  │  で画面エリアに     │  │           │
│       │  │  はめ込み           │  │           │
│       │  │                    │  │           │
│       │  └────────────────────┘  │           │
│       └──────────────────────────┘           │
│                                              │
└──────────────────────────────────────────────┘
```

### 各スクリーンの完成品イメージ（ASCII）

**Screen 1 — EN: "Gentle Words For Your Hardest Moments"**
```
┌──────────────────────────────────┐
│          青グラデーション背景       │
│                                  │
│    Gentle Words                  │
│    For Your Hardest              │
│    Moments                       │
│                                  │
│      ┌────────────────────┐      │
│      │ ╭────────────────╮ │      │
│      │ │                │ │      │
│      │ │     🤍          │ │      │
│      │ │ FORGIVE YOURSELF│ │      │
│      │ │                │ │      │
│      │ │ You're alive   │ │      │
│      │ │ today. That's  │ │      │
│      │ │ enough.        │ │      │
│      │ │                │ │      │
│      │ │ [Forgive Myself]│ │      │
│      │ │   👍   👎       │ │      │
│      │ ╰────────────────╯ │      │
│      └────────────────────┘      │
│                                  │
└──────────────────────────────────┘
raw = card-screenshots/en/self_loathing_0.png (780x1688)
```

**Screen 2 — EN: "What weighs on you? We'll be there."**
```
┌──────────────────────────────────┐
│          青グラデーション背景       │
│                                  │
│    What weighs on                │
│    you? We'll be                 │
│    there.                        │
│                                  │
│      ┌────────────────────┐      │
│      │ ╭────────────────╮ │      │
│      │ │ What are you   │ │      │
│      │ │ struggling with│ │      │
│      │ │ now?           │ │      │
│      │ │                │ │      │
│      │ │[Staying up late]│ │      │
│      │ │[Self-loathing] │ │      │
│      │ │[Procrastination]│ │      │
│      │ │[Anxiety]       │ │      │
│      │ │                │ │      │
│      │ │    [Next]       │ │      │
│      │ ╰────────────────╯ │      │
│      └────────────────────┘      │
│                                  │
└──────────────────────────────────┘
raw = raw/02-struggle-selection.png (1206x2622)
```

**Screen 3 — EN: "Your pain. We get it."**
```
┌──────────────────────────────────┐
│          青グラデーション背景       │
│                                  │
│    Your pain.                    │
│    We get it.                    │
│                                  │
│      ┌────────────────────┐      │
│      │ ╭────────────────╮ │      │
│      │ │ My Path     +  │ │      │
│      │ │                │ │      │
│      │ │ Current Struggles│ │     │
│      │ │ 🌟 Can't wake up│ │     │
│      │ │ ⏰ Procrastination│ │   │
│      │ │ 🌀 Rumination   │ │     │
│      │ │ 💬 Bad-mouthing │ │     │
│      │ │ 💙 Loneliness   │ │     │
│      │ │ 🔮 Obsessive    │ │     │
│      │ ╰────────────────╯ │      │
│      └────────────────────┘      │
│                                  │
└──────────────────────────────────┘
raw = simctl でキャプチャ (1320x2868)
```

**Screen 4 — EN: "Protecting tomorrow's you."**
```
┌──────────────────────────────────┐
│          青グラデーション背景       │
│                                  │
│    Protecting                    │
│    tomorrow's you.               │
│                                  │
│      ┌────────────────────┐      │
│      │ ╭────────────────╮ │      │
│      │ │                │ │      │
│      │ │     🌙          │ │      │
│      │ │ PUT THE PHONE  │ │      │
│      │ │ DOWN           │ │      │
│      │ │                │ │      │
│      │ │ Breathe, don't │ │      │
│      │ │ scroll.        │ │      │
│      │ │                │ │      │
│      │ │[Protect Tomorrow]│ │    │
│      │ │   👍   👎       │ │      │
│      │ ╰────────────────╯ │      │
│      └────────────────────┘      │
│                                  │
└──────────────────────────────────┘
raw = card-screenshots/en/staying_up_late_0.png (780x1688)
```

**JA 版 — 同じレイアウト、ヘッドラインと raw が日本語に切り替わる:**

```
Screen 1 JA: "一番辛い時に優しい言葉を"  + ja/self_loathing_0.png
Screen 2 JA: "何が苦しい？そばにいるよ"  + simctl でキャプチャ
Screen 3 JA: "一人で抱え込まなくていい"  + simctl でキャプチャ
Screen 4 JA: "明日のあなたを守る"        + ja/staying_up_late_0.png
```

---

## 5. ツールスタック

| ツール | 役割 | 備考 |
|--------|------|------|
| ParthJadhav/app-store-screenshots | raw → 完成品 PNG 変換 | Next.js + html-to-image |
| xcrun simctl | シミュレータ起動 + 言語設定 + スクショ撮影 | Screen 2 JA, Screen 3 EN/JA |
| ASC CLI 0.48.0 | 実験 CRUD + スクショアップロード + 実験開始 | `--version`（`--version-id` ではない） |
| CardScreenshotGenerator | Nudge カード PNG レンダリング（189枚/言語） | 既に生成済み。再生成不要 |
| Playwright | cron 用ヘッドレスエクスポート | `npx playwright install chromium` |

### mockup.png の座標

```typescript
const MK_W = 1022;  // mockup 幅
const MK_H = 2082;  // mockup 高さ
const SC_L = (52 / MK_W) * 100;   // スクリーン左オフセット %
const SC_T = (46 / MK_H) * 100;   // スクリーン上オフセット %
const SC_W = (918 / MK_W) * 100;  // スクリーン幅 %
const SC_H = (1990 / MK_H) * 100; // スクリーン高さ %
```

### ASC CLI コマンド（E2E テストで確認済み）

| コマンド | フラグ | 注意 |
|---------|--------|------|
| `asc localizations list` | `--version $VER_ID`（`--version-id` ではない） | E2E で判明 |
| `asc product-pages experiments list` | `--v2 --app $APP_ID` | OK |
| `asc product-pages experiments create` | `--v2 --app $APP_ID --platform IOS --name "X" --traffic-proportion 50` | 未テスト |
| `asc screenshots upload` | `--version-localization $LOC_ID --path ./export/ --device-type APP_IPHONE_67 --replace` | **Treatment loc 非対応** → `upload-treatment.py` 必須 |

---

## 6. E2E フロー（2026-04-01 実行完了・修正済み）

```
STEP 1: raw スクショ準備
  永続ストレージ: assets/app-store-screenshots/raw/{en,ja}/screen{1-4}.png
  既にあればスキップ。なければ simctl で撮影。
    ↓
STEP 2: Next.js ジェネレーター起動
  cd workspace/screenshot-generator && npm run dev -- -p 3847
  ※ create-next-app は対話プロンプトでハングする → 手動スキャフォールド必須
    ↓
STEP 3: page.tsx + /export route
  メインページ: プレビューグリッド + ロケール切替 + Export All ボタン
  /export?locale=X&slide=Y: 単一スライド 1320x2868 レンダリング
  ※ html-to-image の browser evaluate import は不可 → Playwright viewport screenshot で代替
    ↓
STEP 4: Playwright export (export.mjs)
  2言語 × 4画面 = 8 PNG → workspace/export/{en,ja}/screen{1-4}.png
  ※ toPng() ダブルコール不要（Playwright screenshot で直接取得）
  ※ 3000ms wait で画像ロード待ち
    ↓
STEP 5: visual-qa → NG なら STEP 3 に戻る（最大3回）
    ↓
STEP 6: ASC 実験作成 + Treatment + Localizations
  asc product-pages experiments create --v2 --app $APP_ID --platform IOS --name "..." --traffic-proportion 50
  asc product-pages experiments treatments create --experiment-id $EXP_ID --name "..." --v2
  ※ treatment localization は asc CLI に create コマンドなし → Apple API POST 直接
    ↓
STEP 7: スクショアップロード（upload-treatment.py）
  ⚠️ asc screenshots upload は treatment localization に非対応
  → upload-treatment.py で Apple API 直接呼び出し:
    1. asc auth token --confirm で JWT 取得
    2. POST /v1/appScreenshotSets （既存なら GET で ID 取得）
    3. POST /v1/appScreenshots → reserve → upload part → commit
    4. 既存の古いスクショは事前に DELETE
    ↓
STEP 8: レビュー提出（⚠️ --started true は直接使えない）
  ⚠️ asc experiments update --started true は "must be reviewed" エラー
  → Apple reviewSubmissions API の3ステップ:
    1. POST /v1/reviewSubmissions (platform: IOS, app relationship)
    2. POST /v1/reviewSubmissionItems (appStoreVersionExperimentV2 relationship)
    3. PATCH /v1/reviewSubmissions/{id} (submitted: true)
  → state: WAITING_FOR_REVIEW → Apple 審査通過後に自動開始
    ↓
STEP 9: experiments.json 更新 + Slack レポート
    ↓
DONE — Apple 審査通過後、実験自動開始（通常24h以内）
```

### ⚠️ E2E で判明した重要な落とし穴

| # | 問題 | 原因 | 解決策 |
|---|------|------|--------|
| 1 | `create-next-app` がハング | 対話プロンプト（React Compiler?） | 手動 package.json + npm install |
| 2 | html-to-image の browser import 失敗 | page.evaluate 内で bundled module import 不可 | /export route + Playwright viewport screenshot |
| 3 | `asc screenshots upload --treatment-localization` 不可 | フラグが存在しない。version-localization のみ | upload-treatment.py（Apple API 直接） |
| 4 | Treatment localization 作成 CLI なし | asc CLI 0.48.0 未対応 | Apple API POST 直接 |
| 5 | `--started true` でレビュー提出不可 | PPO は reviewRequired: true。提出は reviewSubmissions API 経由 | 3ステップ reviewSubmissions フロー |
| 6 | 古いスクショがセットに残る | 前回の upload 残骸 | upload 前に既存セット内スクショを全 DELETE |
| 7 | `asc auth token` に `--confirm` 必要 | CLI が確認プロンプトを要求 | 全呼び出しに `--confirm` 追加 |
| 8 | macOS TCC Desktop アクセス拒否 | tmux プロセスに Full Disk Access なし | プロジェクトディレクトリに保存。恒久対応: tmux を FDA に追加 |

---

## 7. スキルフォルダ構造

```
~/.openclaw/skills/screenshot-ab/
├── SKILL.md
├── references/
│   ├── headline-gen.md
│   ├── visual-qa.md
│   ├── asc-commands.md
│   └── anicca-app-context.md
├── scripts/
│   ├── setup-workspace.sh
│   ├── export-screenshots.sh
│   ├── upload-treatment-screenshots.py
│   ├── update-experiments-json.py
│   └── slack-upload.sh
├── assets/
│   └── experiments-template.json
└── workspace/
    ├── screenshot-generator/
    │   ├── public/
    │   │   ├── mockup.png
    │   │   └── screenshots/{en,ja}/screen1~4.png
    │   └── src/app/page.tsx
    ├── export/{en,ja}/screen1~4.png
    └── experiments.json
```

### raw 素材の場所（プロジェクト内）

```
/Users/anicca/anicca-project/
├── assets/card-screenshots/
│   ├── en/   (189枚: Screen 1 = self_loathing_*, Screen 4 = staying_up_late_*)
│   └── ja/   (189枚: 同構成)
├── .cursor/plans/ios/1.6.3/screenshot-ab-pipeline/raw/
│   └── 02-struggle-selection.png  (Screen 2 EN)
└── .claude/skills/app-store-screenshots/
    └── mockup.png  (iPhone フレーム)
```

---

## 8. 利用可能なシミュレータ

| デバイス | UDID | 画面サイズ | 用途 |
|---------|------|----------|------|
| iPhone16ProMax-69 | 1D9F5D85-7C93-447F-A62E-1DA07A490E93 | 6.9" (1320x2868) | メイン撮影用 |

---

## 9. 2モード対応

| モード | ユーザー入力 | 変更対象 | 所要時間 |
|--------|------------|---------|---------|
| **デザイン変更** | 新 raw スクショ + 新ヘッドライン | gradient, layout, mockup配置, テキスト全て | 約15分 |
| **テキストのみ** | 新ヘッドライン（4画面×2言語=8個） | COPY 辞書のみ → re-export → re-upload | 約5分 |

### デザイン変更モード
1. ユーザーが新 raw スクショを `assets/app-store-screenshots/raw/{en,ja}/` に配置
2. `page.tsx` の BG_GRADIENT, レイアウト, フォントサイズ等を変更
3. COPY 辞書を更新
4. Playwright export → upload-treatment.py → reviewSubmissions 提出

### テキストのみモード
1. `page.tsx` の COPY 辞書だけ変更
2. Playwright export → upload-treatment.py → reviewSubmissions 提出

---

## 10. E2E 実行ログ（2026-04-01）

| 項目 | 値 |
|------|-----|
| Experiment ID | `3a28dd82-ef26-4ae0-96b9-a5dfad5eb7f6` |
| Experiment Name | `screenshot-ab-v20260401` |
| Treatment ID | `2c2bd3e3-e8ec-46ca-88a0-11f3b52d2837` |
| EN Localization ID | `ebffc336-7ce7-4f85-9a54-39e50ae5e277` |
| JA Localization ID | `028580f5-d3da-49d8-9f35-730e88602032` |
| EN Screenshot Set | `14f81eca-b854-4fc9-8e2c-9eb01dcbc25b` |
| JA Screenshot Set | `0f4ddad9-b4af-4450-9d47-2766c36db70c` |
| Review Submission ID | `9937db0d-f1db-4a7a-8782-3b802e4cec85` |
| Traffic | 50% control / 50% treatment |
| State | `WAITING_FOR_REVIEW`（2026-04-01 02:57 JST 提出） |

### 生成ファイル

| ファイル | パス |
|---------|------|
| Raw EN (4枚) | `assets/app-store-screenshots/raw/en/screen{1-4}-*.png` |
| Raw JA (4枚) | `assets/app-store-screenshots/raw/ja/screen{1-4}-*.png` |
| Export EN (4枚) | `~/.openclaw/skills/screenshot-ab/workspace/export/en/screen{1-4}.png` |
| Export JA (4枚) | `~/.openclaw/skills/screenshot-ab/workspace/export/ja/screen{1-4}.png` |
| upload script | `~/.openclaw/skills/screenshot-ab/workspace/upload-treatment.py` |
| Next.js generator | `~/.openclaw/skills/screenshot-ab/workspace/screenshot-generator/` |

---

## 11. スキル修正パッチ（TODO）

### Patch 1: SKILL.md — ASC アップロードセクション書き換え

**現状（間違い）:**
```
asc screenshots upload --version-localization $LOC_ID --path ./export/ --device-type APP_IPHONE_67
```

**修正後:**
```
# asc CLI は treatment localization に非対応。Apple API 直接呼び出し必須。
python3 scripts/upload-treatment.py \
  --export-dir workspace/export \
  --en-loc $EN_LOC_ID \
  --ja-loc $JA_LOC_ID
```

### Patch 2: SKILL.md — レビュー提出セクション追加

**現状（間違い）:**
```
asc product-pages experiments update --experiment-id $EXP_ID --started true --v2
```

**修正後:**
```bash
TOKEN=$(asc auth token --confirm)

# Step 1: レビュー提出作成
REVIEW_ID=$(curl -s -X POST "https://api.appstoreconnect.apple.com/v1/reviewSubmissions" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"data":{"type":"reviewSubmissions","attributes":{"platform":"IOS"},"relationships":{"app":{"data":{"type":"apps","id":"'$APP_ID'"}}}}}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['id'])")

# Step 2: 実験をレビューアイテムとして追加
curl -s -X POST "https://api.appstoreconnect.apple.com/v1/reviewSubmissionItems" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"data":{"type":"reviewSubmissionItems","relationships":{"reviewSubmission":{"data":{"type":"reviewSubmissions","id":"'$REVIEW_ID'"}},"appStoreVersionExperimentV2":{"data":{"type":"appStoreVersionExperiments","id":"'$EXP_ID'"}}}}}'

# Step 3: レビューに提出
curl -s -X PATCH "https://api.appstoreconnect.apple.com/v1/reviewSubmissions/$REVIEW_ID" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"data":{"type":"reviewSubmissions","id":"'$REVIEW_ID'","attributes":{"submitted":true}}}'
```

### Patch 3: upload-treatment.py — `--confirm` フラグ追加

```diff
- result = subprocess.run(["asc", "auth", "token"], capture_output=True, text=True)
+ result = subprocess.run(["asc", "auth", "token", "--confirm"], capture_output=True, text=True)
```

### Patch 4: upload-treatment.py — 古いスクショ削除ステップ追加

upload 前に既存セット内のスクショを全削除:
```python
# Get existing screenshots in set
resp = requests.get(f"{BASE}/v1/appScreenshotSets/{set_id}/appScreenshots", headers=headers)
for ss in resp.json().get("data", []):
    requests.delete(f"{BASE}/v1/appScreenshots/{ss['id']}", headers=headers)
```

### Patch 5: SKILL.md — 2モードセクション追加

SKILL.md に「デザイン変更」「テキストのみ」の2モード分岐を記載。

### Patch 6: experiments.json 初期化

```json
{
  "app_id": "6755129214",
  "current_experiment": {
    "id": "3a28dd82-ef26-4ae0-96b9-a5dfad5eb7f6",
    "name": "screenshot-ab-v20260401",
    "state": "WAITING_FOR_REVIEW",
    "treatment_id": "2c2bd3e3-e8ec-46ca-88a0-11f3b52d2837",
    "created_at": "2026-04-01T02:57:00Z"
  },
  "history": []
}
```

---

最終更新: 2026-04-01（E2E 完了、全落とし穴記録、修正パッチ明記）
