---
name: screenshot-ab
description: "App Store スクリーンショット A/B テスト自動クローズドループ。前回 PPO 結果チェック → ヘッドライン生成 → ParthJadhav/app-store-screenshots で PNG 生成 → visual-qa → Slack 承認 → ASC CLI 0.48.0 でアップロード + 実験開始。Anicca iOS (ai.anicca.app.ios) 専用。EN + JA 両ロケール対応。Use when: screenshot A/B, スクショA/B, PPO experiment, screenshot iteration, App Store screenshot test, スクリーンショットテスト, screenshot-ab"
---

# screenshot-ab

App Store スクリーンショット A/B テストを自動で回すクローズドループスキル。
ParthJadhav/app-store-screenshots で広告スタイル PNG を生成し、ASC CLI 0.48.0 で PPO 実験を作成・開始する。

**対象アプリ:** Daily Self Care - Anicca (`ai.anicca.app.ios`)
**ロケール:** `en-US` + `ja`（両方必須）
**画面数:** 4画面 × 2言語 = 8スクリーン

## Prerequisites

| ツール | 確認コマンド |
|--------|------------|
| ASC CLI 0.48.0+ | `asc --version` |
| Node.js 18+ | `node --version` |
| ParthJadhav skill | `ls ~/.agents/skills/app-store-screenshots/` or `ls .agents/skills/app-store-screenshots/` |
| Playwright | `npx playwright --version`（なければ `npx playwright install chromium`） |

## ワークスペース

```
~/.openclaw/skills/screenshot-ab/workspace/
├── screenshot-generator/     ← ParthJadhav スキャフォールド先
├── export/en/ + ja/          ← 最終 PNG
└── experiments.json          ← 状態管理
```

初回のみ: `bash scripts/setup-workspace.sh`

---

## PHASE 0: アプリ情報取得

**毎回実行。ハードコード禁止。**

```bash
APP_ID=$(asc apps list --output json | python3 -c "
import json,sys
for a in json.load(sys.stdin)['data']:
    if a['attributes']['bundleId']=='ai.anicca.app.ios':
        print(a['id']); break
")
echo "APP_ID=$APP_ID"

VERSION_ID=$(asc versions list --app $APP_ID --output json | python3 -c "
import json,sys
versions = json.load(sys.stdin)['data']
ready = [v for v in versions if v['attributes']['appStoreState']=='READY_FOR_SALE']
print(ready[0]['id'])
")
echo "VERSION_ID=$VERSION_ID"
```

ロケール確認:
```bash
asc localizations list --version-id $VERSION_ID --output json | python3 -c "
import json,sys
for loc in json.load(sys.stdin)['data']:
    print(f'{loc[\"id\"]}  {loc[\"attributes\"][\"locale\"]}')"
```

→ `references/asc-commands.md` に全コマンド記載。

---

## PHASE 1: 前回実験結果チェック

```bash
cat ~/.openclaw/skills/screenshot-ab/workspace/experiments.json
```

`current.experiment_id` を確認。

```bash
asc product-pages experiments list --v2 --app $APP_ID --output json --pretty
```

実験が存在する場合、Treatment の CVR を確認:
```bash
asc product-pages experiments treatments list --experiment-id $EXP_ID --output json --pretty
```

**判定テーブル:**

| 条件 | アクション |
|------|-----------|
| `current.experiment_id` なし | → PHASE 3（初回 — 新実験開始） |
| 経過 < 7日 | → EXIT（データ不足。来週再チェック） |
| Treatment CVR > Control CVR × 1.2 かつ 7日+ | → WINNER → PHASE 2 |
| Treatment CVR <= Control CVR かつ 14日+ | → NULL（効果なし） → PHASE 2 |
| 90日経過 | → 強制終了 → PHASE 2 |

**WINNER の場合:** 実験を停止してから PHASE 2 へ。
```bash
asc product-pages experiments update --experiment-id $EXP_ID --started false --v2
```

---

## PHASE 2: experiments.json 更新

→ `scripts/update-experiments-json.py` を使用。

```bash
python3 scripts/update-experiments-json.py archive \
  --result WINNER \
  --control-cvr 2.1 \
  --treatment-cvr 3.2 \
  --days 12
```

勝ちパターン・負けパターンを追記:
```bash
python3 scripts/update-experiments-json.py add-pattern \
  --type winning \
  --pattern "感情的2人称 + 数字"
```

→ PHASE 3 へ。

---

## PHASE 3: ヘッドライン生成

→ `references/headline-gen.md` を読んで実行する。
→ `references/anicca-app-context.md` を読んでアプリ情報を把握する。

**入力:**
- `experiments.json` の `winning_patterns` / `losing_patterns`
- `anicca-app-context.md` のペルソナ + 画面説明

**出力:** 4画面 × 2言語 = 8ヘッドライン

```
Screen 1（Hero）: コアバリュー。ストップ・ザ・スクロール。最強の1行
Screen 2（差別化）: 競合との違い。「XXXではない」パターン有効
Screen 3（人気機能）: ユーザーが最も愛する機能
Screen 4（社会的証明）: 結果 / 数字 / レビュー
```

**ルール:**
- EN と JA は**別々のネイティブコピー**。翻訳禁止
- 生成→採点ループ: 10案 → 自己採点 → 8/10+ 採用 → 不足なら再生成（max 3回）
- 1秒ルール: App Store サムネイルサイズで読めること

---

## PHASE 4: スクショ生成

### Step 4-1: raw キャプチャ確認

```bash
SCREENSHOTS_DIR="$HOME/.openclaw/skills/screenshot-ab/workspace/screenshot-generator/public/screenshots"
ls "$SCREENSHOTS_DIR/en/" 2>/dev/null && ls "$SCREENSHOTS_DIR/ja/" 2>/dev/null
```

raw キャプチャがない場合:
- **推奨:** シミュレータで 6.1" iPhone を起動 → 4画面を手動キャプチャ → `screenshots/en/` + `screenshots/ja/` に配置
- **代替:** `asc screenshots capture --bundle-id ai.anicca.app.ios --name screen1`（実験的機能）

**4画面:**

| # | 画面 | キャプチャ方法 |
|---|------|------------|
| 1 | Today タブ（メイン） | アプリ起動直後 |
| 2 | Nudge 通知 or Insight | タブ切替 |
| 3 | 設定 or プロフィール | タブ切替 |
| 4 | Onboarding（Paywall 前） | 初回起動フロー |

### Step 4-2: ParthJadhav で page.tsx 生成/更新

ParthJadhav/app-store-screenshots スキルを呼ぶ:

```
Build App Store screenshots for Anicca (Daily Self Care app).
- 4 slides, EN + JA locales
- Style: calm, premium, warm neutral with purple accent (#6B4CE6)
- Headlines: [PHASE 3 で生成したヘッドライン]
- Raw screenshots are in public/screenshots/en/ and public/screenshots/ja/
- Export to workspace/export/
```

スキャフォールド先: `~/.openclaw/skills/screenshot-ab/workspace/screenshot-generator/`

ParthJadhav が生成するもの:
- `src/app/page.tsx` — 全スライド + ロケール切替 + テーマプリセット
- `src/app/layout.tsx` — フォント設定
- `public/mockup.png` — iPhone フレーム（スキル同梱）
- `package.json` — Next.js + html-to-image 依存

### Step 4-3: エクスポート

```bash
bash scripts/export-screenshots.sh
```

内部処理:
1. `cd workspace/screenshot-generator && npm install && npm run dev`
2. Playwright でヘッドレスアクセス → 各スライド × 各ロケールの PNG エクスポート
3. 出力: `workspace/export/en/screen1~4.png` + `workspace/export/ja/screen1~4.png`
4. サイズ: 1284x2778（IPHONE_65 — ASC 必須サイズ）

---

## PHASE 5: visual-qa 採点

→ `references/visual-qa.md` を読んで採点プロンプトを使う。

`workspace/export/` の PNG 8枚を vision model で採点する。

| カテゴリ | 配点 | チェック |
|---------|------|--------|
| Clarity | 10 | ヘッドラインが1秒で読めるか |
| Hierarchy | 10 | テキスト→デバイス→背景の視覚階層 |
| Consistency | 10 | 4枚のトーン統一 |
| Conversion | 10 | 「ダウンロード」を促す訴求力 |
| Technical | 10 | 解像度 / 切り抜き / アライメント |

| 結果 | アクション |
|------|-----------|
| 40/50+ | → PHASE 6 へ |
| 39/50 以下 | → PHASE 3 に戻る（max 3回） |
| 3回連続 FAIL | → Slack 警告 → EXIT |

---

## PHASE 6: Slack 承認

### Step 6-1: PNG アップロード

`workspace/export/` の PNG 8枚を Slack `#metrics` にアップロードする。

Slack Files v2 API（`SLACK_BOT_TOKEN` 使用）:
```bash
# 1. files.getUploadURLExternal
# 2. PUT upload_url にバイナリ送信
# 3. files.completeUploadExternal
```

### Step 6-2: 承認ボタン

```
📸 App Store スクリーンショット確認
EN: 4枚 / JA: 4枚
visual-qa: XX/50
ヘッドライン: [Screen 1 の EN ヘッドライン]
ASCアップロードに進みますか？
✅ Approve / ❌ Deny
```

| 返答 | アクション |
|------|-----------|
| ✅ Approved | → PHASE 7 へ |
| ❌ Denied | → PHASE 3 に戻る |

---

## PHASE 7: ASC アップロード + 実験作成 + 開始

→ `references/asc-commands.md` を読んで実行する。

### Step 7-1: 実験作成

```bash
EXP_ID=$(asc product-pages experiments create \
  --v2 --app $APP_ID --platform IOS \
  --name "screenshot-ab-v$(date +%Y%m%d)" \
  --traffic-proportion 50 \
  --output json | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['id'])")
echo "EXP_ID=$EXP_ID"
```

### Step 7-2: Treatment 作成

```bash
TREAT_ID=$(asc product-pages experiments treatments create \
  --experiment-id $EXP_ID \
  --name "New Screenshots $(date +%Y%m%d)" \
  --output json | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['id'])")
echo "TREAT_ID=$TREAT_ID"
```

### Step 7-3: Treatment localization 作成（EN + JA）

```bash
EN_LOC=$(asc product-pages experiments treatments localizations create \
  --treatment-id $TREAT_ID --locale en-US \
  --output json | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['id'])")

JA_LOC=$(asc product-pages experiments treatments localizations create \
  --treatment-id $TREAT_ID --locale ja \
  --output json | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['id'])")

echo "EN_LOC=$EN_LOC  JA_LOC=$JA_LOC"
```

### Step 7-4: スクショアップロード

**方法 A: asc screenshots upload（推奨 — 要テスト）**
```bash
asc screenshots upload \
  --version-localization $EN_LOC \
  --path "$HOME/.openclaw/skills/screenshot-ab/workspace/export/en/" \
  --device-type IPHONE_65 \
  --replace

asc screenshots upload \
  --version-localization $JA_LOC \
  --path "$HOME/.openclaw/skills/screenshot-ab/workspace/export/ja/" \
  --device-type IPHONE_65 \
  --replace
```

**方法 B: Apple API 直接（フォールバック）**
```bash
python3 scripts/upload-treatment-screenshots.py \
  --en-loc $EN_LOC \
  --ja-loc $JA_LOC \
  --export-dir "$HOME/.openclaw/skills/screenshot-ab/workspace/export"
```

### Step 7-5: 実験開始

```bash
asc product-pages experiments update \
  --experiment-id $EXP_ID \
  --started true \
  --v2
```

**`--started true` が `reviewRequired` エラーを返す場合:**
→ Slack に「ASC Web UI で手動開始が必要」と通知。URL を含める:
`https://appstoreconnect.apple.com/apps/$APP_ID/productpageoptimization`

### Step 7-6: experiments.json 更新

```bash
python3 scripts/update-experiments-json.py set-current \
  --experiment-id $EXP_ID \
  --name "screenshot-ab-v$(date +%Y%m%d)" \
  --treatment-id $TREAT_ID \
  --en-loc $EN_LOC \
  --ja-loc $JA_LOC \
  --headlines-en "H1|H2|H3|H4" \
  --headlines-ja "H1|H2|H3|H4"
```

### Step 7-7: Slack レポート

```bash
curl -s -X POST "$SLACK_WEBHOOK_AGENTS" \
  -H 'Content-type: application/json' \
  -d "{
    \"text\": \"📸 screenshot-ab-v$(date +%Y%m%d) 開始\nTraffic: 50/50\nEN: 4枚 / JA: 4枚\n実験ID: $EXP_ID\nTreatment: $TREAT_ID\nヘッドライン EN: [Screen1 headline]\nヘッドライン JA: [Screen1 headline]\"
  }"
```

---

## エラーハンドリング

| エラー | 対処 |
|--------|------|
| `asc` コマンド認証エラー | `security unlock-keychain` → ASC CLI トークンリフレッシュ |
| `asc screenshots upload` が Treatment に対応しない | `scripts/upload-treatment-screenshots.py` に切替 |
| `--started true` が reviewRequired | Slack に ASC Web UI URL を通知 |
| ParthJadhav スキャフォールド失敗 | `rm -rf workspace/screenshot-generator && retry` |
| Playwright タイムアウト | `npx playwright install chromium` → retry |
| visual-qa 3回連続 FAIL | Slack 警告して EXIT。ヘッドラインの方向性を根本見直し |
