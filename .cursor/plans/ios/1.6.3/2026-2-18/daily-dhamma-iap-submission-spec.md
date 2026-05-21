# Daily Dhamma - IAP Submission Fix Spec

## 開発環境

| 項目 | 値 |
|------|-----|
| **アプリパス** | `/Users/cbns03/Downloads/anicca-project/daily-apps/daily-dhamma-app` |
| **ブランチ** | `dev` |
| **作業状態** | 実装中 |

---

## 1. 概要（What & Why）

### What

Apple Guideline 2.1 (App Completeness) 違反により v1.0 が Reject された。
原因: Annual/Monthly サブスクリプションが ASC 上で `MISSING_METADATA` 状態のまま提出された。
Apple がレビュー中に IAP を検証できず、Reject。

### Why

IAP を App Store 審査に通すには:
1. **ASC メタデータ完備**: Display Name / Description / App Review Screenshot が **en ロケールで入力済み**（Apple 審査の blocking 条件はen）。プロダクト方針として **ja も同時投入**するが、審査通過に必要な最小条件は en のみ。
2. **Price 設定**: Subscription に価格ティアが設定・有効化済み
3. **Ready to Submit 状態**: バイナリ提出時に IAP が「Ready to Submit」である必要あり
4. **IAP の Version 紐付け**: 提出する App Version に Annual/Monthly の両 IAP が Attached されている必要あり（この紐付けがなかったことが今回のリジェクト直接原因）
5. **コードの可観測性**: Maestro E2E で価格表示を検証できるよう `testID` が必要

---

## 2. 受け入れ条件

> **ロケールポリシー（全 AC 共通）**: **en メタデータ + 価格 + Screenshot = Blocking**（これが未完了なら審査 Reject 確定）。**ja = Policy（non-blocking、今回同時投入するが審査通過条件ではない）**。Section 6・Step 7 も同一ポリシーに従う。

| # | 条件 | 検証方法 | 対応 E2E |
|---|------|---------|---------|
| AC-0 | paywall 画面が正常に開く | Maestro E2E (E-P1) | E-P1 |
| AC-1 | ASC で Annual サブスクが "Ready to Submit" 状態（enメタデータ+価格+Screenshot = Blocking、審査通過必須） | `asc subscriptions list` で state 確認 | — |
| AC-2 | ASC で Monthly サブスクが "Ready to Submit" 状態（enメタデータ+価格+Screenshot = Blocking、審査通過必須） | `asc subscriptions list` で state 確認 | — |
| AC-3 | Annual/Monthly の価格ティアが設定・有効化済み（enメタデータ+価格+Screenshot = Blocking、審査通過必須） | ASC GUI で Price に数値表示あること | — |
| AC-4a | paywall 画面で Monthly の価格文字列が表示される | Maestro E2E (E-P2) | E-P2 |
| AC-4b | paywall 画面で Annual の価格文字列が表示される | Maestro E2E (E-P3) | E-P3 |
| AC-5 | 「登録する」ボタンがタップ可能 | Maestro E2E (E-P4) | E-P4 |
| AC-6 | paywallUtils 全単体テスト PASS | `npm test -- --testPathPattern=paywallUtils` | — |
| AC-7 | 既存テスト 40 件 PASS (regression なし) | `npm test` | — |
| AC-8 | 提出する App Version に Annual/Monthly IAP が Attached 済み（enメタデータ+価格+Screenshot = Blocking、審査通過必須）。Submit 直前 Step 9 で最終確認 | Step 9 で `asc versions list` + ASC GUI 確認 | — |

---

## 3. As-Is / To-Be

### As-Is（問題）

| 項目 | 現状 |
|------|------|
| Annual (6759388949) | MISSING_METADATA — Display Name/Description/Screenshot なし、価格未設定 |
| Monthly (6759389150) | MISSING_METADATA — Display Name/Description/Screenshot なし、価格未設定 |
| App Version | IAP が Attached されていない（=リジェクト直接原因） |
| paywall.tsx | パッケージ検索ロジックがコンポーネント内にインライン。`testID` なし |
| Maestro テスト | `maestro/` ディレクトリ自体が存在しない |

### To-Be（修正後）

| 項目 | 修正後 |
|------|------|
| Annual (6759388949) | Ready to Submit — en/ja メタデータ + 価格 + Screenshot 完備、App Version に Attached |
| Monthly (6759389150) | Ready to Submit — en/ja メタデータ + 価格 + Screenshot 完備、App Version に Attached |
| `utils/paywallUtils.ts` (新規) | `findMonthlyPackage` / `findYearlyPackage` / `formatPackagePrice` を純関数として公開 |
| `paywall.tsx` | utils を使うようリファクタ。各プランボタンと CTA に `testID` 追加 |
| `__tests__/paywallUtils.test.ts` (新規) | 7 件の単体テスト |
| `maestro/paywall/01-paywall-prices-visible.yaml` (新規) | Paywall 価格表示・ボタン動作 E2E |

### `utils/paywallUtils.ts` シグネチャ

```typescript
import { PurchasesPackage } from 'react-native-purchases';

export function findMonthlyPackage(
  packages: PurchasesPackage[]
): PurchasesPackage | undefined;

export function findYearlyPackage(
  packages: PurchasesPackage[]
): PurchasesPackage | undefined;

export function formatPackagePrice(
  pkg: PurchasesPackage | undefined
): string;
```

### `paywall.tsx` の testID 追加箇所

| UI要素 | testID | E2E 検証対象 |
|--------|--------|------------|
| Monthly プランボタン | `paywall_plan_monthly` | E-P2 |
| Yearly プランボタン | `paywall_plan_yearly` | E-P3 |
| 登録する（CTA）ボタン | `paywall_cta` | E-P4 |
| 無料で続けるボタン | `paywall_skip` | スコープ外（後回し） |
| 購入を復元ボタン | `paywall_restore` | スコープ外（後回し） |

> 注: `paywall_skip`/`paywall_restore` の testID は追加するが、今回 Maestro で検証しない。機能テストは手動確認で代替。

---

## 4. テストマトリックス

### 単体テスト (`__tests__/paywallUtils.test.ts`)

| # | テスト名 | カバー |
|---|----------|--------|
| T-P1 | `findMonthlyPackage` finds `monthly` identifier | 正常系 |
| T-P2 | `findMonthlyPackage` finds `$rc_monthly` identifier | RC デフォルト識別子 |
| T-P3 | `findYearlyPackage` finds `annual` identifier | 正常系 |
| T-P4 | `findYearlyPackage` finds `$rc_annual` identifier | RC デフォルト識別子 |
| T-P5 | `findMonthlyPackage` returns undefined when packages empty | 空リスト |
| T-P6 | `formatPackagePrice` returns priceString when pkg exists | 正常系 |
| T-P7 | `formatPackagePrice` returns empty string when pkg undefined | undefined |

### Maestro E2E (`maestro/paywall/01-paywall-prices-visible.yaml`)

| # | シナリオ | 検証内容 | 対応 AC |
|---|---------|---------|---------|
| E-P1 | paywall 画面が開く | paywall.title テキストが表示される | AC-0 |
| E-P2 | Monthly 価格が表示される | `testID=paywall_plan_monthly` 内の priceString テキストが空でない | AC-4a |
| E-P3 | Yearly 価格が表示される | `testID=paywall_plan_yearly` 内の priceString テキストが空でない | AC-4b |
| E-P4 | CTA ボタンがタップ可能 | `testID=paywall_cta` をタップ → loading 状態または購入ダイアログが表示される | AC-5 |

---

## 5. 境界（やらないこと）

| 項目 | 理由 |
|------|------|
| 他画面の `testID` 追加 | スコープ外 |
| de/es/fr/pt-BR ロケールの IAP メタデータ | 審査 blocking 条件は en のみ。ja は今回同時投入。その他は後のリリースで対応 |
| RevenueCatProvider の修正 | 動作上問題なし |
| 購入フロー実機テスト | Sandbox テストは Maestro 対象外（Apple 制限）。手動確認で代替 |
| `paywall_skip` / `paywall_restore` の Maestro E2E | testID は追加するが検証は後回し |
| EAS Build 番号の指定 | アーカイブ後 ASC で自動付番 |

---

## 6. ユーザー GUI 作業（実装前）

> **ロケールポリシー（全 AC 共通）**: **en メタデータ + 価格 + Screenshot = Blocking**（これが未完了なら審査 Reject 確定）。**ja = Policy（non-blocking、今回同時投入するが審査通過条件ではない）**。Section 6・Step 7 も同一ポリシーに従う。

### 必須 (Blocking) — en ロケール + 価格 + 状態

| # | タスク | URL / 場所 | 確認項目 |
|---|--------|-----------|---------|
| B-1 | Annual — **英語** Display Name 入力 | ASC → Daily Dhamma → Subscriptions → dhamma pro → Annual → Localizations → English | "Dhamma Pro Annual" 等 |
| B-2 | Annual — **英語** Description 入力 | 同上 | 40文字程度の説明文 |
| B-3 | Annual — 価格ティア設定 | Annual → Subscription Prices | Price が "$XX.XX/year" 等で表示される |
| B-4 | Annual — App Review Screenshot 追加 | Annual → App Review Information | paywall iOS スクリーンショット（Step 6 で取得） |
| B-5 | Monthly — **英語** Display Name / Description / 価格 / Screenshot 入力 | Monthly と同手順 | Price が "$X.XX/month" 等で表示される |
| B-6 | 両サブスクの状態確認 | `asc subscriptions list --group 21940570 --output table` | state: `READY_TO_SUBMIT` |

### 同時投入 (Policy) — ja ロケール（non-blocking）

| # | タスク | URL / 場所 | 確認項目 |
|---|--------|-----------|---------|
| P-1 | Annual — **日本語** Display Name 入力 | Annual → Localizations → Japanese | "ダンマ・プロ 年額" 等 |
| P-2 | Annual — **日本語** Description 入力 | 同上 | 説明文 |
| P-3 | Monthly — **日本語** Display Name / Description 入力 | Monthly と同手順 | — |

---

## 7. ASC サブスクリプション情報（参照）

| 項目 | 値 |
|------|-----|
| ASC App ID | `6757726663` |
| Bundle ID | `com.dailydhamma.app` |
| Subscription Group | dhamma pro (ID: `21940570`) |
| Annual Product ID | `com.dailydhamma.app.premium.yearly` (ASC ID: `6759388949`) |
| Monthly Product ID | `com.dailydhamma.app.premium.monthly` (ASC ID: `6759389150`) |
| RC Entitlement | `premium` |
| RC Monthly Identifier | `monthly` または `$rc_monthly` |
| RC Annual Identifier | `annual` または `$rc_annual` |

---

## 8. 実行手順

### Step 1: 単体テスト作成（RED）

```bash
cd daily-apps/daily-dhamma-app
# __tests__/paywallUtils.test.ts を作成（全 7 件 FAIL の状態で確認）
npm test -- --testPathPattern=paywallUtils
```

### Step 2: `utils/paywallUtils.ts` 実装（GREEN）

```bash
# utils/paywallUtils.ts を作成し全テスト PASS にする
npm test -- --testPathPattern=paywallUtils
```

### Step 3: `paywall.tsx` をリファクタ + `testID` 追加

```bash
# paywall.tsx を paywallUtils を使うよう更新 + testID を追加
npm test  # 全テスト 47 件 PASS 確認
```

### Step 4: Maestro ディレクトリ作成 & E2E YAML 作成

```bash
mkdir -p daily-apps/daily-dhamma-app/maestro/paywall
# maestro/paywall/01-paywall-prices-visible.yaml を作成
```

### Step 5: Maestro E2E 実行（MCP 経由）

```
mcp__maestro__list_devices
mcp__maestro__launch_app (appId: com.dailydhamma.app)
mcp__maestro__inspect_view_hierarchy  # 実際のテキスト・ID を確認
mcp__maestro__run_flow_files (flow: maestro/paywall/01-paywall-prices-visible.yaml)
mcp__maestro__take_screenshot  # 結果確認
```

### Step 6: App Review スクリーンショット取得

```bash
# Maestro でpaywall表示状態のスクリーンショット取得
mcp__maestro__take_screenshot
# 保存先: maestro/screenshots/paywall-app-review.png
# このPNGファイルを手順7 の App Review Screenshot としてASCにアップロード
```

### Step 7: ASC メタデータ登録（asc-subscription-localization スキル使用）

> **ロケールポリシー（全 AC 共通）**: **en メタデータ + 価格 + Screenshot = Blocking**（これが未完了なら審査 Reject 確定）。**ja = Policy（non-blocking、今回同時投入するが審査通過条件ではない）**。Section 6・Step 7 も同一ポリシーに従う。

```bash
# Annual / Monthly の en メタデータを asc CLI で登録（Blocking）
# ja メタデータは Policy として同時登録（non-blocking）
asc subscriptions list --group 21940570 --output table
# → en + 価格 + Screenshot 完備で READY_TO_SUBMIT になったことを確認（GUI作業 B-1〜B-6 参照）
```

### Step 8: EAS Build #18

```bash
cd daily-apps/daily-dhamma-app
eas build --platform ios --non-interactive
```

### Step 9: IAP Attach 確認（Submit 直前最終ゲート）

> **これが AC-8 の最終ゲート確認。Submit より前に必ず実行すること。**

```bash
# App Version と IAP の紐付けを Submit 直前に再確認
asc versions list --app 6757726663 --output table
# ASC GUI: App Store → バージョン → In-App Purchases セクションで Annual/Monthly 両 IAP が表示されるか確認
# 表示されない場合: 各 IAP ページ右上の "Submit with Version" または Add to Version で紐付け → 再確認
# PASS 条件: 両 IAP が表示され、各 state が READY_TO_SUBMIT
```

### Step 10: App Store 再提出

```bash
# asc-release-flow スキルを使用（Step 9 PASS 後のみ実行）
asc submit --build <BUILD_ID> --app 6757726663
# 提出後: asc versions list --app 6757726663 で WAITING_FOR_REVIEW を確認
```

---

## 9. E2E 判定

| 項目 | 値 |
|------|-----|
| UI変更 | あり（testID 追加は非表示変更、UI 構造は同じ） |
| 新画面 | なし |
| 新ボタン/操作 | なし（既存 UI に `testID` 追加のみ） |
| 結論 | Maestro E2E テスト: **必要**（paywall 価格表示・CTA ボタンを検証） |

---

## 10. Apple 審査リジェクト根拠（参考）

> **Guideline 2.1 – App Completeness**
> "We were unable to complete the review of your app because we were unable to test in-app purchases. We found that in-app purchases are included in your app, but were not submitted."
>
> 引用: Apple 審査チームからの Reject メール (Submission ID: f7957180)

**修正根拠（Apple Developer Documentation）:**
- In-App Purchases は提出前に App Review Information（スクリーンショット含む）を入力し "Ready to Submit" 状態にする必要がある
- さらに提出する App Version に IAP を Attach（紐付け）する必要がある
- 参照: developer.apple.com/in-app-purchase/

---

最終更新: 2026-02-22 (Codex iter 6 反映)
