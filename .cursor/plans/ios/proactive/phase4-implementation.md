# Phase 4 実装仕様書

> 作成日: 2026-01-20
> 目的: Phase 4で実装する内容の詳細と決定事項

---

## 概要

Phase 4の目標: **Nudgeの質を上げる + トラッキング基盤**

参照: `/Users/cbns03/Downloads/anicca-project/.cursor/plans/ios/proactive/roadmap.md`

---

## タスク一覧

| # | タスク | 状態 |
|---|--------|------|
| 1 | 説明文の角カッコ削除 | 未実装 |
| 2 | 通知タイトルを問題別に変更 | 未実装 |
| 3 | 通知タップのトラッキング（nudge_tapped） | 未実装 |
| 4 | 通知無視のトラッキング（nudge_ignored） | 未実装 |
| 5 | 課金ロジック実装（無料10 Nudge/月） | 未実装 |
| 6 | プラン表示修正（0/30 minutes削除） | 未実装 |
| 7 | Paywall配置変更（Superwall） | 未実装 |

---

## 1. 説明文の角カッコ削除

### 現状

`Localizable.strings`のNudge説明文に角カッコ付きプレフィックスがある。

**日本語例**:
```
"nudge_cant_wake_up_detail_1" = "【5秒ルール】5、4、3、2、1で足を床につける..."
"nudge_cant_wake_up_detail_2" = "【信頼ゼロ】「あと5分」の自分を何回信じた？..."
```

**英語例**:
```
"nudge_cant_wake_up_detail_1" = "[5 Second Rule] Count 5, 4, 3, 2, 1 and put your feet on the floor..."
"nudge_cant_wake_up_detail_2" = "[Zero Credibility] How many times have you trusted the '5 more minutes' you?..."
```

### やること

- `ja.lproj/Localizable.strings`: 全ての`【...】`プレフィックスを削除
- `en.lproj/Localizable.strings`: 全ての`[...]`プレフィックスを削除

### 対象キー

`nudge_*_detail_*`のパターンに一致する全てのキー（約30個）

### テスト方法

実機/SimでNudgeCardViewを表示して確認

---

## 2. 通知タイトルを問題別に変更 ->

### 現状

確認が必要:
- 現在の`ProblemType.notificationTitle`の実装
- どのファイルで通知タイトルが設定されているか

### やること

roadmap.mdに定義されたタイトルに変更:

| 問題 | 日本語 | English |
|------|--------|---------|
| staying_up_late | 夜更かし警報 | Late Night Alert |
| cant_wake_up | 起きろ | Wake Up |
| self_loathing | 自分を許して | Forgive Yourself |
| rumination | 今ここに戻ろう | Come Back to Now |
| procrastination | 5分だけやろう | Just 5 Minutes |
| anxiety | 深呼吸 | Breathe |
| lying | 今日は正直に | Be Honest Today |
| bad_mouthing | 善い言葉だけ | Kind Words Only |
| porn_addiction | 誘惑に勝とう | Beat the Urge |
| alcohol_dependency | 今夜は飲まない | No Drinks Tonight |
| anger | 3秒待とう | Wait 3 Seconds |
| obsessive | 手放そう | Let It Go |
| loneliness | 誰かに連絡しよう | Reach Out |

### 確認が必要

- `ProblemType.swift`の`notificationTitle`プロパティを確認
- `Localizable.strings`の既存キーを確認

---

## 3. 通知タップのトラッキング（nudge_tapped）

### 現状

通知タップ → NudgeCardView表示という流れがある。

### やること

通知タップでNudgeCardViewに遷移した時点で`Mixpanel.track("nudge_tapped")`を呼ぶ。

### プロパティ設計

```swift
Mixpanel.mainInstance().track(event: "nudge_tapped", properties: [
    "problem_type": problemType.rawValue,    // どの問題か
    "hour": Calendar.current.component(.hour, from: Date()),  // 何時にタップされたか
    "variant_index": content.variantIndex    // どの文言バリアントか
])
```

### Mixpanel側の設定

Mixpanelは事前にイベント定義不要（自動でイベントが作られる）

### 実装場所

NudgeCardViewが表示されるタイミング（`onAppear`または通知からの遷移処理）

### テスト方法

1. DEBUG通知を発火
2. 通知をタップ
3. Mixpanel Live Viewで`nudge_tapped`イベントを確認

---

## 4. 通知無視のトラッキング（nudge_ignored）

### 現状

iOSは通知が「無視された」ことを直接検知できない。

### 判定ロジック

- 通知タップ → NudgeCardView表示 → `nudge_tapped`送信
- 通知タップされない → NudgeCardView表示されない → 無視

### 実装方針

1. **通知スケジュール時**: 通知IDと送信時刻を`UserDefaults`に保存
2. **NudgeCardView表示時**: そのIDをpendingリストから削除、`nudge_tapped`送信
3. **アプリ起動時**: pendingリストに残っている通知 = 無視された通知 → `nudge_ignored`送信、リストをクリア

### データ構造

```swift
struct PendingNudge: Codable {
    let notificationId: String
    let problemType: String
    let scheduledAt: Date
    let variantIndex: Int
}
```

### テスト方法

1. 通知を発火
2. タップせずにアプリを直接開く
3. Mixpanelで`nudge_ignored`イベントを確認

---

## 5. 課金ロジック実装（無料10 Nudge/月）

### 現状

- RevenueCatでサブスク管理
- SuperwallでPaywall表示
- 現在の制限は「30分/月」の音声セッション（もう使ってない）

### 新しいモデル

| プラン | 内容 |
|--------|------|
| 無料 | 月10 Nudge |
| 有料 | 無制限 |

### 必要な実装

#### 5.1 カウント保存

`UserProfile`に追加:
```swift
var nudgeCountThisMonth: Int
var nudgeCountResetDate: Date
```

#### 5.2 カウントのタイミング

**決定**: 通知スケジュール時にカウント

理由:
- 通知が届いた時点で価値が発生している（Nudgeを受け取っている）
- タップしなくても通知は見ている可能性がある
- シンプルな実装
- ゲーミング防止（無視し続けて無限に通知を受け取ることを防ぐ）

#### 5.3 月初リセット

アプリ起動時に`nudgeCountResetDate`をチェック、月が変わっていたら:
- `nudgeCountThisMonth = 0`
- `nudgeCountResetDate = 今月1日`

#### 5.4 上限チェック

`ProblemNotificationScheduler.scheduleNotifications()`で:
1. 有料ユーザーかチェック（RevenueCat）
2. 無料ユーザーの場合、`nudgeCountThisMonth >= 10`なら通知をスケジュールしない

#### 5.5 10回超えた時の挙動

**決定**: 通知が来なくなる + アプリ起動時にPaywall表示

流れ:
1. 10回目のNudgeが送られる
2. 11回目以降は通知がスケジュールされない
3. ユーザーがアプリを開いた時、上限に達していたらPaywall表示

### 有料判定

```swift
Purchases.shared.getCustomerInfo { customerInfo, error in
    let isPro = customerInfo?.entitlements["pro"]?.isActive == true
}
```

### テスト方法

1. カウントを9に設定
2. 通知スケジュール実行 → カウントが10になる
3. 再度スケジュール実行 → 通知がスケジュールされないことを確認
4. アプリ起動 → Paywall表示を確認

---

## 6. プラン表示修正（0/30 minutes削除）

### 現状

`ProfileView`のプラン表示に「0/30 minutes」のような表示がある（音声セッションの残り時間）

### やること

- 「0/30 minutes」「0/300 minutes」の表示を削除
- 表示を「無料プラン」「月額プラン」「年額プラン」のみにする

### 確認が必要

`ProfileView.swift`のどの部分でこの表示がされているか確認

---

## 7. Paywall配置変更（Superwall）

### 現状のPlacements

Superwallに設定されているPlacements:
- `onboarding_complete`
- `profile_plan_tap`
- `session_complete_3`
- `session_complete_1`
- `campaign_app_launch`
- `quota_exceeded`

### 変更内容

| Placement | 変更 |
|-----------|------|
| `session_complete_*` | 削除（音声セッションはもうない） |
| `quota_exceeded` | 「Nudge 10回超過時」に使用 |

### 実装

`quota_exceeded`を呼び出す場所を変更:

```swift
// アプリ起動時（または適切なタイミング）
if !isPro && nudgeCountThisMonth >= 10 {
    Superwall.shared.register(event: "quota_exceeded")
}
```

### Paywall文言（Superwall Dashboard側）

ユーザーがCursorで設定する内容:
- 「月10回では足りない？」
- 「もっとNudgeが欲しいならProプランへ」
- 的な文言

### 確認が必要

- 現在`quota_exceeded`がどこで呼ばれているか
- `session_complete_*`がどこで呼ばれているか → 削除またはコメントアウト

---

## 実装順序（推奨）

1. **説明文の角カッコ削除** - シンプル、依存なし
2. **通知タイトル変更** - Localizable.stringsの修正
3. **プラン表示修正** - ProfileViewの修正
4. **課金ロジック** - UserProfile + ProblemNotificationScheduler
5. **Paywall配置変更** - Superwall呼び出し箇所の変更
6. **通知タップのトラッキング** - Mixpanel連携
7. **通知無視のトラッキング** - 複雑、最後に

---

## 関連ファイル

| ファイル | 役割 |
|----------|------|
| `Localizable.strings (ja/en)` | 文言 |
| `ProblemType.swift` | 問題タイプ定義、通知タイトル |
| `ProblemNotificationScheduler.swift` | 通知スケジュール |
| `NudgeCardView.swift` | 1枚画面表示 |
| `ProfileView.swift` | プラン表示 |
| `UserProfile.swift` | ユーザー設定、Nudgeカウント |
| `AppDelegate.swift` | 通知処理、アプリ起動時処理 |
| `AppState.swift` | アプリ状態管理 |

---

## 決定事項まとめ

| 項目 | 決定 | 理由 |
|------|------|------|
| Nudgeカウントのタイミング | 通知スケジュール時 | 通知が届いた時点で価値発生、シンプル、ゲーミング防止 |
| 10回超えた時の挙動 | 通知停止 + アプリ起動時Paywall | 自然なUX、スパム的な「課金して」通知を避ける |
| 無視の判定 | アプリ起動時にpendingリストをチェック | タップされてない = 無視 |

---

## 備考

- AlarmKit対応（cantWakeUp 6:00/6:05の2段階アラーム）は別途実装済み
- 時間帯フィルタリング（cantWakeUp 6:00-9:00限定）は実装済み
