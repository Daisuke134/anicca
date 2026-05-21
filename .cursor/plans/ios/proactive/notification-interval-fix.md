# 通知間隔シフトロジック修正

## 背景・目的

### なぜ間隔が必要か

1. **インパクトの維持**: 通知が同時に来ると、一つ一つの効果が薄れる
2. **効果測定**: どの通知がユーザーの行動変容に効いたか分析できなくなる
3. **UX**: 12:00にドゥンドゥンドゥンと3つ来たら、うざい・無視される

### ユースケース

- ユーザーが13個の問題を全部選択している場合
- 将来的にカスタム悩み→カスタム声かけが増えた場合
- 複数の問題が同じ時刻にスケジュールされている場合

### 要件

| 優先度 | 間隔 |
|--------|------|
| 理想 | 30分以上 |
| 最低 | 15分以上 |
| 絶対NG | 5分未満 |

---

## As-Is（現状・バグあり）

### コード（ProblemNotificationScheduler.swift:48-61）

```swift
for schedule in allSchedules {
    var hour = schedule.time.hour
    var minute = schedule.time.minute
    var currentMinutes = hour * 60 + minute

    if let last = lastScheduledMinutes {
        let diff = currentMinutes - last
        if diff < minimumIntervalMinutes && diff >= 0 {  // ← BUG: diff >= 0
            // 15分ずらす（スキップしない）
            currentMinutes = last + 15
            hour = (currentMinutes / 60) % 24
            minute = currentMinutes % 60
            logger.info("Shifted \(schedule.problem.rawValue) to \(hour):\(minute)")
        }
    }
    // ... schedule notification
    lastScheduledMinutes = currentMinutes
}
```

### バグの原因

`diff >= 0` の条件により、**3つ目以降の同時刻通知がシフトされない**。

### シミュレーション（anxiety, badMouthing, loneliness が全部12:00の場合）

| 順番 | 問題 | 元の時刻 | last | diff | 条件判定 | 結果 |
|------|------|----------|------|------|----------|------|
| 1 | anxiety | 12:00 | nil | - | - | 12:00 |
| 2 | badMouthing | 12:00 | 720 | 0 | 0 < 30 && 0 >= 0 ✓ | 12:15 |
| 3 | loneliness | 12:00 | 735 | -15 | -15 < 30 && **-15 >= 0 ✗** | **12:00** ← BUG |

**結果**: anxiety と loneliness が両方12:00に来る！

---

## To-Be（修正後）

### 修正コード

```swift
for schedule in allSchedules {
    var hour = schedule.time.hour
    var minute = schedule.time.minute
    var currentMinutes = hour * 60 + minute

    if let last = lastScheduledMinutes {
        // 修正: 前回スケジュール時刻 + 最小間隔より前なら、15分ずらす
        if currentMinutes < last + minimumIntervalMinutes {
            currentMinutes = last + 15
            hour = (currentMinutes / 60) % 24
            minute = currentMinutes % 60
            logger.info("Shifted \(schedule.problem.rawValue) to \(hour):\(minute)")
        }
    }
    // ... schedule notification
    lastScheduledMinutes = currentMinutes
}
```

### 修正後シミュレーション

| 順番 | 問題 | 元の時刻 | last | 条件 | 結果 |
|------|------|----------|------|------|------|
| 1 | anxiety | 12:00 | nil | - | 12:00 |
| 2 | badMouthing | 12:00 | 720 | 720 < 720+30 ✓ | 12:15 |
| 3 | loneliness | 12:00 | 735 | 720 < 735+30 ✓ | **12:30** ✓ |

**結果**: 12:00, 12:15, 12:30 と15分間隔で配信される！

---

## パッチ

### ファイル: `aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift`

### 変更箇所: Line 53-56

**Before:**
```swift
            if let last = lastScheduledMinutes {
                let diff = currentMinutes - last
                if diff < minimumIntervalMinutes && diff >= 0 {
                    // 15分ずらす（スキップしない）
```

**After:**
```swift
            if let last = lastScheduledMinutes {
                // 前回スケジュール時刻 + 最小間隔より前なら、15分ずらす
                if currentMinutes < last + minimumIntervalMinutes {
```

### 削除する行

- `let diff = currentMinutes - last` （不要になる）

---

## テストケース

### ケース1: 3つが同時刻（12:00）

入力: anxiety(12:00), badMouthing(12:00), loneliness(12:00)
期待: 12:00, 12:15, 12:30

### ケース2: 2つが近接（12:00, 12:10）

入力: anxiety(12:00), rumination(12:10)
期待: 12:00, 12:15（12:10は30分以内なので15分シフト）

### ケース3: 十分離れている（12:00, 13:00）

入力: anxiety(12:00), procrastination(13:00)
期待: 12:00, 13:00（シフト不要）

### ケース4: 大量の同時刻（5つが21:00）

入力: stayingUpLate(21:00), rumination(21:00), obsessive(21:00), selfLoathing(21:30), ...
期待: 21:00, 21:15, 21:30, 21:45, 22:00, ...

---

## 実装チェックリスト

- [ ] パッチ適用
- [ ] ビルド確認
- [ ] 実機テスト（通知スケジュール確認）
- [ ] ログで「Shifted」が正しく出力されることを確認

---

最終更新: 2025-01-18
