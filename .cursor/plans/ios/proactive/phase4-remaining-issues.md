# Phase 4 残課題 引き継ぎ書

> **作成日**: 2026-01-21
>
> **目的**: Phase 4 テスト中に発見された未解決の問題をまとめ、次の作業者に引き継ぐ

---

## 概要

Phase 4 の大部分は完了しているが、以下の4つの問題が残っている。

| # | 問題 | 重要度 |
|---|------|--------|
| 1 | AlarmKit ボタンからの遷移ができない | 高 |
| 2 | Superwall の Paywall が古いデザインのまま | 高 |
| 3 | Paywall テスト（5回目/10回目）が未実施 | 中 |
| 4 | ignored → シフトのログ確認方法 | 低 |

---

## 問題1: AlarmKit ボタンからの遷移ができない

### 現象

1. AlarmKit アラームが鳴る
2. オレンジボタン「今日を始める」をタップ
3. **何も起きない（遷移しない）**
4. しかし、その後**手動でアプリを開くと NudgeCard が既に表示されている**

### 重要な観察

- NudgeCard は**ちゃんと準備されている**（手動でアプリを開くと表示される）
- つまり `appState.pendingNudgeCard = content` は**実行されている**
- 問題は**アラームボタンからアプリへの遷移自体**ができていないこと

### 現在のコード構造

```
OpenProblemOneScreenIntent.perform()
  ↓
NotificationCenter.post("OpenProblemOneScreen")
  ↓
aniccaiosApp.swift の .onReceive で受信
  ↓
appState.pendingNudgeCard = content
  ↓
MainTabView.swift の .fullScreenCover(item: $appState.pendingNudgeCard) で表示
```

### 試した修正（効果なし）

1. `ProblemAlarmKitScheduler.swift`: `NotificationCenter.post()` を `MainActor.run` で囲んだ
2. `aniccaiosApp.swift`: `.receive(on: DispatchQueue.main)` を追加

### 推測される原因

**Intent からアプリを開く処理が欠けている可能性**

`LiveActivityIntent` の `perform()` は通知を post するだけで、**アプリをフォアグラウンドに持ってくる処理がない**。

iOS の AlarmKit では、secondaryButton をタップした時に自動的にアプリが開かれる**はず**だが、何らかの理由で開かれていない。

### 調査すべきこと

1. **Apple ドキュメント**で `AlarmKit` + `LiveActivityIntent` の正しい実装方法を確認
2. **secondaryButtonBehavior: .custom** の意味を確認（`.default` にすべき？）
3. Intent から**明示的にアプリを開く**方法があるか調査
   - `openURL` を使う？
   - 別の Intent タイプを使う？

### 関連ファイル

- `aniccaios/aniccaios/Notifications/ProblemAlarmKitScheduler.swift` (186行目: secondaryIntent の設定)
- `aniccaios/aniccaios/aniccaiosApp.swift` (22-33行目: 通知受信)

---

## 問題2: Superwall の Paywall が古いデザインのまま

### 現象

- Superwall Dashboard でペイウォールのデザインを更新した
- しかしアプリでは**古いデザイン**が表示される
- オンボーディング完了時の `onboarding_complete` でも古いまま
- ローディング後に更新される現象ではなく、**ずっと古いまま**

### 現在のコード

```swift
// SuperwallManager.swift
func configure() {
    Superwall.configure(
        apiKey: AppConfig.superwallAPIKey,
        purchaseController: controller
    )

    // 最新のペイウォールをプリロード
    Task {
        await Superwall.shared.preloadAllPaywalls()
    }
}

func register(placement: String) {
    Superwall.shared.register(placement: placement)
}
```

### 推測される原因

1. **キャッシュ問題**: `preloadAllPaywalls()` が古いキャッシュを使っている
2. **API キー問題**: 開発用/本番用の API キーが混在している可能性
3. **Dashboard 設定問題**: Paywall が Draft のままで Published されていない
4. **Campaign 紐付け問題**: Placement に正しい Paywall が紐付いていない

### 調査すべきこと

1. **Superwall Dashboard で確認**:
   - Placements 一覧で `onboarding_complete` が存在するか
   - Campaigns で `onboarding_complete` にどの Paywall が紐付いているか
   - Paywalls で最新デザインが **Published** になっているか（Draft ではなく）

2. **アプリ側で確認**:
   - `AppConfig.superwallAPIKey` の値（開発/本番どちらか）
   - アプリを**完全削除して再インストール**してキャッシュクリア

3. **Superwall SDK のドキュメント**:
   - キャッシュの明示的なクリア方法があるか
   - `preloadAllPaywalls()` の正しい使い方

### 関連ファイル

- `aniccaios/aniccaios/Services/SuperwallManager.swift`
- `AppConfig` のファイル（API キー定義場所）

---

## 問題3: Paywall テスト（5回目/10回目）が未実施

### 現象

テスト担当者が**年額プランに加入中**のため、Free ユーザー向けの Paywall テストができない。

### 解決方法

**サンドボックスアカウントを切り替える**

1. iPhone の **設定** → **App Store** → **サンドボックスアカウント**
2. 現在のアカウントを**サインアウト**
3. **新しいサンドボックスアカウント**でサインイン
   - App Store Connect → ユーザーとアクセス → サンドボックス → テスター で作成可能

RevenueCat は device ID + サンドボックスアカウント で識別するため、新しいアカウントでは Free ユーザーとして扱われる。

### テスト手順（サンドボックス切り替え後）

**5回目 Paywall**:
1. Profile → 🧪 Phase 4 デバッグ → NudgeCard完了回数「4回」
2. NudgeCard を完了
3. 期待: Paywall 表示

**10回目（月間上限）Paywall**:
1. Profile → 🧪 Phase 4 デバッグ → NudgeCard完了回数「0」（リセット）
2. 月間NudgeCard完了「9回」
3. NudgeCard を完了
4. 期待: Paywall 表示 + 通知停止

---

## 問題4: ignored → シフトのログ確認

### 現象

「2回」ボタンを押した後、アプリを再起動するとログがリセットされて確認できない。

### 解決方法

1. 「2回」ボタンを押す
2. アプリを**終了しないで**
3. 「月変わり」ボタンを押す（通知再スケジュール）
4. そのままログを確認

### 期待されるログ

```
Shifted staying_up_late from 21:0 to 21:30 due to 2 consecutive ignored days
```

### ログから確認できたこと

```
DEBUG: Recorded 2 ignored for staying_up_late, consecutiveIgnoredDays: 2
DEBUG: Recorded 2 ignored for staying_up_late, consecutiveIgnoredDays: 4
```

→ `consecutiveIgnoredDays` は正しくインクリメントされている。シフトロジック自体は動いている可能性が高い。

---

## 完了済み項目（参考）

以下は正常に動作することが確認済み:

- ✅ デバッグ通知 → NudgeCard 表示
- ✅ 0時ボタン → variant 3 表示
- ✅ 1時ボタン → variant 4 表示
- ✅ 👍 → `nudge_positive_feedback` イベント
- ✅ 👎 → `nudge_negative_feedback` イベント
- ✅ 月変わりリセット
- ✅ 日本語「マイパス」表示

---

## 優先順位

1. **問題1 (AlarmKit)**: ユーザー体験に直結。最優先で解決すべき。
2. **問題2 (Superwall)**: 課金に直結。早急に解決すべき。
3. **問題3 (Paywall テスト)**: サンドボックス切り替えで解決可能。
4. **問題4 (ログ確認)**: 軽微。現状のワークアラウンドで確認可能。

---

## 注意事項

- 現在の aniccaiosApp.swift と ProblemAlarmKitScheduler.swift には修正が加えられているが、**効果がなかった**
- これらの修正は元に戻すか、別のアプローチで上書きする必要がある

---

*この引き継ぎ書は 2026-01-21 時点の状況を記録したものである。*
