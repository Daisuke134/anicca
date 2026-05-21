# iOS Legal / Privacy / ATT - Round 2 実装トラッカー（迷子防止）

| 項目 | 値 |
|---|---|
| Worktree | `/workspace/worktrees/anicca-proactive-legal` |
| ブランチ | `cursor/anicca-ios-legal-update-e2d1` |
| 参照Spec | `.cursor/plans/proactive/2026-01-26-ios-legal-update-and-att-decision-spec.md` |
| このファイルの目的 | 「次にやること」と「完了条件」を固定し、実装中に迷子/ズレを防ぐ |

---

## 現状スナップショット（2026-01-26 / このブランチ時点）

| # | 指摘 | 現状 | 重要度 | メモ |
|---:|---|---|---|---|
| 1 | Privacyにマイク説明が無いのに Info.plist に残ってる | `NSMicrophoneUsageDescription` + 文言 + `MicrophonePermissionStepView.swift` が残存 | 高 | 「使わないなら消す」に寄せる |
| 2 | ATT が「表示前に1回消費」され復旧性がない | `AppState.maybePresentATTPromptAfterNudge()` で `attPromptPresentedKey` を先に `true` 保存 | 最重要 | 表示失敗で二度と出ないリスク |
| 3 | `Config.swift` に `mobile/daily_metrics` が残ってる | `AppConfig.dailyMetricsURL` が残存 | 低 | 「完全削除」主張の整合性 |
| 4 | Netlify の “no content change” | `apps/landing` に変更はある | 低 | それでも出るなら Netlify 側 ignore 設定が濃厚 |

---

## 決定ログ（Round 2）

| # | 決め | 理由 | 備考 |
|---:|---|---|---|
| 1 | **マイクは使っていない前提で完全削除**（権限宣言/文言/導線/参照） | 「権限文字列がある＝ユーザーが不安」かつPrivacy本文と矛盾 | カメラは現状「使わない」文言なので残しても良いが、Privacyに1行追記する案あり（今回は“削除”が優先） |
| 2 | **ATTの `attPromptPresentedKey` 保存タイミングを後ろへ** | 表示失敗時の回復性（再表示可能性）を確保 | 保存は「画面 `onAppear`」または「`requestTrackingAuthorization` を呼ぶ瞬間」 |
| 3 | **`mobile/daily_metrics` 残骸は未使用なら削除** | 「完全削除」方針を強くする | 参照が0件なら削除一択 |
| 4 | **push後に Deploy Preview が更新されることを確認** | 視覚確認できる状態にする | “no content change” が続くなら Netlify ignore rule を見直す |

---

## Specとのズレ（明示して迷子防止）

| 項目 | Spec側の記述 | Round 2 の実施方針 |
|---|---|---|
| ATTの扱い | Spec内に「ATTは出さない」方針が存在 | **今回は「ATTを出す/出さない」の議論は止めて**、まず **“キー保存タイミング後ろ倒し”** の回復性を実装する（レビュー指摘の修正） |
| 目的 | 法務整合とATT意思決定 | Round 2 は「レビュー指摘の整合修正」に限定 |

---

## 実装チェックリスト（この順で進める）

### A. マイク完全削除

| # | ToDo | 触るファイル候補 | 完了条件 |
|---:|---|---|---|
| A1 | `Info.plist` から `NSMicrophoneUsageDescription` を削除 | `aniccaios/aniccaios/Info.plist` | ビルド設定/差分でキーが消えている |
| A2 | `InfoPlist.strings`（EN/JA）からマイク文言を削除 | `aniccaios/aniccaios/Resources/*/InfoPlist.strings` | マイクキーが存在しない |
| A3 | マイク許可導線（未使用View含む）を削除 | `Onboarding/MicrophonePermissionStepView.swift` ほか | リポジトリ内にマイク許可導線が残らない（検索で0件） |
| A4 | `project.pbxproj` にマイク関連ファイル参照が残ってないか確認 | `aniccaios/aniccaios.xcodeproj/project.pbxproj` | ビルドに影響する参照が残ってない |

### B. ATT “回復性” 修正

| # | ToDo | 触るファイル候補 | 完了条件 |
|---:|---|---|---|
| B1 | `attPromptPresentedKey` を「表示前に保存」しない | `aniccaios/aniccaios/AppState.swift` | 表示フラグを立てる前に永続化しない |
| B2 | 永続化のタイミングを後ろへ | `ATTPermissionStepView.swift` / `AppState.swift` | `onAppear` か `request...` 実行時に保存される |
| B3 | “OS側で既に回答済み” の場合の扱いを整理 | `AppState.swift` | notDetermined以外は適切にスキップし、必要なら保存 |

### C. `daily_metrics` 残骸削除

| # | ToDo | 触るファイル候補 | 完了条件 |
|---:|---|---|---|
| C1 | `AppConfig.dailyMetricsURL` の参照を検索 | `aniccaios/aniccaios/Config.swift` ほか | 参照0件が確認できる |
| C2 | 参照0件なら定義を削除 | `Config.swift` | `dailyMetricsURL` が存在しない |

### D. Deploy Preview 確認

| # | ToDo | 対象 | 完了条件 |
|---:|---|---|---|
| D1 | `apps/landing` 配下に変更が含まれることを確認 | `git diff origin/dev..HEAD` | `apps/landing/**` が差分に出る |
| D2 | push後、Deploy Preview が更新される | Netlify / GitHub Checks | Preview URL で更新内容が見える |

---

## 受け入れ条件（Round 2）

| # | 条件 | 判定方法 |
|---:|---|---|
| 1 | マイク権限宣言/文言/導線が repo から消えている | `NSMicrophoneUsageDescription` / microphone / MicrophonePermission の検索が0件 |
| 2 | ATTが「表示失敗しても二度と出ない」状態になっていない | `attPromptPresentedKey` を表示前に保存していないことをコードで確認 |
| 3 | `mobile/daily_metrics` 残骸が消えている | `Config.swift` から該当定義が消えている |
| 4 | Deploy Preview が視覚確認できる | Preview URL で内容が確認できる |

---

## 実装後の確認コマンド（人間用）

| # | コマンド | 目的 |
|---:|---|---|
| 1 | `git diff origin/dev..HEAD` | 変更範囲の最終確認 |
| 2 | `rg -n "NSMicrophoneUsageDescription|microphone|MicrophonePermission" aniccaios/aniccaios` | マイク残骸が0件か |
| 3 | `rg -n "attPromptPresentedKey" aniccaios/aniccaios` | 永続化タイミングの確認 |

