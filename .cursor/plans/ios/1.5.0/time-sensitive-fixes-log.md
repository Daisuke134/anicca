# Time Sensitive & ScreenTime Cleanup — 修正ログ

## ブランチ情報

| 項目 | 値 |
|------|-----|
| ワークツリー | `/Users/cbns03/Downloads/anicca-time-sensitive` |
| ブランチ | `feature/time-sensitive-and-screentime-cleanup` |
| ベース | `dev` |
| Spec | `time-sensitive-and-screentime-cleanup-spec.md` |

## 実装変更（Spec準拠）

### 1. Time Sensitive 通知有効化

| ファイル | 変更内容 |
|---------|---------|
| `NotificationScheduler.swift:42-46` | `requestAuthorization` に `.timeSensitive` 追加（iOS 15+ guard付き） |
| `NotificationScheduler.swift:116-118` | `interruptionLevel` を条件付き `.timeSensitive` に変更（`timeSensitiveSetting == .enabled` の場合のみ、フォールバック `.active`） |
| `ProblemNotificationScheduler.swift:43-49` | `timeSensitiveSetting == .disabled` のログ警告追加 |
| `ProblemNotificationScheduler.swift:183-184` | テスト通知の `interruptionLevel` を `.active` に固定（デバッグ用のため `.timeSensitive` は不要） |
| `ProblemNotificationScheduler.swift:242-244` | Problem Nudge の `interruptionLevel` を条件付き `.timeSensitive` に変更（`timeSensitiveSetting == .enabled` の場合のみ、フォールバック `.active`） |

### 2. ScreenTimeReport Extension 完全削除

| ファイル | 変更内容 |
|---------|---------|
| `AniccaScreenTimeReport/` (7ファイル) | ディレクトリごと削除 |
| `aniccaios/Shared/ScreenTimeSharedStore.swift` | 削除 |
| `project.pbxproj` | 関連参照4箇所削除（FileReference, RootGroup, mainGroup, Products） |

## レビュー後の追加修正

### 3. テストバグ修正（既存バグ）

| ファイル | 変更内容 |
|---------|---------|
| `ProblemNotificationSchedulerTests.swift:85-86` | `test_llmNudge_noTimeShift` の期待値を `90` → `30` に修正 |

**原因**: `calculateNewShift(currentShift: 0, consecutiveIgnored: 5)` は `min(0 + 30, 120) = 30` を返す。テストが単一呼び出しと累積呼び出しを混同していた。devブランチでも同じ失敗が再現する既存バグ。

### 4. 孤立ビルドフェーズ削除

| ファイル | 変更内容 |
|---------|---------|
| `project.pbxproj` | `Embed ExtensionKit Extensions` ビルドフェーズ定義を削除 |
| `project.pbxproj` | `buildPhases` 配列からの参照を削除 |

**原因**: ScreenTimeReport Extension 削除時に残った孤立参照。ビルドには影響しないがプロジェクト構造の整合性のため削除。

### 5. `self.center` プロパティ統一

| ファイル | 変更内容 |
|---------|---------|
| `ProblemNotificationScheduler.swift:43` | `UNUserNotificationCenter.current()` → `self.center` に変更 |

**理由**: クラス内に `private let center = UNUserNotificationCenter.current()` プロパティが既に定義されている。新規追加コードもこれを使うべき。

### 6. 孤立ローカライズ文字列削除

| ファイル | 削除キー |
|---------|---------|
| `en.lproj/Localizable.strings` | `"profile_toggle_screen_time" = "Screen Time";` |
| `ja.lproj/Localizable.strings` | `"profile_toggle_screen_time" = "スクリーンタイム";` |
| `es.lproj/Localizable.strings` | `"profile_toggle_screen_time" = "Screen Time";` |
| `fr.lproj/Localizable.strings` | `"profile_toggle_screen_time" = "Screen Time";` |
| `de.lproj/Localizable.strings` | `"profile_toggle_screen_time" = "Screen Time";` |
| `pt-BR.lproj/Localizable.strings` | `"profile_toggle_screen_time" = "Screen Time";` |

**理由**: ScreenTime機能削除に伴い、参照元がなくなった孤立文字列。

## Time Sensitive 利用方針

### 対象通知

| 通知タイプ | interruptionLevel | 条件 |
|-----------|-------------------|------|
| Server-driven Nudge（即時） | `.timeSensitive` | `timeSensitiveSetting == .enabled` の場合のみ |
| Problem Nudge（スケジュール済み） | `.timeSensitive` | `timeSensitiveSetting == .enabled` の場合のみ |
| テスト通知（デバッグ用） | `.active` | 常に `.active`（Focus貫通不要） |
| 全通知共通フォールバック | `.active` | `timeSensitiveSetting != .enabled` の場合 |

### ユーザー設定の扱い

- `requestAuthorization` 時に `.timeSensitive` オプションを含めて許可を求める（iOS 15+）
- 実際の通知発火時は `center.notificationSettings().timeSensitiveSetting` を毎回チェック
- ユーザーが設定アプリで Time Sensitive を無効にした場合、自動的に `.active` にフォールバック
- 既存ユーザー（v1.4.0以前で許可済み）は次回 `requestAuthorization` 呼び出し時に追加許可が求められる

### App Review 向け申請理由

AniccaはAI行動変容アプリであり、ユーザーが登録した「苦しみ」（夜更かし、先延ばし等）に対して最適なタイミングでNudge通知を送信する。Time Sensitive通知が必要な理由：

1. **夜更かし問題（staying_up_late）**: 深夜のFocusモード中にNudgeを届ける必要がある
2. **起床困難（cant_wake_up）**: 早朝のスリープフォーカス中に起床Nudgeを届ける必要がある
3. **行動科学グラウンディング**: 研究ベースの最適タイミング（問題発生時刻）にNudgeを届けることが有効性の核心

entitlement: `com.apple.developer.usernotifications.time-sensitive` は3つの `.entitlements` ファイルすべてに登録済み。

## ScreenTime 削除に伴うサーバー状態移行方針

### 背景

v1.5.0で `AniccaScreenTimeReport` Extension を完全削除。サーバー側 `sensor_access_state.screen_time_enabled` カラムに `true` が残存するユーザーが存在する。

### 移行方針

| 項目 | 内容 |
|------|------|
| **方式** | サーバー側バックフィル（SQL UPDATE） |
| **SQL** | `UPDATE sensor_access_state SET screen_time_enabled = false WHERE screen_time_enabled = true;` |
| **実施タイミング** | v1.5.0 リリース後、App Store承認確認後に実行 |
| **クライアント側対応** | `profileSyncPayload` に `sensorAccess` を含めない（部分送信による他フラグ消失を回避） |
| **ロールバック方針** | 不要。`screen_time_enabled = false` はExtension削除後の正確な状態であり、復元の必要なし |
| **影響範囲** | `screen_time_enabled` カラムのみ。`sleep_enabled`, `steps_enabled`, `motion_enabled` 等は影響なし |

### なぜクライアント側で移行しないか

`profileSyncPayload` は `PATCH /api/mobile/profile` で全プロファイルをupsertする。`sensorAccess` を部分的に送信すると、サーバー側で他のセンサーフラグ（sleep, steps, motion）が上書き/消失するリスクがある。サーバー側SQLで `screen_time_enabled` のみをピンポイントで更新するのが安全。

## テスト結果

| 項目 | 結果 |
|------|------|
| `fastlane test` | **48テスト全通過、失敗0** |
| ビルド | **成功** |

## 注意事項

- `NotificationScheduler.swift:45` に `'timeSensitive' was deprecated in iOS 15.0: Use time-sensitive entitlement` という警告が出る。entitlement は既に登録済み（3つの `.entitlements` ファイルすべてに `com.apple.developer.usernotifications.time-sensitive = true` あり）。この警告はApple SDKの誤解を招く表現で、実際にはentitlement + コード両方が必要。
- devへのマージは未実施。ユーザーの実機確認待ち。
