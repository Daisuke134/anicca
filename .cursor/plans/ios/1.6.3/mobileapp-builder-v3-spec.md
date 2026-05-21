# mobileapp-builder v3 — App Rejection 防止 + Self-Improvement ループ

**作成日:** 2026-02-25
**ステータス:** 確認済み・実装完了

---

## 概要（What & Why）

Daily Dhamma と Thankful が連続リジェクット。原因を CLI で実機確認した上で SKILL.md を修正する。

### リジェクット原因（確認済み）

| アプリ | Guideline | 原因 | CLI で直せるか |
|--------|-----------|------|--------------|
| Daily Dhamma | **2.1** | IAP が submit されていなかった | ✅ `asc subscriptions submit` |
| Thankful | **2.1** | IAP が submit されていなかった | ✅ `asc subscriptions submit` |
| Thankful | **3.1.2** | App Description に Terms URL がなかった | ✅ `asc localizations upload` |

### 重要な確認事実

| 確認項目 | 結果 |
|---------|------|
| Thankful SettingsView | Terms + Privacy リンクあり ✅（コード変更不要） |
| Thankful PaywallView | Terms/Privacy リンクなし（**Paywall には不要** — Settings にあれば OK） |
| Daily Dhamma paywall.tsx | Terms + Privacy リンクあり ✅（コード変更不要） |
| `asc subscriptions submit` コマンド | 存在する ✅ CLI で IAP submit 可能 |
| `asc localizations upload` | App Description 更新可能 ✅ |

---

## 受け入れ条件

| # | 条件 | 結果 |
|---|------|------|
| AC1 | PHASE 9 Step 4（メタデータ）に App Description へ Terms URL を追加する手順がある | ✅ SKILL.md に追記 |
| AC2 | PHASE 12 の前に `asc subscriptions submit` を実行する手順がある | ✅ PHASE 11.6 に追記 |
| AC3 | SELF-IMPROVEMENT RULE が SKILL.md に存在する | ✅ SKILL.md に追記 |
| AC4 | Thankful が再提出された | ✅ |
| AC5 | Daily Dhamma が再提出された | ✅（IAP 既に submit 済み） |

---

## SKILL.md への変更（2箇所）

### 変更 1: PHASE 9 Step 4 メタデータ — App Description に Terms URL を追記

**App Description の末尾に以下を追加する（Guideline 3.1.2 — App Store メタデータ要件）:**

```bash
# EN description に Terms URL を追記
CURRENT_DESC=$(asc localizations list --version "<VERSION_ID>" --output json | \
  python3 -c "import sys,json;d=json.load(sys.stdin);[print(loc['attributes']['description']) for loc in d['data'] if loc['attributes']['locale']=='en-US']")

# localizations/en-US/description.txt に保存して upload
mkdir -p /tmp/locs/en-US
echo "$CURRENT_DESC

Terms of Use: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/" > /tmp/locs/en-US/description.txt

asc localizations upload --version "<VERSION_ID>" --path /tmp/locs
```

### 変更 2: PHASE 11.6 — IAP SUBMIT GATE（新規フェーズ）

**`asc subscriptions submit` で CLI から直接 submit できる（手動不要）。**

```bash
### PHASE 11.6: IAP SUBMIT（Guideline 2.1 — CLI で全自動）

# Monthly と Annual を submit for review
asc subscriptions submit --subscription-id "<MONTHLY_ID>" --confirm
asc subscriptions submit --subscription-id "<ANNUAL_ID>" --confirm

# 確認: state = WAITING_FOR_REVIEW になれば OK
asc subscriptions get --id "<MONTHLY_ID>" | grep state
asc subscriptions get --id "<ANNUAL_ID>" | grep state
```

### 変更 3: SELF-IMPROVEMENT RULE（新規セクション）

```markdown
## SELF-IMPROVEMENT RULE

**失敗 → 即 SKILL.md に正しい CLI コマンドを書き込む → git push → 次フェーズへの移行は書き込み後のみ許可**

| トリガー | アクション |
|---------|-----------|
| Apple リジェクット | 原因分析 → 該当 PHASE に修正ルール追記 → git push |
| CLI エラー | 正しいコマンドを確認して即修正 → git push |
| 「手動が必要」と思った | まず `--help` で確認する。CLI にある可能性が高い |

**禁止:**
- 「手動が必要」と確認せずに言う → 必ず CLI --help で確認してから判断
- 「次は気をつける」だけで終わらせる → SKILL.md に具体的なコマンドを追記
```

---

## 境界

| やらないこと | 理由 |
|-------------|------|
| Thankful PaywallView へのリンク追加 | Settings にあれば OK（Guideline 3.1.2 要件を満たす） |
| コード変更・再ビルド | 不要。App Description 更新 + IAP submit のみ |
| Daily Dhamma コード変更 | paywall.tsx に Terms/Privacy あり、IAP submit 済み |
