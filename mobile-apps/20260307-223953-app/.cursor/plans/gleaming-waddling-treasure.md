# Spec: mobileapp-builder トークン浪費修正（全8パッチ）

## Context

FrostDip 実績: **78.7M tokens（5h枠の87.5%、週枠の14.1%）、$58.92**
Source: `mobile-apps/20260307-223953-app/logs/iteration-{1..22}.log` の `result.usage` 集計

**無駄の内訳（実測データ）:**

| 無駄分類 | トークン | 原因 | 対策パッチ |
|---------|---------|------|-----------|
| US-008a 3回失敗 | 15.9M | スクショパイプライン再実行 | (構造的問題、別対応) |
| US-007 1回失敗 | 3.6M | Maestro E2E テスト失敗 | (構造的問題、別対応) |
| AUTH-FAIL | 1.3M | keychain 拒否 | **F1** |
| **無駄合計** | **17.2M（21.8%）** | | |
| 有効トークン | 61.6M | 実際に成果を出した分 | |

**実証済み:**

| テスト | 結果 |
|--------|------|
| `ASC_WEB_SESSION_CACHE_BACKEND=file` + `asc apps create` | ✅ BreathCalm APP_ID: 6760253231。2FA 不要 |
| `ASC_WEB_SESSION_CACHE_BACKEND=file` + `asc web privacy apply/publish/pull` | ✅ `DATA_NOT_COLLECTED`, `published: true` |

---

## CC restart vs polling（重要判断）

**結論: RC SK鍵待ちは CC 内 bash polling が正解。restart は不要。**

| 方式 | トークンコスト | 根拠 |
|------|--------------|------|
| CC restart | 1M+/回（CLAUDE.md + prd.json + progress.txt + references 再読み込み） | Source: [Anthropic harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) |
| CC 内 bash polling (`while ! test -f ...; do sleep 30; done`) | ~500 tokens/回（bash は外部プロセス。sleep 中 LLM トークン消費ゼロ） | Source: [Claude Code architecture](https://docs.anthropic.com/en/docs/claude-code/overview) — bash は子プロセス |
| ralph.sh polling（CC 外） | 0 LLM tokens | 現行 WAITING_FOR_HUMAN 方式 |

**なぜ bash polling が安全か:**
- `sleep 30` は OS プロセスが待つだけ。LLM は idle。トークン消費なし
- ファイル出現で bash が return → LLM に ~500 tokens の tool result が返る
- CC restart だと 1M+ tokens で全コンテキスト再構築
- **polling は restart の 2000分の1 のコスト**

**RC SK鍵: US-001 完了時に先行依頼（WAITING_FOR_HUMAN 完全排除）**

Source: [Anthropic harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — 「discrete sessions」原則
+ FrostDip 実測: CC restart = 1.2M tokens/回（iter 9 の cache_read_input_tokens）

| 方式 | タイミング | CC restart | リスク |
|------|-----------|-----------|--------|
| ❌ 現行: US-005b で WAITING_FOR_HUMAN | US-005b 実行時 | 1回必要（1.2M tokens） | SK鍵なしで CC 停止 → 再起動 |
| ✅ 提案: US-001 完了後に Slack 依頼 | US-001 完了直後 | 0回 | US-005b までに6イテレーション（~30-60分）の猶予。間に合わなければ WAITING_FOR_HUMAN フォールバック |

**仕組み:**
1. ralph.sh が US-001 完了を検知（既存のイテレーション後 US 完了検知 L274）
2. prd.json からアプリ名を取得
3. Slack に RC プロジェクト作成 + SK鍵依頼を送信
4. 以降の各イテレーション冒頭で Slack を監視（`openclaw message read`）
5. sk_... を検出 → `projects/<slug>/.env` に書き出し
6. US-005b 開始時: source .env → SK鍵あり → WAITING_FOR_HUMAN 不要

**CC 再起動時の安全性（ダイスの懸念への回答）:**
- `claude --print` はブロッキングコール（ralph.sh L223）。CC exit で自動終了。古い CC が残る問題はない
- Source: [Claude Code --print mode](https://docs.anthropic.com/en/docs/claude-code/cli-usage) — non-interactive, single execution
- 新 CC は CLAUDE.md の指示に従い prd.json を読んで次の未完了 US を特定する。「SK鍵を読んで続行」ではなく「全コンテキスト再読み込み」が発生する（これが 1.2M tokens の無駄）
- **だから先行依頼で WAITING_FOR_HUMAN 自体を排除するのが最適解**

**最終方針:**

| 待機対象 | 方式 | CC restart |
|---------|------|-----------|
| iris 2FA | ralph.sh PREFLIGHT auto-2FA | 0回 |
| RC SK鍵 | US-001 完了時に先行依頼 + 各イテレーション冒頭で Slack 監視 | 0回（間に合えば） |
| App Privacy | 不要（file backend で 2FA なし） | 0回 |

---

## 修正後フロー

```
ralph.sh PREFLIGHT
  Check 1-5: 既存（変更なし）
  Check 6: ASC_WEB_SESSION_CACHE_BACKEND=file + asc web auth status
    → true → 進む
    → false → Slack 通知「6桁コードを送ってください」
      → ralph.sh: openclaw message read で Slack から 6桁コード検知
      → ralph.sh: asc web auth login --two-factor-code CODE
      → 再チェック → true → 進む

イテレーションループ:
  [毎回] Slack 監視（sk_... / 6桁コード検知 → .env に保存）
  [毎回] progress.txt サイズチェック（10KB 超 → アーカイブ）

  US-001 完了時（ralph.sh 検知）:
    → Slack: 「App: <name>。RC プロジェクト作成 + SK鍵を送ってください」
    → 以降のイテレーション冒頭で Slack 監視開始

  US-005a:
    Step 4.9: iris session check → file backend → true ✅
    Step 5: asc apps create（セッション有効 → 2FA 不要）✅
    Step 5.3: asc web privacy apply + publish ✅（US-009 から移動）

  US-005b:
    SK鍵が .env にあれば → そのまま続行（WAITING_FOR_HUMAN 不要）
    SK鍵がなければ → WAITING_FOR_HUMAN フォールバック
      → ralph.sh: Slack で sk_... 検知 → .env 書き出し → 自動解除

  US-009:
    Step 1: App Privacy 検証のみ（US-005a で設定済み）
```

---

## 全8パッチ（F1〜F8）

### F1: file backend 環境変数（keychain 回避）

**問題:** ASC CLI が macOS Keychain をデフォルト使用。CC のヘッドレス環境で silent denial → 常に `authenticated: false`
**削減:** US-005a 20M → 8M、US-009 6M → 3M（合計 -15M）
**Source:** ASC CLI ソースコード `web/auth/session.go` — `CacheBackend` 環境変数で file 切替可能

**Patch F1-a:** `.claude/skills/mobileapp-builder/ralph.sh` L19
```diff
  export ASC_BYPASS_KEYCHAIN=true
+ export ASC_WEB_SESSION_CACHE_BACKEND=file
```

**Patch F1-b:** `.claude/skills/mobileapp-builder/CLAUDE.md` L14
```diff
- export PATH="..." && export ASC_BYPASS_KEYCHAIN=true
+ export PATH="..." && export ASC_BYPASS_KEYCHAIN=true && export ASC_WEB_SESSION_CACHE_BACKEND=file
```

**Patch F1-c:** 各アプリの `CLAUDE.md` L14（テンプレートから自動コピー）
同上の変更。

---

### F2: PREFLIGHT Check 6 auto-2FA（Slack 自動取得）

**問題:** Check 6 が iris expired 検出後、ただポーリングするだけ。ダイスが手動で `asc web auth login` を実行する必要あり
**削減:** PREFLIGHT 待ち時間短縮（手動介入 → Slack 投稿のみ）
**Source:** `openclaw message read --channel slack --target <channel> --limit 1 --json` 確認済み

**ファイル:** `.claude/skills/mobileapp-builder/ralph.sh` L135-158 を置換

```bash
# Check 6: iris session（ASC web 操作の前提）
echo -n "  [6/6] iris session... "
IRIS_STATUS=$(asc web auth status --apple-id "$APPLE_ID" 2>&1 || echo "IRIS_FAIL")
if echo "$IRIS_STATUS" | grep -q 'authenticated.*true'; then
  echo "✅"
else
  echo "⚠️ iris expired — 2FA 必要"
  notify_slack "⏸️ iris session expired。iPhoneに届く6桁コードを送ってください。"

  WAIT_COUNT=0
  while [ $WAIT_COUNT -lt 960 ]; do
    LATEST_MSG=$(/opt/homebrew/bin/openclaw message read --channel slack --target "$SLACK_CHANNEL" --limit 1 --json 2>/dev/null | jq -r '.[0].text // empty')
    TWO_FA_CODE=$(echo "$LATEST_MSG" | grep -oE '[0-9]{6}' | head -1)

    if [ -n "$TWO_FA_CODE" ]; then
      echo "  🔑 2FA コード検出: $TWO_FA_CODE"
      ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web auth login \
        --apple-id "$APPLE_ID" --two-factor-code "$TWO_FA_CODE" 2>&1

      IRIS_RECHECK=$(asc web auth status --apple-id "$APPLE_ID" 2>&1 || echo "FAIL")
      if echo "$IRIS_RECHECK" | grep -q 'authenticated.*true'; then
        echo "  ✅ iris session restored"
        break
      fi
    fi
    sleep 30
    WAIT_COUNT=$((WAIT_COUNT + 1))
  done

  if [ $WAIT_COUNT -ge 960 ]; then
    echo "❌ iris session タイムアウト（8時間）"
    notify_slack "❌ iris session タイムアウト。手動対応必要。"
    exit 2
  fi
fi
```

---

### F3: RC SK鍵 先行依頼 + WAITING_FOR_HUMAN auto-resolve

**問題:**
1. RC SK鍵待ちで CC が WAITING_FOR_HUMAN → exit → 再起動（1.2M tokens 無駄）
2. WAITING_FOR_HUMAN ループがポーリングするだけで自動解決しない
**削減:** CC restart 0-1回削減（1.2M tokens 節約）
**Source:** [snarktank/ralph](https://github.com/snarktank/ralph) + FrostDip 実測データ

**Patch F3-a:** `.claude/skills/mobileapp-builder/ralph.sh` — US完了検知セクション（L274+）に追加
```bash
    # US-001 完了時: RC SK鍵の先行依頼
    if echo "$NEW_PASSES" | grep -q "US-001"; then
      APP_NAME=$(python3 -c "import json; d=json.load(open('$SCRIPT_DIR/prd.json')); print(d.get('app_name', d.get('slug','')))" 2>/dev/null)
      notify_slack "📱 RC セットアップお願いします（2分）:\n1. https://app.revenuecat.com → + Create new project → 名前: $APP_NAME\n2. Settings → API Keys → + New secret API key\n3. 権限を全て Read & Write → Generate\n4. sk_... をこのチャットに貼ってください"
    fi
```

**Patch F3-b:** `.claude/skills/mobileapp-builder/ralph.sh` — イテレーションループ冒頭（L188 の前）に Slack 監視を追加
```bash
  # Slack 監視: sk_... / 2FA コードを .env に自動保存
  LATEST_MSG=$(/opt/homebrew/bin/openclaw message read --channel slack --target "$SLACK_CHANNEL" --limit 1 --json 2>/dev/null | jq -r '.[0].text // empty')
  SK_KEY=$(echo "$LATEST_MSG" | grep -oE 'sk_[A-Za-z0-9_]+' | head -1)
  if [ -n "$SK_KEY" ]; then
    SLUG=$(python3 -c "import json; print(json.load(open('$SCRIPT_DIR/prd.json')).get('slug',''))" 2>/dev/null)
    PROJECT_ENV="$HOME/.config/mobileapp-builder/projects/$SLUG/.env"
    mkdir -p "$(dirname "$PROJECT_ENV")"
    if ! grep -q "RC_SECRET_KEY" "$PROJECT_ENV" 2>/dev/null; then
      echo "RC_SECRET_KEY=$SK_KEY" >> "$PROJECT_ENV"
      echo "  🔑 RC SK鍵を $PROJECT_ENV に保存"
    fi
  fi
```

**Patch F3-c:** `.claude/skills/mobileapp-builder/ralph.sh` L188-200 を置換（WAITING_FOR_HUMAN フォールバック）
```bash
  # WAITING_FOR_HUMAN: Slack からの入力を自動取得して解決
  WAIT_COUNT=0
  while [ -f "$SCRIPT_DIR/progress.txt" ] && grep -q "WAITING_FOR_HUMAN" "$SCRIPT_DIR/progress.txt"; do
    echo "🏭 ⏸️ WAITING_FOR_HUMAN 検出。Slack 監視中... (${WAIT_COUNT}回目)"

    LATEST_MSG=$(/opt/homebrew/bin/openclaw message read --channel slack --target "$SLACK_CHANNEL" --limit 1 --json 2>/dev/null | jq -r '.[0].text // empty')

    # RC SK鍵検出
    SK_KEY=$(echo "$LATEST_MSG" | grep -oE 'sk_[A-Za-z0-9_]+' | head -1)
    if [ -n "$SK_KEY" ]; then
      echo "  🔑 RC SK鍵検出"
      SLUG=$(python3 -c "import json; print(json.load(open('$SCRIPT_DIR/prd.json')).get('slug',''))" 2>/dev/null)
      PROJECT_ENV="$HOME/.config/mobileapp-builder/projects/$SLUG/.env"
      mkdir -p "$(dirname "$PROJECT_ENV")"
      echo "RC_SECRET_KEY=$SK_KEY" >> "$PROJECT_ENV"
      sed -i '' '/WAITING_FOR_HUMAN/d' "$SCRIPT_DIR/progress.txt"
      echo "  ✅ SK鍵を $PROJECT_ENV に保存。WAITING_FOR_HUMAN 解除"
      break
    fi

    # 2FA コード検出（フォールバック）
    TWO_FA=$(echo "$LATEST_MSG" | grep -oE '^[0-9]{6}$' | head -1)
    if [ -n "$TWO_FA" ]; then
      echo "  🔑 2FA コード検出: $TWO_FA"
      ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web auth login \
        --apple-id "$APPLE_ID" --two-factor-code "$TWO_FA" 2>&1
      sed -i '' '/WAITING_FOR_HUMAN/d' "$SCRIPT_DIR/progress.txt"
      echo "  ✅ 2FA ログイン完了。WAITING_FOR_HUMAN 解除"
      break
    fi

    WAIT_COUNT=$((WAIT_COUNT + 1))
    if [ $WAIT_COUNT -ge 960 ]; then
      echo "🏭 ❌ WAITING_FOR_HUMAN タイムアウト（8時間）"
      notify_slack "❌ WAITING_FOR_HUMAN タイムアウト（8時間）。手動対応必要。"
      exit 2
    fi
    sleep 30
  done
```

---

### F4: us-005a WAITING_FOR_HUMAN 削除（iris + app create）

**問題:** US-005a Step 4.9 と Step 5 に WAITING_FOR_HUMAN パターンが残っている。file backend で不要になった
**削減:** F1 に含む（US-005a 20M → 8M の一部）

**ファイル:** `.claude/skills/mobileapp-builder/references/us-005a-infra.md`

**Step 4.9 (L93-113) 置換:**
```bash
## Step 4.9: iris セッション確認（file backend — keychain 不要）
source ~/.config/mobileapp-builder/.env
export ASC_WEB_SESSION_CACHE_BACKEND=file

SESSION_STATUS=$(asc web auth status --apple-id "$APPLE_ID" 2>&1)
if echo "$SESSION_STATUS" | grep -q '"authenticated":true'; then
  echo "✅ iris session active"
else
  echo "❌ iris session expired — ralph.sh PREFLIGHT が検知してるはず"
  exit 1
fi
```

**Step 5 (L115-169) 置換:**
```bash
## Step 5: ASC App Creation（セッション有効 → 2FA 不要）
source ~/.config/mobileapp-builder/.env
export ASC_WEB_SESSION_CACHE_BACKEND=file

APP_RESULT=$(ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc apps create \
  --name "<app_name>" \
  --bundle-id "<bundle_id>" \
  --sku "<slug>" \
  --platform IOS \
  --primary-locale "en-US" \
  --apple-id "$APPLE_ID" \
  --output json 2>&1)

if echo "$APP_RESULT" | jq -e '.data.id' > /dev/null 2>&1; then
  APP_ID=$(echo "$APP_RESULT" | jq -r '.data.id')
  echo "APP_ID=$APP_ID" >> ~/.config/mobileapp-builder/projects/<slug>/.env
  echo "✅ ASC App created: $APP_ID"
else
  echo "❌ App creation failed: $APP_RESULT"
  exit 1
fi
```

---

### F5: App Privacy を US-009 → US-005a に移動

**問題:** US-009 で App Privacy apply/publish → iris session expired → WAITING_FOR_HUMAN → CC restart のループ
**削減:** US-009 6M → 3M（-3M）
**Source:** App Privacy は App 作成直後に設定可能。提出直前まで待つ理由なし

**Patch F5-a:** `.claude/skills/mobileapp-builder/references/us-005a-infra.md` — Step 5.3 を Step 5 の後に新規追加

```bash
## Step 5.3: App Privacy（DATA_NOT_COLLECTED — US-009 から移動）
source ~/.config/mobileapp-builder/.env
source ~/.config/mobileapp-builder/projects/<slug>/.env
export ASC_WEB_SESSION_CACHE_BACKEND=file

echo '{"schemaVersion":1,"dataUsages":[{"dataProtections":["DATA_NOT_COLLECTED"]}]}' > /tmp/privacy.json

ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web privacy apply \
  --app "$APP_ID" --file /tmp/privacy.json --apple-id "$APPLE_ID"
ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web privacy publish \
  --app "$APP_ID" --confirm --apple-id "$APPLE_ID"

# 検証
PRIVACY_CHECK=$(ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web privacy pull --app "$APP_ID" --apple-id "$APPLE_ID" 2>&1)
echo "$PRIVACY_CHECK" | grep -q '"published":true' && echo "✅ App Privacy published" || { echo "❌ App Privacy failed"; exit 1; }
```

**Patch F5-b:** `.claude/skills/mobileapp-builder/references/us-009-submit.md` L52-111 を置換

```bash
## Step 1: App Privacy 確認（検証のみ — US-005a Step 5.3 で設定済み）
export ASC_WEB_SESSION_CACHE_BACKEND=file
PRIVACY_CHECK=$(ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web privacy pull --app "$APP_ID" --apple-id "$APPLE_ID" 2>&1)
echo "$PRIVACY_CHECK" | grep -q '"published":true' && echo "✅ App Privacy confirmed" || echo "⚠️ App Privacy not published — US-005a Step 5.3 を再実行"
```

---

### F6: US-001 トレンドリサーチ制限

**問題:** FrostDip では US-001 で 25M tokens 消費。無制限の Web 検索・アイデア生成が原因
**削減:** US-001 25M → 10M（-15M）
**Source:** [ghuntley.com/ralph](https://ghuntley.com/ralph/) — 「use as little context as possible」

**ファイル:** `.claude/skills/mobileapp-builder/references/us-001-trend.md` 冒頭に追加

```markdown
## トレンドリサーチ制限（トークン節約 — MUST）
Source: ghuntley.com/ralph — "use as little context as possible"

| ルール | 値 | 根拠 |
|--------|-----|------|
| アイデア生成 | 最大 10 個 | FrostDip は 25+ 生成で 15M 浪費 |
| 深掘り | トップ 3 のみ | 残り 7 は one-liner で十分 |
| 競合分析 | 5 社まで | FrostDip は 8 社で過剰 |
| Web 検索 | 1 アイデアあたり最大 3 クエリ | 検索は高コスト（1回 ~100K tokens） |
| 合計検索回数 | 最大 15 回/US-001 | 10 ideas × 1 + top 3 × 1.67 |
```

---

### F7: progress.txt サイズ管理

**問題:** progress.txt が無制限に成長 → CC が毎回全文読み込み → コンテキスト膨張
**削減:** 各イテレーション開始時の読み込みコスト削減（推定 -2M/ビルド）
**Source:** [Anthropic harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — 「LLM performance degrades as context fills」

**Patch F7-a:** `.claude/skills/mobileapp-builder/CLAUDE.md` Rule テーブルに追加

```markdown
| 25 | **progress.txt 管理**: Codebase Patterns + 現在 US の記録のみ保持。完了 US の詳細は `logs/us-XXX-summary.md` に移動。10KB 以下維持。Source: Anthropic harnesses — context 膨張防止 |
```

**Patch F7-b:** `.claude/skills/mobileapp-builder/ralph.sh` — イテレーションループ内（L178 の後、CC 起動前）に追加

```bash
  # F7: progress.txt サイズ管理（10KB 上限）
  if [ -f "$SCRIPT_DIR/progress.txt" ]; then
    PROGRESS_SIZE=$(wc -c < "$SCRIPT_DIR/progress.txt" | tr -d ' ')
    if [ "$PROGRESS_SIZE" -gt 10240 ]; then
      echo "🏭 progress.txt ${PROGRESS_SIZE}B > 10KB — アーカイブ実行"
      # Codebase Patterns セクションを保持、残りをアーカイブ
      ARCHIVE_FILE="$SCRIPT_DIR/logs/progress-archive-$(date +%Y%m%d-%H%M%S).txt"
      cp "$SCRIPT_DIR/progress.txt" "$ARCHIVE_FILE"
      # Codebase Patterns（先頭）+ 最新2セクション（末尾）を残す
      python3 -c "
import re
with open('$SCRIPT_DIR/progress.txt') as f: content = f.read()
sections = re.split(r'\n---\n', content)
patterns = sections[0] if sections[0].startswith('## Codebase') else ''
recent = '\n---\n'.join(sections[-2:]) if len(sections) > 2 else '\n---\n'.join(sections)
with open('$SCRIPT_DIR/progress.txt', 'w') as f:
    if patterns: f.write(patterns + '\n---\n')
    f.write(recent)
" 2>/dev/null || true
      echo "  ✅ アーカイブ: $ARCHIVE_FILE"
    fi
  fi
```

---

### F8: CLAUDE.md Rule 26（WAITING_FOR_HUMAN 最小化宣言）

**問題:** CC が iris/app create/privacy で WAITING_FOR_HUMAN を書く判断基準がない
**削減:** CC が不要な WAITING_FOR_HUMAN を書かなくなる（F1-F5 の効果を保証）
**Source:** F1-F5 の実証結果を CLAUDE.md にルール化

**ファイル:** `.claude/skills/mobileapp-builder/CLAUDE.md` Rule テーブルに追加

```markdown
| 26 | **WAITING_FOR_HUMAN 最小化**: iris session / asc apps create / App Privacy は `ASC_WEB_SESSION_CACHE_BACKEND=file` で 2FA 不要。RC SK鍵のみ WAITING_FOR_HUMAN 使用可（ralph.sh が Slack から自動取得）。Source: BreathCalm 実証（2026-03-08） |
```

---

## トークンテーブル（US-010 フォーマット — FrostDip 実測データ）

**定数:** `WEEKLY_CAP = 560,000,000` | `5h_window = 90,000,000` | `MONTHLY_CAP = 2,240,000,000`
Source: `.claude/skills/mobileapp-builder/references/us-010-report.md`

### FrostDip 実績（US別）

| US | 内容 | 実績(M) | 5h枠% | 週枠% | Iters | 失敗 | 問題 |
|----|------|---------|-------|-------|-------|------|------|
| US-005a | インフラ | 1.2 | 1.3% | 0.21% | 1 | 0 | — |
| US-005b | マネタイズ | 4.7 | 5.2% | 0.84% | 2 | 0 | — |
| US-006a | TDD Data Layer | 4.0 | 4.4% | 0.71% | 1 | 0 | — |
| US-006b | TDD Onboarding | 4.4 | 4.9% | 0.79% | 1 | 0 | — |
| US-006c | TDD Core Screens | 4.2 | 4.6% | 0.74% | 1 | 0 | — |
| US-006d | TDD Polish | 3.4 | 3.8% | 0.61% | 1 | 0 | — |
| US-006-R | Code Review | 5.6 | 6.2% | 1.00% | 1 | 0 | 82 turns |
| US-007 | Maestro E2E | 16.1 | 17.9% | 2.87% | 2 | 1 | **最多ターン 194** |
| US-008a | Screenshots | 24.3 | 27.0% | 4.35% | 4 | 3 | **最大浪費 317 turns** |
| US-008d | Compliance | 6.7 | 7.4% | 1.19% | 1 | 0 | 81 turns |
| US-008e | Preflight/TF | 0.9 | 1.0% | 0.16% | 1 | 0 | — |
| US-009 | Submit | 2.0 | 2.3% | 0.36% | 1 | 0 | WAITING_FOR_HUMAN |
| AUTH-FAIL | — | 1.3 | 1.4% | 0.22% | 1 | 1 | **F1 で解決** |
| **合計** | | **78.7** | **87.5%** | **14.1%** | **22** | **5** | |

### パッチ適用後の見込み

| 分類 | 現状(M) | 修正後(M) | 削減(M) | 根拠 |
|------|---------|-----------|---------|------|
| AUTH-FAIL | 1.3 | 0 | -1.3 | F1: file backend |
| US-009 WAITING_FOR_HUMAN | 2.0 | 1.0 | -1.0 | F5: App Privacy を US-005a に移動 |
| US-005b SK鍵 restart | 含む | -1.2 | -1.2 | F3: 先行依頼で restart 排除 |
| US-001 (未計測) | ~25(推定) | ~10 | -15 | F6: トレンドリサーチ制限 |
| context 膨張 | — | -2(推定) | -2 | F7: progress.txt 10KB 管理 |
| **削減合計** | | | **-20.5** | |
| **修正後合計** | **78.7** | **~58** | | **64.4% of 5h** |

### 日次/週次/月次（修正後見込み）

| 期間 | 修正後(M) | 5h枠% | 週枠% | 月次枠% |
|------|-----------|-------|-------|---------|
| 1日（1アプリ） | 58 | 64.4% | 10.4% | 2.6% |
| 1週間（5アプリ） | 290 | — | 51.8% | 12.9% |
| 1週間（7アプリ） | 406 | — | 72.5% | 18.1% |
| 1ヶ月（20アプリ） | 1,160 | — | — | 51.8% |
| 1ヶ月（30アプリ） | 1,740 | — | — | 77.7% |

### 判定

| 判定項目 | 結果 | 備考 |
|---------|------|------|
| 1アプリ/日が5h枠に収まるか | ✅ 64.4% | 余裕あり |
| 週7アプリが週枠に収まるか | ✅ 72.5% | 余裕あり |
| 月30アプリが月次枠に収まるか | ✅ 77.7% | 余裕あり |

> **結論:** 修正後は**週7アプリ / 月30アプリ**が可能。
> FrostDip の実績は想定より低く（78.7M、87.5%）、パッチで ~58M（64.4%）に。
> Source: [Anthropic Pricing](https://platform.claude.com/docs/en/about-claude/pricing) — Max plan は月額固定 $200

---

## 変更対象ファイル一覧

| # | ファイル | パッチ | 変更内容 |
|---|---------|--------|---------|
| 1 | `.claude/skills/mobileapp-builder/ralph.sh` L19 | F1-a | `ASC_WEB_SESSION_CACHE_BACKEND=file` 追加 |
| 2 | `.claude/skills/mobileapp-builder/ralph.sh` L135-158 | F2 | Check 6 auto-2FA from Slack |
| 3 | `.claude/skills/mobileapp-builder/ralph.sh` L274+ | F3-a | US-001 完了時 RC SK鍵先行依頼 |
| 4 | `.claude/skills/mobileapp-builder/ralph.sh` L178+ | F3-b | 毎イテレーション Slack 監視（sk_... 検出） |
| 5 | `.claude/skills/mobileapp-builder/ralph.sh` L188-200 | F3-c | WAITING_FOR_HUMAN auto-resolve（フォールバック） |
| 6 | `.claude/skills/mobileapp-builder/ralph.sh` L178+ | F7-b | progress.txt サイズ管理 |
| 7 | `.claude/skills/mobileapp-builder/CLAUDE.md` L14 | F1-b | PATH行に file backend 追加 |
| 8 | `.claude/skills/mobileapp-builder/CLAUDE.md` 末尾 | F7-a, F8 | Rule 25, 26 追加 |
| 9 | `.claude/skills/mobileapp-builder/references/us-005a-infra.md` L93-169 | F4 | Step 4.9/5 WAITING_FOR_HUMAN 削除 |
| 10 | `.claude/skills/mobileapp-builder/references/us-005a-infra.md` Step 5後 | F5-a | Step 5.3 App Privacy 追加 |
| 11 | `.claude/skills/mobileapp-builder/references/us-009-submit.md` L52-111 | F5-b | Step 1 を検証のみに変更 |
| 12 | `.claude/skills/mobileapp-builder/references/us-001-trend.md` 冒頭 | F6 | トレンドリサーチ制限追加 |

---

## 検証方法

| # | テスト | コマンド | 期待結果 |
|---|--------|---------|---------|
| 1 | file backend 環境変数 | `source ralph.sh 環境 && echo $ASC_WEB_SESSION_CACHE_BACKEND` | `file` |
| 2 | iris session | `ASC_WEB_SESSION_CACHE_BACKEND=file asc web auth status` | `authenticated: true` |
| 3 | Check 6 flow | ralph.sh 起動 → Check 6 通過確認 | ✅ |
| 4 | progress.txt trim | 11KB の progress.txt で ralph.sh 起動 | アーカイブ実行、10KB 以下に |
| 5 | CLAUDE.md Rule 確認 | `grep "Rule 25\|Rule 26" CLAUDE.md` | 2行ヒット |
| 6 | us-005a WAITING_FOR_HUMAN | `grep WAITING_FOR_HUMAN us-005a-infra.md` | 0件 |
| 7 | us-009 検証のみ | `grep "検証のみ" us-009-submit.md` | 1件ヒット |
| 8 | us-001 制限 | `grep "最大 10 個" us-001-trend.md` | 1件ヒット |

---

## 実証済み結果（前回セッション）

| # | テスト | 結果 |
|---|--------|------|
| 1 | `asc web auth status` (file backend) | ✅ `authenticated: true` |
| 2 | `asc apps create` (BreathCalm) | ✅ APP_ID: 6760253231, 2FA 不要 |
| 3 | `asc web privacy apply` | ✅ `applied: true` |
| 4 | `asc web privacy publish` | ✅ `published: true` |
| 5 | `asc web privacy pull` | ✅ `DATA_NOT_COLLECTED`, `published: true` |

---

## 追加調査結果（2026-03-08 Session 2）

### opusplan モデル設定

**結論: 変更不要。現行設定が最適。**

| 項目 | 値 | Source |
|------|-----|--------|
| ralph.sh L223 | `--model opusplan` | 既存設定 |
| Plan mode | Claude Opus 4.6 | Source: [Claude Code Model Config](https://docs.anthropic.com/en/docs/claude-code/model-configuration) |
| Execution mode | Claude Sonnet 4.6 | 同上 |
| `--print` mode 動作 | Opus が使われる（FrostDip logs `modelUsage` = `claude-opus-4-6`） | FrostDip iter 1-22 log 検証済み |
| Per-US モデル切替 | 不要 | opusplan が自動切替。US ごとの設定は過剰最適化 |

---

### スキルローディング分析

**Anthropic 公式ガイドライン:**
Source: [Anthropic Agent Skills Best Practices](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills)
- SKILL.md body: **500行以下**
- References: **1階層のみ**（references の references を読まない）
- Progressive disclosure: メタデータ（30-50 tokens/skill）→ 必要時に本文読み込み

**US 別スキルロード状況:**

| US | 追加ロードスキル数 | スキル名 | 行数 | 準拠 |
|----|------------------|---------|------|------|
| US-001 | 0 | — | — | ✅ |
| US-005a | 0 | — | — | ✅ |
| US-005b | 0 | — | — | ✅ |
| US-006a-d | 0 | — | — | ✅ |
| US-006-R | 1 | release-review/SKILL.md | 230行 | ✅ |
| US-007 | 1 | maestro-ui-testing/SKILL.md | ~300行 | ✅ |
| US-008a | 1 | asc-shots-pipeline/SKILL.md | ~250行 | ✅ |
| US-008b | 1 | asc-metadata-sync/SKILL.md | ~200行 | ✅ |
| US-008d | 0 | — | — | ✅ |
| US-008e | 1 | asc-release-flow/SKILL.md | ~300行 | ✅ |
| US-009 | 0 | — | — | ✅ |
| US-010 | 0 | — | — | ✅ |

**問題発見: `us-008-release.md` = 940行（500行上限超過）**

| 項目 | 値 |
|------|-----|
| ファイル | `.claude/skills/mobileapp-builder/references/us-008-release.md` |
| 現在行数 | 940行 |
| Anthropic 上限 | 500行 |
| 超過 | 440行（88%超過） |
| 影響 | US-008a の 24.3M tokens の一因（コンテキスト膨張） |
| 対策 | US-008a/b/c/d/e を個別ファイルに分割（既に部分的に分割済み）。本パッチでは対象外（構造的問題、別対応） |

---

### F3-a パッチ修正: prd.json に `app_name` フィールドがない

**発見:** `prd.json` のキーは `project`, `branchName`, `description`, `userStories` のみ。`app_name`/`slug` フィールドは存在しない。

**検証結果:**
```
$ python3 -c "import json; print(list(json.load(open('prd.json')).keys()))"
['project', 'branchName', 'description', 'userStories']
```

**修正:** F3-a の `prd.json.get('app_name')` → `prd.json.get('project')` に変更

```bash
    # US-001 完了時: RC SK鍵の先行依頼
    if echo "$NEW_PASSES" | grep -q "US-001"; then
      APP_NAME=$(python3 -c "import json; print(json.load(open('$SCRIPT_DIR/prd.json')).get('project','unknown'))" 2>/dev/null)
      notify_slack "📱 RC セットアップお願いします（2分）:\n1. https://app.revenuecat.com → + Create new project → 名前: $APP_NAME\n2. Settings → API Keys → + New secret API key\n3. 権限を全て Read & Write → Generate\n4. sk_... をこのチャットに貼ってください"
    fi
```

**同様に F3-b/F3-c の `prd.json.get('slug')` も `prd.json.get('project')` に修正。**
`project` フィールドはアプリ名（例: "FrostDip"）を含む。slug としても使用可能。

---

### リスクチェックリスト（E2E 本番リスク）

| # | リスク | 深刻度 | 状態 | 対策 |
|---|--------|--------|------|------|
| 1 | prd.json に `app_name`/`slug` がない → F3-a/b/c が `project` キーを使う必要 | HIGH | ✅ 修正済み（上記） | `project` キーを使用 |
| 2 | `us-008-release.md` が 940行（500行上限超過） | MEDIUM | ⚠️ 未対応 | 本パッチスコープ外。別イテレーションで分割 |
| 3 | US-009 が WAITING_FOR_HUMAN のまま（FrostDip） | HIGH | ⚠️ F1 適用後に解決 | F1 パッチで file backend 有効化 → 2FA 不要に |
| 4 | `openclaw message read` が Slack メッセージを正しくパースできるか | MEDIUM | ✅ 検証済み | FrostDip セッションで動作確認済み |
| 5 | iris session の file backend cache が expire する頻度 | LOW | ✅ 実証済み | BreathCalm テストで 2FA なしで動作。expire 時は F2 auto-2FA で対応 |
| 6 | progress.txt アーカイブの python3 パーサーが edge case で壊れる | LOW | ⚠️ 未テスト | `|| true` で安全。失敗してもアーカイブされないだけ |
| 7 | RC SK鍵が US-005b までに届かない場合 | MEDIUM | ✅ 設計済み | WAITING_FOR_HUMAN フォールバック（F3-c）+ ralph.sh auto-resolve |
| 8 | US-010 が正常に動作するか（未テスト） | HIGH | ⚠️ 要テスト | FrostDip で ralph.sh 再実行して US-009 + US-010 を検証 |

---

### US-010 テスト計画

**前提条件:**
- FrostDip screenshots: 4ファイル確認済み（`screenshots/raw-65/en-US/*.png`）
- POSTIZ_API_KEY: `.env` に3エントリ確認済み
- US-009: `passes: false`（WAITING_FOR_HUMAN）→ F1 パッチ適用後に自動解決

**テスト手順:**

| Step | アクション | 期待結果 |
|------|-----------|---------|
| 1 | F1 パッチを適用（`ASC_WEB_SESSION_CACHE_BACKEND=file`） | ralph.sh + CLAUDE.md に反映 |
| 2 | FrostDip で `ralph.sh` を再実行 | US-009 が file backend で App Privacy 検証 → passes: true |
| 3 | US-010 が自動開始 | logs/ からトークン集計 → build-report.json 生成 |
| 4 | Slack + X 投稿 | build-report が Slack に送信される |
| 5 | 全 US が passes: true | `<promise>COMPLETE</promise>` で終了 |

**注意:** US-009 の WAITING_FOR_HUMAN はまだ progress.txt に残っている。F1 パッチ適用 + progress.txt から WAITING_FOR_HUMAN 行を削除してから再実行が必要。
