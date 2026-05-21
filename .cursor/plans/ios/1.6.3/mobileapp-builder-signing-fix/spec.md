# mobileapp-builder: Signing Setup + Self-Iteration 強化 spec

## 概要（What & Why）

**What**: mobileapp-builder スキル全体（SKILL.md, references/*, scripts/*, SETUP.md）と
Mac Mini の mobileapp-factory スキルに対して以下を実装する:
1. Signing PREFLIGHT（Distribution cert + Provisioning Profile の汎用セットアップフロー）
2. 自己反復ゲートの強化（各フェーズ末尾の BLOCKING チェックポイント）
3. Anicca CEO パターンの強化（ワーカーへのガイダンス能力追加）
4. display name 変更ルールの追加
5. submit 前クリーンアップルールの追加

**Why**:
- 現状 Distribution cert が REVOKED になるとワーカーが詰まり人間介入が必要になる
- SKILL.md にオープンソース対応の署名セットアップ手順がない（誰のアカウントでも動く汎用フローがない）
- 自己改善ルールは文言だけで強制力がなく、エラーが起きても SKILL.md が更新されないことがある
- Anicca がワーカーの詰まりを検出しても具体的な解決策を送れない

---

## 受け入れ条件（テスト可能な形式）

| # | 条件 |
|---|------|
| 1 | Distribution cert が REVOKED でも PHASE 2.5 が自動で新規作成して進める |
| 2 | `check-prerequisites.sh` が Distribution cert の有効性チェックを含む |
| 3 | 各 PHASE の末尾に自己改善チェックが BLOCKING gate として存在する |
| 4 | `submission-checklist.md` に Signing Health セクションが存在する |
| 5 | `SETUP.md` に Signing Setup セクションが存在する |
| 6 | mobileapp-factory が詰まったワーカーに SKILL.md から解決策を送れる |
| 7 | 全コマンドが `convert` ではなく `magick` を使う |
| 8 | 全 RULE が「私は〜を学んだ」でなく「〜しろ」の命令形で書かれている |

---

## 変更対象ファイル一覧

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `SKILL.md` | 修正 + 追加 | PHASE 2.5 追加、RULE 37/38 書き直し、RULE 39 追加、自己改善ゲート追加、`convert`→`magick` 統一 |
| `references/submission-checklist.md` | 追加 | Section S（Signing Health）追加、F4 追加 |
| `scripts/check-prerequisites.sh` | 追加 | Distribution cert チェックブロック追加 |
| `SETUP.md` | 追加 | Section 4.5 Signing Setup 追加 |
| `mobileapp-factory/SKILL.md`（Mac Mini） | 修正 | STEP 3 ガイダンス強化、STEP 4 SKILL.md 更新検出追加 |

---

## As-Is / To-Be

### SKILL.md

**As-Is:**
- PHASE 2（SCAFFOLD）の直後にビルドが来る。署名セットアップは「自動署名に任せる」前提
- RULE 37: 「2026-02-28 実機確認済み」形式の日記スタイル
- SELF-IMPROVEMENT RULE: 文言はあるが PHASE フロー内に組み込まれていない
- ImageMagick コマンドが PHASE 9 で `convert` を使用（RULE 31 と矛盾）

**To-Be:**
- PHASE 2.5 SIGNING PREFLIGHT を PHASE 2 と PHASE 3 の間に挿入
- RULE 37/38 を命令形 action plan に書き直し
- RULE 39 追加（`INFOPLIST_KEY_CFBundleDisplayName` ルール）
- 各 PHASE 末尾に BLOCKING 自己改善チェックポイントを追加
- `convert` → `magick` 統一

### PHASE 2.5 の内容（新規追加）

```
PHASE 2.5: SIGNING PREFLIGHT

Step 1: 有効な Distribution cert を確認する
asc certificates list --type IOS_DISTRIBUTION --output json | python3 -c "
import sys,json
d=json.load(sys.stdin)
valid=[c for c in d['data'] if c['attributes'].get('certificateState')!='REVOKED']
if valid:
    print('✅ VALID cert exists:', valid[0]['attributes']['name'])
else:
    print('❌ NO VALID CERT — proceed to Step 2')
    exit(1)
"
→ 有効なものがあれば Step 3 へスキップ

Step 2: Distribution cert を新規作成する（REVOKED or 存在しない場合）
mkdir -p ~/Downloads/.signing
asc certificates csr generate ~/Downloads/.signing/dist.csr
# NOTE: openssl req 禁止 — Apple API が 409 で拒否する
asc certificates create --certificate-type IOS_DISTRIBUTION \
  --csr ~/Downloads/.signing/dist.csr \
  --output json | python3 -c "import sys,json;d=json.load(sys.stdin);print('CERT_ID:', d['data']['id'])"
# 発行された .cer を Keychain にインポート
# 秘密鍵パスを CERT_KEY_PATH 変数に保存

Step 3: Keychain の REVOKED 証明書を全て削除する
security find-identity -v -p codesigning | grep "REVOKED" | \
  awk '{print $3}' | while read hash; do
    security delete-certificate -Z "$hash"
    echo "Deleted REVOKED cert: $hash"
  done

Step 4: アプリ専用 Provisioning Profile を作成する
CERT_ID=$(asc certificates list --type IOS_DISTRIBUTION --output json | \
  python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data'][0]['id'])")
PROFILE_NAME="<app_name> AppStore Distribution"
asc profiles create \
  --profile-type IOS_APP_STORE \
  --bundle-id <BUNDLE_ID_RESOURCE_ID> \
  --certificate $CERT_ID \
  --name "$PROFILE_NAME" \
  --output json > /tmp/profile.json
PROFILE_UUID=$(python3 -c "import sys,json;d=json.load(open('/tmp/profile.json'));print(d['data']['attributes']['uuid'])")
# ~/Library/MobileDevice/Provisioning Profiles/ にインストール
asc profiles download --id $(python3 -c "import sys,json;d=json.load(open('/tmp/profile.json'));print(d['data']['id'])") \
  ~/Library/MobileDevice/Provisioning\ Profiles/

Step 5: Fastfile を manual signing テンプレートで更新する
# export_options に以下を追加:
# signingStyle: "manual"
# signingCertificate: "iPhone Distribution: <Name> (<Team ID>)"
# provisioningProfiles: { "<bundle_id>" => "<PROFILE_UUID>" }
# NOTE: signingStyle: "automatic" 禁止 — Xcode 管理プロファイルが REVOKED cert を参照している可能性
```

### 自己改善 BLOCKING ゲート（各 PHASE 末尾に追加）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 PHASE X 終了前チェック（BLOCKING）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
このフェーズで以下が1件でもあった場合は SKILL.md を修正してから次フェーズへ:
- CLI コマンドがエラーを返した
- 想定外の動作が起きた
- コマンドを訂正した

修正方法:
  1. SKILL.md の対応 PHASE または CRITICAL RULES に修正内容を追記
  2. git add SKILL.md && git commit -m "fix(mobileapp-builder): <修正内容>" && git push
  3. git push が完了したら次フェーズへ

禁止: エラーが起きたのに SKILL.md を修正せずに次フェーズへ進む
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### submission-checklist.md の追加セクション

```markdown
## S: 署名ヘルスチェック（PHASE 2.5 で実施済みであることを確認）

| # | チェック項目 | コマンド |
|---|------------|---------|
| S1 | 有効な Distribution cert が1件以上ある | `asc certificates list --type IOS_DISTRIBUTION` → REVOKED でない cert が存在 |
| S2 | Keychain に REVOKED Distribution 証明書がない | `security find-identity -v -p codesigning` → "REVOKED" が含まれない |
| S3 | アプリの Provisioning Profile がインストール済み | `ls ~/Library/MobileDevice/Provisioning\ Profiles/ | grep <PROFILE_UUID>` |
| S4 | Fastfile が signingStyle: "manual" を使用している | Fastfile の export_options を目視確認 |
```

### mobileapp-factory SKILL.md の強化（Mac Mini）

**STEP 3 追加内容:**
```
詰まり検出時のガイダンス手順:
1. process action:log sessionId:<id> で最後の50行を取得
2. エラーメッセージを抽出
3. SKILL.md の CRITICAL RULES をスキャンして対応する RULE を特定
4. process action:submit sessionId:<id> data:"<RULE に書いてある解決策>" でワーカーに送信
5. Slack に「ワーカーにガイダンスを送信しました: <内容>」と報告

共通エラーと送信内容のマッピング:
| エラーキーワード | 送信するガイダンス |
|---------------|-----------------|
| "Signing certificate is invalid" | "RULE 37: asc certificates csr generate → asc certificates create → Keychain import → delete REVOKED → new Profile → Fastfile manual signing" |
| "already added to another reviewSubmission" | "RULE 38: asc submit cancel --id <id> --confirm → asc submit create" |
| "INVALID_BINARY" | "RULE 35/36: Check primaryCategory + usesIdfa settings" |
```

**STEP 4 追加内容:**
```
SKILL.md 自己更新の検出:
git log --oneline -3 .claude/skills/mobileapp-builder/SKILL.md
→ 今回の実行で更新されていれば Slack に報告:
  「🔄 レシピが自己改善されました: <コミットメッセージ>」
```

---

## テストマトリックス

| # | To-Be | テスト方法 |
|---|-------|----------|
| 1 | PHASE 2.5 が存在する | SKILL.md に "PHASE 2.5" のセクションがある |
| 2 | check-prerequisites.sh に Distribution cert チェックがある | スクリプトを実行して cert チェック項目が表示される |
| 3 | submission-checklist.md に S セクションがある | ファイルに "## S:" が存在する |
| 4 | SETUP.md に Section 4.5 がある | ファイルに "Section 4.5" が存在する |
| 5 | RULE 37/38 が命令形になっている | "実機確認済み" の日記スタイル文言がない |
| 6 | RULE 39 が存在する | SKILL.md に INFOPLIST_KEY_CFBundleDisplayName ルールがある |
| 7 | `convert` コマンドが SKILL.md にない | grep で `convert ` がゼロ件 |
| 8 | mobileapp-factory に詰まり検出ガイダンスがある | スキルにエラーマッピングテーブルが存在する |

---

## 境界（やらないこと）

- spec-template.md, iap-bible.md, workflow-template.json, add_prices.py は変更しない（署名と無関係）
- アプリのコード（Swift/SwiftUI）は変更しない
- 既存の CRITICAL RULES 1〜36 の内容は変更しない（RULE 37/38 の形式のみ修正）
- mobileapp-factory スキルの STEP 1（Claude Code 起動方法）は変更しない

---

## 実行手順

```bash
# 1. MacBook で SKILL.md, submission-checklist.md, check-prerequisites.sh, SETUP.md を修正
cd /Users/cbns03/Downloads/anicca-project/.claude/skills/mobileapp-builder
# → 各ファイルを編集

# 2. Mac Mini で mobileapp-factory/SKILL.md を修正
ssh anicca@100.99.82.95
# → /Users/anicca/.openclaw/skills/mobileapp-factory/SKILL.md を編集

# 3. コミット・プッシュ
git add -A && git commit -m "feat(mobileapp-builder): signing preflight + self-iteration gates" && git push

# 4. Mac Mini で git pull して最新化
ssh anicca@100.99.82.95 "cd /Users/anicca/.openclaw/skills/mobileapp-factory && git pull"
```
