# HabitSetupStepView の Toggle 関連問題と対処

## 発生日時
2025-01-XX

## 報告された問題

### 問題1: カスタム習慣が表示されない
**症状**: 「Set your habits」画面で「Add Habit」を押して新しい習慣を追加しても、画面に表示されない。

**原因**: 
- `sortedAllHabits`（35-44行目）で、カスタム習慣は`customHabitTimes[customHabit.id]`がnilでない場合のみ追加されていた
- 新しく追加したカスタム習慣は時刻が設定されていないため、`customHabitTimes`にエントリがなく、表示されなかった

**対処**:
```swift
// 修正前
for customHabit in appState.customHabits {
    if let time = customHabitTimes[customHabit.id] {
        allHabits.append(...)
    }
}

// 修正後
for customHabit in appState.customHabits {
    let time = customHabitTimes[customHabit.id]  // nilでも追加
    allHabits.append(...)
}
```

### 問題2: Doneボタンが押せない
**症状**: スリープやトレーニングなどの習慣を設定・時刻設定しても、Doneボタンが押せない。最低1つでも設定したら次に進めるはずなのに、進めない。

**原因**:
1. `canSave`（324-330行目）のロジックに問題があった
   - `customHabitsHaveTime`が`appState.customHabits.allSatisfy`で**全ての**カスタム習慣が時刻設定済みを要求していた
   - カスタム習慣を追加した直後は時刻が設定されていないため、`customHabitsHaveTime`がfalseになっていた
2. 時間設定シートでCancelを押した場合、`selectedHabits`には含まれているが`habitTimes`には含まれていない状態になり、`defaultHabitsHaveTime`がfalseになる可能性があった

**対処**:
```swift
// 修正前
private var canSave: Bool {
    guard !isSaving else { return false }
    let defaultHabitsHaveTime = selectedHabits.allSatisfy { habitTimes[$0] != nil }
    let customHabitsHaveTime = appState.customHabits.allSatisfy { customHabitTimes[$0.id] != nil }
    return defaultHabitsHaveTime && customHabitsHaveTime
}

// 修正後
private var canSave: Bool {
    guard !isSaving else { return false }
    
    // 選択されたデフォルト習慣が全て時間設定済みかチェック
    let defaultHabitsHaveTime = selectedHabits.allSatisfy { habitTimes[$0] != nil }
    
    // 時刻が設定されているカスタム習慣のみをチェック
    // （時刻未設定のカスタム習慣は無視）
    let customHabitsWithTime = appState.customHabits.filter { customHabitTimes[$0.id] != nil }
    let customHabitsHaveTime = customHabitsWithTime.isEmpty || customHabitsWithTime.allSatisfy { customHabitTimes[$0.id] != nil }
    
    // 最低1つでも習慣が設定されていればOK
    let hasAtLeastOneHabit = !selectedHabits.isEmpty || !customHabitsWithTime.isEmpty
    
    return hasAtLeastOneHabit && defaultHabitsHaveTime && customHabitsHaveTime
}
```

### 問題3: 時間設定シートのCancel処理
**症状**: デフォルト習慣のToggleをONにして時間設定シートを開いた後、Cancelを押すと、`selectedHabits`には含まれているが`habitTimes`には含まれていない状態になり、`canSave`がfalseになる。

**原因**:
- Cancelを押した場合（310-312行目）、`showingTimePicker = nil`のみで、`selectedHabits`から削除されていなかった
- ToggleをONにすると`selectedHabits.insert(habit)`が実行されるが、Cancel時に選択状態が解除されていなかった

**対処**:
```swift
// 修正前
ToolbarItem(placement: .navigationBarLeading) {
    Button(String(localized: "common_cancel")) {
        showingTimePicker = nil
    }
}

// 修正後
ToolbarItem(placement: .navigationBarLeading) {
    Button(String(localized: "common_cancel")) {
        // Cancel時にselectedHabitsから削除
        selectedHabits.remove(habit)
        showingTimePicker = nil
    }
}
```

## 修正内容のまとめ

### 修正1: カスタム習慣の表示（35-45行目）
- **変更**: 時刻未設定のカスタム習慣も表示するように修正
- **影響**: 新しく追加したカスタム習慣が即座に画面に表示される

### 修正2: 時間設定シートのCancel処理（310-312行目）
- **変更**: Cancel時に`selectedHabits`から削除するように修正
- **影響**: Cancel時に選択状態が正しく解除され、`canSave`のロジックが正しく動作する

### 修正3: Doneボタンの有効化ロジック（324-330行目）
- **変更**: 
  - 時刻設定済みのカスタム習慣のみをチェック
  - 最低1つでも習慣が設定されていれば有効化
- **影響**: 最低1つでも習慣を設定すればDoneボタンが有効になる

## 期待される動作

1. ✅ カスタム習慣追加後、時刻未設定でもリストに表示される
2. ✅ 時間設定シートでCancelを押すと、選択状態が正しく解除される
3. ✅ 最低1つでも習慣を設定すればDoneボタンが有効になる

## 関連ファイル

- `aniccaios/aniccaios/Onboarding/HabitSetupStepView.swift`
- `aniccaios/aniccaios/AppState.swift`
- `aniccaios/aniccaios/Models/CustomHabitConfiguration.swift`

## 参考

- Xcodeログに表示されていたエラー（RTIInputSystemClient関連）は、この問題とは無関係のシステムレベルの警告でした

