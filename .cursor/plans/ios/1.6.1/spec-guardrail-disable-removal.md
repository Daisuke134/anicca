# Guardrail Disable Removal Spec (v1)

**作成日**: 2026-02-05
**目的**: Guardrails がnudgeを勝手にOFFにするのを止める

---

## 問題

現在の guardrails が `enabled = false` を設定している:

| Guardrail | 条件 | 現状 |
|-----------|------|------|
| Night Curfew | 23:00-05:59（exempt以外） | `enabled = false` |
| <30min Interval | 同じ問題で30分以内 | `enabled = false` |
| Max-32 Cap | 32個超過 | `enabled = false` |

## ユーザー要望

- 時間スロットは既に設計済み
- 重複はない（数学的に保証）
- **全て配信したい。OFFにするな。**
- 警告ログは残してOK

## 修正方針

**`enabled = false` を削除し、警告ログのみ残す。**

---

## ファイル: `apps/api/src/agents/commander.js`

### Patch 1: Night Curfew (L587-597)

**Before:**
```javascript
// Rule 3: Night curfew (23:00-05:59) — disable non-exempt
for (const nudge of result) {
  const slot = slotLookup.get(nudge.slotIndex);
  if (!slot) continue;
  const { scheduledHour } = slot;
  const isNightTime = scheduledHour >= 23 || scheduledHour < 6;
  if (isNightTime && nudge.enabled && !NIGHT_EXEMPT_PROBLEMS.has(slot.problemType)) {
    nudge.enabled = false;
    nudge.reasoning += ' [guardrail: night curfew applied]';
  }
}
```

**After:**
```javascript
// Rule 3: Night curfew (23:00-05:59) — WARNING ONLY (user wants all nudges delivered)
for (const nudge of result) {
  const slot = slotLookup.get(nudge.slotIndex);
  if (!slot) continue;
  const { scheduledHour } = slot;
  const isNightTime = scheduledHour >= 23 || scheduledHour < 6;
  if (isNightTime && nudge.enabled && !NIGHT_EXEMPT_PROBLEMS.has(slot.problemType)) {
    // WARNING ONLY - do not disable. User wants all nudges delivered.
    nudge.reasoning += ' [warning: night curfew zone]';
    console.warn(`⚠️ [Guardrail] Nudge at ${slot.scheduledTime} is in night curfew zone (not disabled)`);
  }
}
```

### Patch 2: <30min Interval (L599-623)

**Before:**
```javascript
for (const [, entries] of byProblem) {
  entries.sort((a, b) => a.nudge.slotIndex - b.nudge.slotIndex);
  let lastMinutes = -Infinity;
  for (const { nudge, slot } of entries) {
    const adjustedHour = slot.scheduledHour < 6 ? slot.scheduledHour + 24 : slot.scheduledHour;
    const currentMinutes = adjustedHour * 60 + slot.scheduledMinute;
    if (currentMinutes - lastMinutes < 30) {
      nudge.enabled = false;
      nudge.reasoning += ' [guardrail: <30min interval]';
    } else {
      lastMinutes = currentMinutes;
    }
  }
}
```

**After:**
```javascript
for (const [, entries] of byProblem) {
  entries.sort((a, b) => a.nudge.slotIndex - b.nudge.slotIndex);
  let lastMinutes = -Infinity;
  for (const { nudge, slot } of entries) {
    const adjustedHour = slot.scheduledHour < 6 ? slot.scheduledHour + 24 : slot.scheduledHour;
    const currentMinutes = adjustedHour * 60 + slot.scheduledMinute;
    if (currentMinutes - lastMinutes < 30) {
      // WARNING ONLY - do not disable. User wants all nudges delivered.
      nudge.reasoning += ' [warning: <30min interval]';
      console.warn(`⚠️ [Guardrail] Nudge at ${slot.scheduledTime} is within 30min of previous (not disabled)`);
    }
    // Always update lastMinutes to track all nudges
    lastMinutes = currentMinutes;
  }
}
```

### Patch 3: Max-32 Cap (L649-658) - KEEP AS IS

Max-32 は iOS 通知制限のため維持。ただし、通常 32 を超えることはないので問題なし。

```javascript
// Keep this guardrail - iOS notification limit is real
```

### Patch 4: Min-1 Per Problem (L625-647) - KEEP AS IS

これは re-enable ロジックなので維持。

---

## テストケース

### 既存テストの更新（3件）

| テスト名 | 行 | 変更内容 |
|---------|-----|---------|
| `disables non-exempt problems in night hours (23:00-05:59)` | L109 | `enabled: false` → `enabled: true`、`night curfew` → `warning: night curfew zone` |
| `disables same-problem slots <30min apart` | L134 | `enabled: false` → `enabled: true`、`<30min` → `warning: <30min interval` |
| `does not re-enable night-curfewed non-exempt problems even for min-1 rule` | L147 | **削除または修正** - night curfewがdisableしなくなるため前提が無効 |

### reasoningLogger.test.js (変更不要)

- `[OFF: <30min interval]` と `[OFF: night curfew applied]` テストは手動で `enabled: false` を設定
- Max-32 cap シナリオで引き続き有効
- **変更不要**

---

## 実行チェックリスト

| # | タスク | 状態 |
|---|--------|------|
| 1 | Night curfew: `enabled = false` 削除 | ✅ |
| 2 | <30min interval: `enabled = false` 削除 | ✅ |
| 3 | テスト更新 | ✅ |
| 4 | テスト実行 | ✅ (265 tests passed) |
| 5 | コミット & プッシュ | ✅ (26dd5a49) |

---

## 完了条件

1. ✅ Night curfew で nudge が OFF にならない
2. ✅ <30min interval で nudge が OFF にならない
3. ✅ 警告ログは出力される
4. ✅ 全テスト PASS
5. ✅ 全 nudge が配信される

---

## Review History

| Version | Date | Reviewer | Status | Issues |
|---------|------|----------|--------|--------|
| v1 | 2026-02-05 | Claude | ✅ IMPLEMENTED | All tasks complete |
