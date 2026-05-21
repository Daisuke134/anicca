# Spec: iOS ATT（App Tracking Transparency）完全削除（SKAN前提）

## 概要（What）

本Specは、iOSアプリから **ATTに関する導線・画面・OSリクエスト・永続化キー・文言・関連イベント**を完全削除し、
ユーザー体験として **ATTフルスクリーンも、iOS公式ATTポップアップも一切出ない**状態にする。

対象は iOSアプリ本体と、必要であればWebのPrivacy Policy（EN/JA）のATT/IDFA言及整合まで。

---

## 背景（Why）

| 観点 | 現状の問題 | なぜ直すか（狙い） |
|---|---|---|
| UX | NudgeCardの価値体験直後に「ATT説明フルスクリーン」→「iOS公式ATTポップアップ」が発生し得る | 価値体験の直後に“追跡許可”を挟むのは離脱要因になりやすい |
| 法務/安心 | 追跡・広告識別子の説明が出るだけで不安を誘発しやすい | “使わないなら消す”方針（不要な権限説明/導線を残さない）に一致 |
| 計測 | 広告計測は **SKAN中心で成立しうる**（ただし粒度は粗い） | ATT取得のUXコストに見合わない。まずSKAN運用で回す |

補足（前提）：
- SKANは広告起点のアトリビューションを主目的とする（ユーザー識別は返さない）。
- 「ユーザー単位で精密に追う」用途は諦め、**集計ベース**で広告を回す。

---

## スコープ（Scope）

| 区分 | 含む | 含まない |
|---|---|---|
| iOS | ATT導線/画面/OSリクエスト/永続化/Info.plist文言/i18n/ATT関連イベント | SKANのCV設計、広告運用戦略、SDKの設定変更（別Spec） |
| Web | Privacy PolicyのATT/IDFA言及整合（EN/JA） | UI/レイアウト変更（禁止） |

---

## As-Is（現状）

| 項目 | 現状 |
|---|---|
| 表示タイミング | オンボ完了後にNudgeCard終了時、ATT説明フルスクリーンが出る場合がある |
| 画面 | `ATTPermissionStepView` が `fullScreenCover` で表示される |
| OSポップアップ | `ATTrackingManager.requestTrackingAuthorization` を呼ぶことで iOS公式ATTダイアログが出る |
| 永続化 | `attPromptPresentedKey`（例: `com.anicca.attPromptPresented`）で「表示済み」を保持する実装が存在しうる |
| Info.plist | `NSUserTrackingUsageDescription` が存在しうる |
| i18n | `onboarding_att_*` 等のキーが `Localizable.strings`（EN/JA）に存在しうる |
| Analytics | `onboardingATTViewed` 等のイベントが存在しうる |

---

## To-Be（変更後）

| 項目 | To-Be（正） |
|---|---|
| UI | **ATT説明フルスクリーンを表示しない** |
| OS | **`requestTrackingAuthorization` を呼ばない**（よってATTポップアップも出ない） |
| 永続化 | ATT表示済みキー/状態フラグ/提示関数を削除 |
| Info.plist | `NSUserTrackingUsageDescription` を削除 |
| i18n | ATT関連文言キーをEN/JA両方から同時削除（CIキー整合ガード対応） |
| Analytics | ATT関連イベントを削除（到達不能でも残さない） |
| Legal（Web） | Privacy Policy内のATT/IDFAの言及を「ATTを出さない」前提に整合（必要に応じて削除/修正） |

---

## 実装方針（ファイル別）

| 変更カテゴリ | ファイル | 変更内容 |
|---|---|---|
| iOS 導線削除 | `aniccaios/aniccaios/MainTabView.swift` | ATT表示の `fullScreenCover` を削除 |
| iOS 状態/キー削除 | `aniccaios/aniccaios/AppState.swift` | `attPromptPresentedKey` / `isPresentingATTPrompt` / 提示関数（例: `maybePresentATTPromptAfterNudge()`）/ 付随関数を削除。呼び出し元も削除 |
| iOS 画面削除 | `aniccaios/aniccaios/Onboarding/ATTPermissionStepView.swift` | ファイル削除（参照が残らないようにする） |
| iOS Info.plist | `aniccaios/aniccaios/Info.plist` | `NSUserTrackingUsageDescription` を削除 |
| iOS Analytics | `aniccaios/aniccaios/Services/AnalyticsManager.swift`（＋イベント定義のある箇所） | ATT関連イベント定義/参照を削除 |
| iOS i18n | `aniccaios/aniccaios/Resources/en.lproj/Localizable.strings` / `ja.lproj/Localizable.strings` | `onboarding_att_*` 等をEN/JA両方から同時削除 |
| Web Legal（必要時） | `apps/landing/app/privacy/en/page.tsx` / `ja/page.tsx` | ATT/IDFAの文言を「ATTを出さない」前提へ整合（文面のみ） |

---

## 受け入れ条件（Acceptance Criteria）

| # | 条件 | 判定方法 |
|---:|---|---|
| 1 | NudgeCard後にATT説明フルスクリーンが出ない | `fullScreenCover`/導線が存在しない（検索） |
| 2 | iOS公式ATTポップアップが一切出ない | `requestTrackingAuthorization` が0件（検索） |
| 3 | `NSUserTrackingUsageDescription` が存在しない | `Info.plist` のキー削除を確認 |
| 4 | ATT関連の永続化キー/状態が存在しない | `attPromptPresentedKey` 等が0件（検索） |
| 5 | EN/JAのATT文言キーが両方から削除され、キー整合が壊れていない | EN/JA同時削除 + CIキー整合ガードに通る |
| 6 | Web PrivacyがATT/IDFA前提になっていない（必要な場合のみ） | EN/JAページ内容を確認 |

---

## To-Beチェックリスト（漏れ防止）

| # | To-Be | 状態 |
|---:|---|---|
| 1 | iOS: ATTフルスクリーン導線削除 | ☐ |
| 2 | iOS: `requestTrackingAuthorization` 呼び出し削除 | ☐ |
| 3 | iOS: ATT状態/永続化キー削除 | ☐ |
| 4 | iOS: `NSUserTrackingUsageDescription` 削除 | ☐ |
| 5 | iOS: ATT i18nキー削除（EN/JA同時） | ☐ |
| 6 | iOS: ATTイベント削除 | ☐ |
| 7 | Web: Privacy文面のATT/IDFA言及整合（必要時） | ☐ |

---

## テストマトリクス（変更範囲だけ）

| # | To-Be | テスト/確認 | カバー |
|---:|---|---|---|
| 1 | 1,2,3,4 | `rg -n "ATTrackingManager|requestTrackingAuthorization|NSUserTrackingUsageDescription|attPromptPresentedKey|isPresentingATTPrompt|ATTPermissionStepView" aniccaios/aniccaios` | ☐ |
| 2 | 5 | `rg -n "onboarding_att_" aniccaios/aniccaios/Resources`（EN/JAとも0件） | ☐ |
| 3 | 6 | `rg -n "onboardingATT|ATTViewed|ATTPrompt" aniccaios/aniccaios`（イベントが0件） | ☐ |
| 4 | 7 | `cd apps/landing && npm ci && npm run build`（文面変更をした場合のみ） | ☐ |

---

## Skills / Sub-agents

| ステージ | 使用するもの | 用途 |
|---|---|---|
| Specレビュー | `/codex-review` | 抜け漏れ/矛盾/やり忘れの検出 |
| 実装後レビュー | Subagent: code-quality-reviewer | 削除漏れ・参照漏れの最終チェック |

---

## 境界（Boundaries）

| 種別 | 内容 |
|---|---|
| UI禁止 | レイアウト/色/フォント/余白の変更は禁止（削除・文面整合のみ） |
| 触るファイル | 「実装方針（ファイル別）」に列挙したもののみ |
| 触らない | 課金/通知/Nudgeロジックの仕様変更（ATT削除に直接関係しないもの） |

---

## 実行手順（実装フェーズ）

| # | 手順 | コマンド |
|---:|---|---|
| 1 | iOS参照漏れチェック | `rg -n "ATTrackingManager|requestTrackingAuthorization|NSUserTrackingUsageDescription|attPromptPresentedKey|isPresentingATTPrompt|ATTPermissionStepView|onboarding_att_" aniccaios/aniccaios` |
| 2 | Web build（必要時） | `cd apps/landing && npm ci && npm run build` |

