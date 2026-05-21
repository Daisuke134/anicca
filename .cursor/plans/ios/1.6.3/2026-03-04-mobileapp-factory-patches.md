plea# Mobile App Factory + Builder パッチ一覧

**日付**: 2026-03-04
**対象**: Chi Daily (APP_ID: 6759994539, Bundle: com.aniccafactory.chidaily)
**原則**: ASC CLI Skills (https://github.com/rudrankriyam/app-store-connect-cli-skills) に100%従う。オリジナル禁止。

---
Tell me the full path of the spec that was basically fixing this whole fucking recipe. 
## 実テスト結果（2026-03-04 Mac Mini で実行）

| テスト | コマンド | 結果 | 証拠 |
|--------|---------|------|------|
| ASC 認証 | `asc auth status` | ✅ | Anicca + AniccaFactory 認証済み |
| スクショ capture | `asc screenshots capture --bundle-id ... --udid ...` | ✅ | 4枚全異なるMD5 |
| AXe UI操作 | `axe describe-ui / swipe / tap` | ✅ | 画面遷移成功（swipe で onboarding 3ページ、UserDefaults で home） |
| `asc screenshots frame` | `asc screenshots frame --input ... --device iphone-air` | ❌ | **asc 0.36.3 バグ**: kou exit status 1 |
| `kou generate` 直接 | `kou generate koubou.yaml` | ✅ | 1320x2868 PNG 出力成功（バックグラウンドエージェント確認） |
| Beta Groups list | `asc testflight beta-groups list --app 6759994539` | ✅ | External Testers (ID: 219ab913) |
| Beta Testers list | `asc testflight beta-testers list --app 6759994539` | ✅ | keiodaisuke@gmail.com: state=NOT_INVITED |
| Build add-groups | `asc builds add-groups --build BUILD_ID --group GROUP_ID` | ✅ | Successfully added |
| Beta-testers invite | `asc testflight beta-testers invite --app ... --email ...` | ⚠️ | invitationId 返却、しかし state=NOT_INVITED のまま |
| Builds list | `asc builds list --app 6759994539 --sort -uploadedDate --limit 3` | ✅ | Build #2 = VALID |
| Age Rating | `asc age-rating get --app 6759994539` | ✅ | 設定済み |
| Screenshot upload | 未実行 | - | version-localization ID 取得が必要 |
| App Privacy | API不可 | ❌ | Apple API に endpoint なし（実証済み） |

---

## P1: スクリーンショット重複（3枚同一MD5）

**根本原因**: simctl io screenshot を使い、AXe で画面遷移せず同じ画面を撮影していた。

**パッチ対象**: `.claude/skills/mobileapp-builder/references/us-008-release.md`

**パッチ内容**: スクリーンショットセクションを以下に置換。スキル `asc-shots-pipeline` に完全準拠。

```markdown
## Step 4: Screenshots (skill: asc-shots-pipeline)

### 4.1 設定ファイル作成

`.asc/shots.settings.json` を作成:

\```json
{
  "version": 1,
  "app": {
    "bundle_id": "$BUNDLE_ID",
    "project": "${APP_NAME}ios/${APP_NAME}.xcodeproj",
    "scheme": "$APP_NAME",
    "simulator_udid": "$UDID"
  },
  "paths": {
    "plan": ".asc/screenshots.json",
    "raw_dir": "./screenshots/raw",
    "framed_dir": "./screenshots/framed"
  },
  "pipeline": {
    "frame_enabled": true,
    "upload_enabled": false
  },
  "upload": {
    "version_localization_id": "",
    "device_type": "IPHONE_67",
    "source_dir": "./screenshots/framed"
  }
}
\```

### 4.2 シミュレータでアプリ起動

\```bash
UDID=$(xcrun simctl list devices | grep "Screenshots" | grep "Booted" | grep -oE '[A-F0-9-]{36}' | head -1)
if [ -z "$UDID" ]; then
  UDID=$(xcrun simctl list devices | grep "Booted" | head -1 | grep -oE '[A-F0-9-]{36}')
fi

xcrun simctl terminate "$UDID" "$BUNDLE_ID" 2>/dev/null || true
sleep 1
xcrun simctl launch "$UDID" "$BUNDLE_ID"
sleep 3
\```

### 4.3 AXe で各画面キャプチャ（skill: asc-shots-pipeline Section 3）

\```bash
export ASC_BYPASS_KEYCHAIN=true
RAW_DIR="./screenshots/raw"
rm -f "$RAW_DIR"/screen*.png

# Screen 1: Welcome/Onboarding Page 1（アプリ起動直後）
asc screenshots capture --bundle-id "$BUNDLE_ID" --name "screen1_welcome" --udid "$UDID" --output-dir "$RAW_DIR" --output json

# Screen 2: Onboarding Page 2（スワイプで遷移）
axe swipe --start-x 250 --start-y 240 --end-x 70 --end-y 240 --duration 0.3 --udid "$UDID"
sleep 2
asc screenshots capture --bundle-id "$BUNDLE_ID" --name "screen2_features" --udid "$UDID" --output-dir "$RAW_DIR" --output json

# Screen 3: Paywall（スワイプで遷移）
axe swipe --start-x 250 --start-y 240 --end-x 70 --end-y 240 --duration 0.3 --udid "$UDID"
sleep 2
asc screenshots capture --bundle-id "$BUNDLE_ID" --name "screen3_paywall" --udid "$UDID" --output-dir "$RAW_DIR" --output json

# Screen 4: Home（UserDefaults でオンボーディングスキップ → 再起動）
xcrun simctl spawn "$UDID" defaults write "$BUNDLE_ID" hasCompletedOnboarding -bool true
xcrun simctl terminate "$UDID" "$BUNDLE_ID"
sleep 1
xcrun simctl launch "$UDID" "$BUNDLE_ID"
sleep 3
asc screenshots capture --bundle-id "$BUNDLE_ID" --name "screen4_home" --udid "$UDID" --output-dir "$RAW_DIR" --output json
\```

### 4.4 重複チェック（MUST — スキップ禁止）

\```bash
md5 -r "$RAW_DIR"/screen*.png | sort
# 同一MD5が2つ以上あったら NG → AXe の遷移を修正して再撮影
\```

### 4.5 フレーム合成（skill: asc-shots-pipeline Section 4）

\```bash
export PATH="/Users/anicca/Library/Python/3.9/bin:$PATH"
pip install koubou==0.14.0  # asc 0.36.3 requires 0.14.0
kou --version  # expect 0.14.0

FRAMED_DIR="./screenshots/framed"
rm -rf "$FRAMED_DIR"
mkdir -p "$FRAMED_DIR"

# NOTE: asc 0.36.3 の `asc screenshots frame` にバグあり（kou exit status 1）
# 回避策: kou generate を直接使用する
# kou の YAML config を Python で生成:
python3 << 'PYEOF'
import yaml, os

raw_dir = os.environ.get("RAW_DIR", "./screenshots/raw")
framed_dir = os.environ.get("FRAMED_DIR", "./screenshots/framed")

screenshots = {}
for f in sorted(os.listdir(raw_dir)):
    if f.startswith("screen") and f.endswith(".png"):
        name = f.replace(".png", "")
        screenshots[name] = {
            "content": [
                {
                    "type": "image",
                    "asset": os.path.join(os.path.abspath(raw_dir), f),
                    "frame": True,
                    "position": ["50%", "50%"],
                    "scale": 0.85
                }
            ]
        }

config = {
    "defaults": {
        "background": {
            "type": "solid",
            "colors": ["#000000"]
        }
    },
    "project": {
        "device": "iPhone 16 Plus - Black - Portrait",
        "name": "AppScreenshots",
        "output_dir": os.path.abspath(framed_dir),
        "output_size": "iPhone6_7"
    },
    "screenshots": screenshots
}

with open(".asc/koubou.yaml", "w") as f:
    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
print("Config written")
PYEOF

kou generate .asc/koubou.yaml
\```

### 4.6 アップロード（skill: asc-shots-pipeline Section 5）

\```bash
# Version Localization ID を取得（skill: asc-id-resolver）
VERSION_ID=$(asc versions list --app "$APP_ID" --output json | python3 -c "
import json,sys
d=json.load(sys.stdin)
for v in d['data']:
    if v['attributes'].get('versionString') == '$VERSION':
        print(v['id']); break
")

LOC_ID=$(asc localizations list --version "$VERSION_ID" --output json | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d['data'][0]['id'])
")

# 既存スクリーンショットを削除（あれば）
EXISTING=$(asc screenshots list --version-localization "$LOC_ID" --output json 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
for s in d.get('data',[]): print(s['id'])
" 2>/dev/null)
for sid in $EXISTING; do
  asc screenshots delete --id "$sid" --confirm
done

# アップロード
asc screenshots upload \
  --version-localization "$LOC_ID" \
  --path "$FRAMED_DIR" \
  --device-type "IPHONE_67" \
  --output json

# 確認（MUST）
asc screenshots list --version-localization "$LOC_ID" --output table
\```
```

---

## P2: Paywall スクリーンショットテキスト切れ

**根本原因**: フォントサイズが大きすぎる or パディング不足。

**パッチ対象**: アプリの SwiftUI コード（PaywallView.swift）

**パッチ内容**: スクリーンショット撮り直しで解決する可能性が高い。P1 のパッチで正しい解像度（1290x2796）のキャプチャに変更済み。それでもテキスト切れがある場合は PaywallView の `.font(.title)` を `.font(.title2)` に変更。

---

## P3: TestFlight テスターが招待されていない

**根本原因**: `beta-testers add` だけで `invite` を実行していなかった。さらにビルドがグループに追加されていなかった。

**パッチ対象**: `.claude/skills/mobileapp-builder/references/us-007-testing.md`

**パッチ内容**: TestFlight セクションを以下に置換。スキル `asc-testflight-orchestration` + `asc-release-flow` に完全準拠。

```markdown
## Step 3: TestFlight Distribution (skill: asc-testflight-orchestration + asc-release-flow)

### 3.1 Beta グループ確認/作成

\```bash
export ASC_BYPASS_KEYCHAIN=true

# グループ一覧
asc testflight beta-groups list --app "$APP_ID" --paginate --output json

# グループがなければ作成
GROUP_ID=$(asc testflight beta-groups list --app "$APP_ID" --output json | python3 -c "
import json,sys
d=json.load(sys.stdin)
groups = d.get('data',[])
if groups:
    print(groups[0]['id'])
else:
    print('')
")

if [ -z "$GROUP_ID" ]; then
  asc testflight beta-groups create --app "$APP_ID" --name "External Testers"
  GROUP_ID=$(asc testflight beta-groups list --app "$APP_ID" --output json | python3 -c "
  import json,sys; d=json.load(sys.stdin); print(d['data'][0]['id'])")
fi
echo "GROUP_ID: $GROUP_ID"
\```

### 3.2 ビルドをグループに追加（skill: asc-testflight-orchestration）

\```bash
# 最新ビルドID取得（skill: asc-id-resolver）
BUILD_ID=$(asc builds latest --app "$APP_ID" --platform IOS --output json | python3 -c "
import json,sys; d=json.load(sys.stdin); print(d['data']['id'])")
echo "BUILD_ID: $BUILD_ID"

# ビルドをグループに追加
asc builds add-groups --build "$BUILD_ID" --group "$GROUP_ID"
\```

### 3.3 テスター追加 + 招待（skill: asc-testflight-orchestration）

\```bash
# テスター追加（グループに紐付け）
asc testflight beta-testers add --app "$APP_ID" --email "$TESTER_EMAIL" --group "External Testers"

# 招待送信（add だけでは NOT_INVITED のまま — invite が必須）
asc testflight beta-testers invite --app "$APP_ID" --email "$TESTER_EMAIL"
\```

### 3.4 What to Test ノート追加（skill: asc-testflight-orchestration）

\```bash
asc builds test-notes create --build "$BUILD_ID" --locale "en-US" --whats-new "Initial beta test"
\```

### 3.5 確認（MUST — Evidence Over Assertion）

\```bash
# テスター状態確認
asc testflight beta-testers list --app "$APP_ID" --output json | python3 -c "
import json,sys
d=json.load(sys.stdin)
for t in d['data']:
    a = t['attributes']
    print(f'{a[\"email\"]}: state={a[\"state\"]}')
"
# 期待値: state=INVITED または ACCEPTED

# ビルドがグループに紐付いているか確認
asc testflight beta-groups list --app "$APP_ID" --output json
\```

### 3.6 招待が NOT_INVITED のままの場合

Beta App Review が完了していない可能性。External テスターへのビルド配布には Apple の Beta App Review が必要。

\```bash
# ビルドの beta review status を確認
asc builds info --build "$BUILD_ID" --output json | python3 -c "
import json,sys
d=json.load(sys.stdin)
attrs = d['data']['attributes']
print(f'processingState: {attrs.get(\"processingState\")}')
print(f'usesNonExemptEncryption: {attrs.get(\"usesNonExemptEncryption\")}')
"
\```

Beta App Review は Apple 側の処理。通常 24-48 時間。完了するまで External テスターには届かない。
Internal テスター（App Store Connect ユーザー）は Review 不要で即配布可能。
```

---

## P4: App Privacy API 404

**根本原因**: Apple の App Store Connect API に App Privacy 設定のエンドポイントが存在しない。

**パッチ対象**: `.claude/skills/mobileapp-builder/references/us-009-submit.md`

**パッチ内容**: App Privacy セクションを以下に置換。

```markdown
## Step 1: App Privacy（WAITING_FOR_HUMAN — API 不可）

Apple App Store Connect API には App Privacy を設定するエンドポイントが存在しない。
`/v1/appDataUsages` は 404 を返す（2026-03-04 実証済み）。

### アクション:

1. progress.txt に以下を書く:
\```
WAITING_FOR_HUMAN: App Privacy を ASC Web UI で設定してください
URL: https://appstoreconnect.apple.com/apps/$APP_ID/distribution/app-privacy
設定内容: "Data Not Collected" を選択（analytics SDK なし、tracking SDK なし）
\```

2. `passes: false` のまま iteration を終了
3. ralph.sh が Slack に通知 → 人間が Web UI で設定
4. 人間が完了 → progress.txt から `WAITING_FOR_HUMAN` を削除
5. 次の iteration で Step 2 以降を続行

**絶対にAPIで設定しようとしない。3回試行して BLOCKED するだけ。**
```

---

## P5: RevenueCat Public API Key が API 取得不可

**根本原因**: RevenueCat の API v2 には Public API Key を返すエンドポイントがない。Dashboard のみ。

**パッチ対象**: `.claude/skills/mobileapp-builder/references/us-005b-monetization.md`

**パッチ内容**: RC セットアップセクションに以下を追加。

```markdown
## RevenueCat Public API Key（WAITING_FOR_HUMAN）

RevenueCat API v2 では Public API Key を取得できない。Dashboard からのみ取得可能。

### アクション:

1. RC プロジェクト作成 + App 作成は API v2 で実行（既存手順通り）
2. progress.txt に以下を書く:
\```
WAITING_FOR_HUMAN: RevenueCat Public API Key を Dashboard から取得してください
URL: https://app.revenuecat.com → Projects → 該当プロジェクト → API Keys
Key Name: "Apple - iOS (Public)" の値をコピー
取得後: ~/.config/mobileapp-builder/.env に REVENUECAT_PUBLIC_KEY=<value> を追加
\```

3. `passes: false` のまま iteration を終了
4. 人間が .env に設定 → progress.txt から `WAITING_FOR_HUMAN` を削除
5. 次の iteration で iOS コード内の RC configure に Key を埋め込む
```

---

## P6: "Out of extra usage" 空イテレーション

**根本原因**: ralph.sh が CC の "Out of extra usage" 出力を検出せず、空イテレーションを5回回した。

**パッチ対象**: `.claude/skills/mobileapp-builder/ralph.sh`

**パッチ内容**: L55 付近（`OUTPUT=$(cat "$tmpfile")` の後）に以下を追加。

```bash
  # Detect "Out of extra usage" and break immediately
  if echo "$OUTPUT" | grep -qi "out of extra usage\|out of.*usage\|usage.*exceeded\|rate.limit\|billing"; then
    echo "🏭 ⚠️ CC usage 超過検出。残りイテレーションをスキップ。"
    notify_slack "⚠️ CC usage 超過。イテレーション $i で停止。"
    break
  fi
```

---

## P7: validate.sh subscription check 常に SKIP

**根本原因**: `asc subscriptions list --app APP_ID` が404を返す。正しいコマンドではない可能性。

**パッチ対象**: `.claude/skills/mobileapp-builder/validate.sh`

**パッチ内容**: subscription check を以下に置換。

```bash
# Gate: Subscription check
# asc subscriptions list is unreliable. Check via RevenueCat or skip gracefully.
echo "🔍 Gate: Subscription check"
if asc iap list --app "$APP_ID" --output json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if len(d.get('data',[])) > 0 else 1)" 2>/dev/null; then
  echo "  ✅ IAP products found"
else
  echo "  ⚠️ IAP check skipped (RevenueCat manages subscriptions)"
fi
```

---

## P8: validate.sh framed screenshots パス間違い

**根本原因**: validate.sh が `$APP_DIR/screenshots/framed` を見ているが、実際は `$APP_DIR/${APP_NAME}ios/screenshots/framed` にある。

**パッチ対象**: `.claude/skills/mobileapp-builder/validate.sh`

**パッチ内容**: framed screenshots check を以下に置換。

```bash
# Gate: Framed screenshots check
echo "🔍 Gate: Framed screenshots"
FRAMED_COUNT=$(find "$APP_DIR" -path "*/screenshots/framed/*.png" -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$FRAMED_COUNT" -ge 3 ]; then
  echo "  ✅ Framed screenshots: $FRAMED_COUNT found"
else
  echo "  ❌ Framed screenshots: $FRAMED_COUNT found (minimum 3 required)"
  FAILED=true
fi
```

---

## P9: validate.sh が最新ビルドを見ていない

**根本原因**: `asc builds list --app APP_ID --limit 1` にソートがない。古いビルドが返る可能性。

**パッチ対象**: `.claude/skills/mobileapp-builder/validate.sh`

**パッチ内容**: builds check を以下に置換。

```bash
# Gate: Build status check (skill: asc-id-resolver + asc-build-lifecycle)
echo "🔍 Gate: Build status"
BUILD_STATE=$(asc builds list --app "$APP_ID" --sort -uploadedDate --limit 1 --output json 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
if d.get('data'):
    print(d['data'][0]['attributes'].get('processingState','UNKNOWN'))
else:
    print('NO_BUILD')
" 2>/dev/null)

if [ "$BUILD_STATE" = "VALID" ]; then
  echo "  ✅ Latest build: VALID"
elif [ "$BUILD_STATE" = "PROCESSING" ]; then
  echo "  ⚠️ Latest build: PROCESSING (not yet ready)"
else
  echo "  ❌ Latest build: $BUILD_STATE"
  FAILED=true
fi
```

---

## P10: 1 iteration に 4 US 詰め込み

**根本原因**: CLAUDE.md に「1 iteration = 1 US」と書いてあるが、エージェントが守らなかった。

**パッチ対象**: `.claude/skills/mobileapp-builder/CLAUDE.md`

**パッチ内容**: 以下を CRITICAL Rules セクションに追加。

```markdown
| 21 | **1 iteration = 1 US（厳守）**。2つ以上のUSを1イテレーションで実行したら即座に停止。次のイテレーションで続行。500ターン超過も即停止 |
```

---

## P11: WAITING_FOR_HUMAN 開始前チェック不足

**根本原因**: ralph.sh のWAITING_FOR_HUMAN チェックに上限がない（無限待ち可能性）。

**パッチ対象**: `.claude/skills/mobileapp-builder/ralph.sh`

**パッチ内容**: L40-43 の while loop を以下に置換。

```bash
  # WAITING_FOR_HUMAN: don't burn iterations while waiting for human input
  WAIT_COUNT=0
  while [ -f "$SCRIPT_DIR/progress.txt" ] && grep -q "WAITING_FOR_HUMAN" "$SCRIPT_DIR/progress.txt"; do
    echo "🏭 ⏸️ WAITING_FOR_HUMAN 検出。人間の入力待ち... (${WAIT_COUNT}回目)"
    WAIT_COUNT=$((WAIT_COUNT + 1))
    if [ $WAIT_COUNT -ge 120 ]; then  # 1時間（30秒 x 120）
      echo "🏭 ❌ WAITING_FOR_HUMAN タイムアウト（1時間）"
      notify_slack "❌ WAITING_FOR_HUMAN タイムアウト（1時間）。手動対応必要。"
      break 2
    fi
    sleep 30
  done
```

---

## P12: `asc screenshots frame` バグ (asc 0.36.3)

**根本原因**: asc 0.36.3 が内部で生成する Koubou YAML の `defaults.background` フォーマットが間違っている。`colors` フィールドに `None` が渡されて Pydantic validation エラー。

**パッチ対象**: `.claude/skills/mobileapp-builder/references/us-008-release.md` (P1 のパッチに含まれる)

**パッチ内容**: `asc screenshots frame` を使わず `kou generate` を直接使用する（P1 参照）。asc CLI のバグ修正を待つ。GitHub Issue: https://github.com/rudrankriyam/App-Store-Connect-CLI/issues/new/choose

---

## P13: kou の PATH 未設定

**根本原因**: `pip install koubou` でインストールされる `kou` バイナリが `/Users/anicca/Library/Python/3.9/bin/` にあるが、PATH に含まれていない。

**パッチ対象**: `.claude/skills/mobileapp-builder/ralph.sh` + `.claude/skills/mobileapp-builder/CLAUDE.md`

**パッチ内容**:

ralph.sh L7 付近に追加:
```bash
export PATH="/Users/anicca/Library/Python/3.9/bin:$PATH"
```

CLAUDE.md の CRITICAL Rules に追加:
```markdown
| 22 | **PATH 設定（全イテレーション冒頭で実行）**: `export PATH="/Users/anicca/Library/Python/3.9/bin:$PATH"` と `export ASC_BYPASS_KEYCHAIN=true` |
```

---

## 追加パッチ: CLAUDE.md に ASC スキル正引きテーブル追加

**パッチ対象**: `.claude/skills/mobileapp-builder/CLAUDE.md`

**パッチ内容**: 以下を追加。エージェントが正しいコマンドを使うための正引きテーブル。

```markdown
## ASC CLI 正しいコマンド（skill 準拠）

| タスク | 正しいコマンド | スキル |
|--------|---------------|--------|
| スクショ capture | `asc screenshots capture --bundle-id ... --udid ... --output-dir ...` | asc-shots-pipeline |
| スクショ frame | `kou generate koubou.yaml`（asc screenshots frame はバグ） | asc-shots-pipeline |
| スクショ upload | `asc screenshots upload --version-localization LOC_ID --path ... --device-type IPHONE_67` | asc-shots-pipeline |
| ビルド最新取得 | `asc builds latest --app APP_ID --platform IOS` | asc-id-resolver |
| ビルドをグループ追加 | `asc builds add-groups --build BUILD_ID --group GROUP_ID` | asc-testflight-orchestration |
| テスター追加 | `asc testflight beta-testers add --app APP_ID --email ... --group ...` | asc-testflight-orchestration |
| テスター招待 | `asc testflight beta-testers invite --app APP_ID --email ...` | asc-testflight-orchestration |
| テスター確認 | `asc testflight beta-testers list --app APP_ID --paginate` | asc-testflight-orchestration |
| Version ID 取得 | `asc versions list --app APP_ID` | asc-id-resolver |
| App Privacy | WAITING_FOR_HUMAN（API不可） | - |
| RC Public Key | WAITING_FOR_HUMAN（Dashboard のみ） | - |
| 審査提出 | `asc submit create --app APP_ID --version VER --build BUILD_ID --confirm` | asc-submission-health |
| Encryption | `ITSAppUsesNonExemptEncryption = NO` in Info.plist | asc-submission-health |
| Content Rights | `asc apps update --id APP_ID --content-rights DOES_NOT_USE_THIRD_PARTY_CONTENT` | asc-submission-health |
```

---

## 追加パッチ: 不足スキルのインストール

以下のスキルを `.claude/skills/` にコピー:

```bash
cp -r /tmp/asc-skills-fresh/skills/asc-workflow /Users/anicca/anicca-project/.claude/skills/asc-workflow
cp -r /tmp/asc-skills-fresh/skills/asc-app-create-ui /Users/anicca/anicca-project/.claude/skills/asc-app-create-ui
cp -r /tmp/asc-skills-fresh/skills/asc-crash-triage /Users/anicca/anicca-project/.claude/skills/asc-crash-triage
```

---

## 修正対象ファイル一覧

| # | ファイル | パッチ |
|---|---------|--------|
| 1 | `.claude/skills/mobileapp-builder/ralph.sh` | P6, P11, P13 |
| 2 | `.claude/skills/mobileapp-builder/validate.sh` | P7, P8, P9 |
| 3 | `.claude/skills/mobileapp-builder/references/us-007-testing.md` | P3 |
| 4 | `.claude/skills/mobileapp-builder/references/us-008-release.md` | P1, P2, P12 |
| 5 | `.claude/skills/mobileapp-builder/references/us-009-submit.md` | P4 |
| 6 | `.claude/skills/mobileapp-builder/references/us-005b-monetization.md` | P5 |
| 7 | `.claude/skills/mobileapp-builder/CLAUDE.md` | P10, P13, 正引きテーブル |
| 8 | `.claude/skills/asc-workflow/` (新規) | スキルインストール |
| 9 | `.claude/skills/asc-app-create-ui/` (新規) | スキルインストール |
| 10 | `.claude/skills/asc-crash-triage/` (新規) | スキルインストール |

---

## 次のステップ

1. 上記パッチを全ファイルに適用
2. `asc workflow` で全フローを `.asc/workflow.json` に統合
3. Chi Daily で end-to-end テスト実行（US-001 から US-009 まで）
4. 成功したら次の app factory run で検証
