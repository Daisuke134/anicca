# Nudge通知頻度リデザイン仕様書

**バージョン:** 1.6.0  
**作成日:** 2026-02-02  
**ステータス:** Draft  
**ブランチ:** release/1.6.0

---

## 1. 背景と目的

### 1.1 問題点

| 問題 | 詳細 |
|-----|------|
| **通知が多すぎる** | ユーザーフィードバック：「通知が頻繁すぎる」 |
| **1問題あたり5-6回/日** | 5問題選択で25-30回/日、多すぎる |
| **時間間隔が狭い** | 例：`cant_wake_up` は 6:00, 6:15, 6:30 と15分間隔で連打 |
| **コンテンツ重複** | 毎日同じメッセージが同じ時間に来る |

### 1.2 目的

- 1問題あたりの通知数を**5-6回 → 3回**に削減（夜更かしは例外で5回）
- 全問題選択時でも**最低15分間隔**を確保
- ユーザー体験を改善しつつ、Nudgeの効果を維持

---

## 2. エビデンスベースの設計

### 2.1 学術的エビデンス

| 出典 | 知見 |
|------|------|
| JMIR mHealth 2023 (Bell et al.) | 通知を受けると1時間以内にアプリを開く確率が**3.5倍**に増加 |
| JMIR mHealth 2023 | 24時間で見ると**1.3倍**のエンゲージメント増加 |
| JMIR mHealth 2023 | 固定通知 vs ランダム通知 vs 通知なしで離脱時間は大差なし |
| Springer JMIS 2021 | 週3回が最適なエンゲージメント/チャーン回避バランス |
| UrbanAirship Benchmark | Daily+通知でリテンション820%向上 |

### 2.2 設計方針

| 方針 | 根拠 |
|------|------|
| **1問題3回/日**（朝・昼・夜） | 研究では1日1回でも効果あり。3回は十分なリマインダー |
| **夜更かしのみ例外（5回）** | 問題の性質上、20:00-01:00の夜間集中介入が必要。ポルノは夜更かしとスロット重複を避けるため3回に統一 |
| **最低15分間隔** | 同時通知・連打の回避 |
| **理想は30分間隔** | ユーザー負担軽減 |

---

## 3. 新時間帯設計

### 3.1 時間帯リデザイン

| 問題タイプ | 現状 | 新設計 | スロット数 |
|----------|------|--------|---------|
| **staying_up_late** | 20:00, 21:00, 22:00, 23:00, 00:00, 01:00 | **20:00, 22:00, 23:30, 00:00, 01:00** | 6→5 |
| **cant_wake_up** | 06:00, 06:15, 06:30, 08:00, 22:15 | **06:00, 06:45, 07:15** | 5→3 |
| self_loathing | 07:00, 12:00, 14:45, 17:00, 19:00 | **08:00, 13:00, 19:00** | 5→3 |
| rumination | 08:30, 18:00, 19:30, 21:15, 22:45 | **08:30, 14:00, 21:00** | 5→3 |
| procrastination | 09:00, 11:00, 13:00, 15:00, 18:30 | **09:15, 13:30, 17:00** | 5→3 |
| anxiety | 07:30, 10:00, 14:00, 17:30, 20:45 | **07:30, 12:15, 18:45** | 5→3 |
| lying | 08:15, 11:30, 14:30, 16:30, 19:15 | **08:15, 13:15, 18:15** | 5→3 |
| bad_mouthing | 09:30, 12:30, 15:30, 18:15, 21:45 | **09:30, 14:30, 19:30** | 5→3 |
| **porn_addiction** | 20:30, 21:30, 22:30, 23:30, 00:30, 01:30 | **20:30, 22:30, 23:45** | 6→3 |
| alcohol_dependency | 16:00, 17:15, 18:45, 19:45, 20:15 | **16:00, 18:00, 20:15** | 5→3 |
| anger | 07:45, 10:45, 13:30, 15:45, 16:45 | **07:45, 12:30, 17:30** | 5→3 |
| obsessive | 08:45, 10:30, 12:15, 14:15, 17:45 | **09:00, 13:45, 18:30** | 5→3 |
| loneliness | 09:15, 11:15, 13:45, 15:15, 16:15 | **10:00, 15:00, 19:45** | 5→3 |

### 3.2 間隔分析（全13問題選択時）

全41スロットを時刻順にソートした場合の間隔分布（**trimSlots適用前**の参考値）：

| 間隔 | 箇所数 | 割合 |
|------|--------|------|
| 15-29分 | 22箇所 | 55% |
| 30-44分 | 11箇所 | 27.5% |
| 45-59分 | 1箇所 | 2.5% |
| 60分以上 | 6箇所 | 15% |

**注意:** 
- これは**trimSlots適用前**の全41スロット分布
- 実運用では32スロット上限（iOS制限）でtrimされる
- 通常ユーザーは3-5問題選択なので、実際の間隔はもっと余裕がある

### 3.3 選択数別の通知数

| 選択数 | 旧（1日） | 新（1日） | 改善 |
|-------|---------|---------|------|
| 1問題 | 5-6回 | **3回**（夜更かし: 5回） | 40-50%削減 |
| 3問題 | 15-18回 | **9回**（夜更かし含む場合11回） | 50%削減 |
| 5問題 | 25-30回 | **15回**（夜更かし含む場合17回） | 50%削減 |
| 10問題 | 32回（上限） | **30-32回**（夜更かし含む場合32回） | 上限付近 |
| 13問題（全選択） | 32回（上限） | **32回**（41→32切り詰め） | 上限で制御 |

**注:** 新設計では夜更かし（5スロット）以外は3スロット。夜更かしを含む場合は+2スロット。

---

## 4. 実装変更リスト

### 4.1 変更ファイル一覧

| # | ファイル | 変更内容 | プラットフォーム |
|---|---------|---------|---------------|
| 1 | `aniccaios/aniccaios/Models/ProblemType.swift` | `notificationSchedule`プロパティを更新 | iOS |
| 2 | `apps/api/src/agents/scheduleMap.js` | `getScheduleMap(appVersion)`関数追加 + 旧/新MAP定義 | Backend |
| 3 | `apps/api/src/routes/mobile/nudge.js` | `X-App-Version`ヘッダー読み取り + `getScheduleMap`呼び出し | Backend |
| 4 | `apps/api/src/jobs/generateNudges.js` | ユーザーごとのアプリバージョン参照 + `getScheduleMap`呼び出し | Backend |
| 5 | `aniccaios/aniccaios/Services/LLMNudgeService.swift` | `X-App-Version`ヘッダー送信追加 | iOS |
| 6 | `aniccaios/aniccaiosTests/ProblemTypeTests.swift` | スロット数の期待値を更新 | iOS Test |
| 7 | `aniccaios/aniccaiosTests/NotificationHotfixTests.swift` | スロット数・間隔関連のテストを確認・更新 | iOS Test |
| 8 | `apps/api/src/agents/__tests__/scheduleMap.test.js` | iOS一致検証・間隔検証・バージョン分岐テスト追加 | Backend Test |

### 4.2 変更詳細

#### 4.2.1 ProblemType.swift

**Before:**
```swift
var notificationSchedule: [(hour: Int, minute: Int)] {
    switch self {
    case .stayingUpLate:
        return [(20, 0), (21, 0), (22, 0), (23, 0), (0, 0), (1, 0)]
    case .cantWakeUp:
        return [(6, 0), (6, 15), (6, 30), (8, 0), (22, 15)]
    // ... 他の問題タイプ
    }
}
```

**After:**
```swift
var notificationSchedule: [(hour: Int, minute: Int)] {
    switch self {
    case .stayingUpLate:
        return [(20, 0), (22, 0), (23, 30), (0, 0), (1, 0)]  // 5スロット
    case .cantWakeUp:
        return [(6, 0), (6, 45), (7, 15)]  // 3スロット
    case .selfLoathing:
        return [(8, 0), (13, 0), (19, 0)]
    case .rumination:
        return [(8, 30), (14, 0), (21, 0)]
    case .procrastination:
        return [(9, 15), (13, 30), (17, 0)]
    case .anxiety:
        return [(7, 30), (12, 15), (18, 45)]
    case .lying:
        return [(8, 15), (13, 15), (18, 15)]
    case .badMouthing:
        return [(9, 30), (14, 30), (19, 30)]
    case .pornAddiction:
        return [(20, 30), (22, 30), (23, 45)]  // 3スロット
    case .alcoholDependency:
        return [(16, 0), (18, 0), (20, 15)]
    case .anger:
        return [(7, 45), (12, 30), (17, 30)]
    case .obsessive:
        return [(9, 0), (13, 45), (18, 30)]
    case .loneliness:
        return [(10, 0), (15, 0), (19, 45)]
    }
}
```

#### 4.2.2 scheduleMap.js

**Before:**
```javascript
export const SCHEDULE_MAP = {
  staying_up_late:     ['20:00', '21:00', '22:00', '23:00', '00:00', '01:00'],
  cant_wake_up:        ['06:00', '06:15', '06:30', '08:00', '22:15'],
  // ... 他の問題タイプ
};
```

**After:**
```javascript
export const SCHEDULE_MAP = {
  staying_up_late:     ['20:00', '22:00', '23:30', '00:00', '01:00'],  // 5スロット
  cant_wake_up:        ['06:00', '06:45', '07:15'],
  self_loathing:       ['08:00', '13:00', '19:00'],
  rumination:          ['08:30', '14:00', '21:00'],
  procrastination:     ['09:15', '13:30', '17:00'],
  anxiety:             ['07:30', '12:15', '18:45'],
  lying:               ['08:15', '13:15', '18:15'],
  bad_mouthing:        ['09:30', '14:30', '19:30'],
  porn_addiction:      ['20:30', '22:30', '23:45'],  // 3スロット
  alcohol_dependency:  ['16:00', '18:00', '20:15'],
  anger:               ['07:45', '12:30', '17:30'],
  obsessive:           ['09:00', '13:45', '18:30'],
  loneliness:          ['10:00', '15:00', '19:45'],
};
```

---

## 5. 影響範囲分析

### 5.1 影響を受けるコンポーネント

| コンポーネント | 影響 | 変更必要 |
|--------------|------|---------|
| `ProblemNotificationScheduler` | `notificationSchedule`から時間帯取得 | **変更不要**（自動適用） |
| `NudgeContentSelector` | `notificationVariantCount`を使用（変更なし） | **変更不要** |
| `LLMNudgeCache` | `scheduledTime`でマッチング | **変更不要** |
| `LLMNudgeService` | APIから時間帯取得 | **変更不要** |
| `buildFlattenedSlotTable()` | `SCHEDULE_MAP`から時間帯取得 | **変更不要**（自動適用） |
| `trimSlots()` | 32スロット上限で切り詰め | **変更不要** |

### 5.2 Day 1 / Day 2+ フロー確認

| 日 | フロー | 影響 |
|---|-------|------|
| **Day 1** | ルールベース（iOS側の`notificationSchedule`） | ✅ 新時間帯で通知スケジュール |
| **Day 2+** | LLM優先（Backend `SCHEDULE_MAP`）→ フォールバックはルールベース | ✅ 新時間帯でLLM Nudge生成 |

### 5.3 後方互換性

| 項目 | 状態 | 詳細 |
|------|------|------|
| 既存ユーザー | ✅ OK | 次回アプリ起動時に新スケジュール適用 |
| LLMキャッシュ | ✅ OK | 日次更新で新時間帯に自動移行 |
| ルールベースコンテンツ | ✅ OK | `notificationVariantCount`は変更なし |
| API互換性 | ✅ OK | APIレスポンス形式は変更なし |

### 5.4 バージョン不一致時の挙動

**重要:** iOS/Backend同時デプロイを原則とする。理由：

| シナリオ | Day 1（iOS） | Day 2+（Backend） | 問題 |
|---------|-------------|------------------|------|
| iOS旧 + Backend新 | 旧スケジュール（iOS） | 新スケジュール（Backend） | ❌ 不整合 |
| iOS新 + Backend旧 | 新スケジュール（iOS） | 旧スケジュール（Backend） | ❌ 不整合 |
| iOS新 + Backend新 | 新スケジュール | 新スケジュール | ✅ 一致 |

**対策:**
1. **バージョン分岐**: `getScheduleMap(appVersion)`でクライアントバージョンに応じた設定を返す
2. **Backend先行デプロイ可能**: 旧クライアントは旧設定、新クライアントは新設定で自動分岐

---

## 6. テスト計画

### 6.1 単体テスト（iOS）

| テスト | ファイル | 確認項目 |
|-------|---------|---------|
| スロット数テスト | `aniccaios/aniccaiosTests/ProblemTypeTests.swift` | 各問題のスロット数が期待値と一致 |
| 時間帯テスト | `aniccaios/aniccaiosTests/NotificationHotfixTests.swift` | 時間帯が有効範囲内 |
| **間隔検証テスト（新規）** | `aniccaios/aniccaiosTests/NotificationHotfixTests.swift` | 全スロット間隔 >= 15分 |
| **上限検証テスト（既存）** | `aniccaios/aniccaiosTests/NotificationHotfixTests.swift` | trimSlotsで32以下に制限 |

### 6.2 単体テスト（Backend）

| テスト | ファイル | 確認項目 |
|-------|---------|---------|
| scheduleMapテスト | `apps/api/src/agents/__tests__/scheduleMap.test.js` | iOS と完全一致 |
| **一致検証テスト（新規）** | `apps/api/src/agents/__tests__/scheduleMap.test.js` | iOS ProblemType.swiftの時刻リストと完全一致 |
| **間隔検証テスト（新規）** | `apps/api/src/agents/__tests__/scheduleMap.test.js` | 全スロット間隔 >= 15分 |
| **バージョン分岐テスト（新規）** | `apps/api/src/agents/__tests__/scheduleMap.test.js` | getScheduleMap('1.5.0')→OLD、getScheduleMap('1.6.0')→NEW |

### 6.3 iOS/Backend一致検証（新規）

**方法:** iOS側の時刻リストをJSON出力し、Backend側と比較

```javascript
// scheduleMap.test.js
const IOS_EXPECTED = {
  staying_up_late: ['20:00', '22:00', '23:30', '00:00', '01:00'],
  cant_wake_up: ['06:00', '06:45', '07:15'],
  // ... 全13問題
};

test('SCHEDULE_MAP matches iOS ProblemType.notificationSchedule', () => {
  for (const [problem, times] of Object.entries(IOS_EXPECTED)) {
    expect(SCHEDULE_MAP[problem]).toEqual(times);
  }
});
```

### 6.4 間隔検証テスト（新規）

```javascript
// scheduleMap.test.js
test('all slots have at least 15 minutes interval', () => {
  const allSlots = buildFlattenedSlotTable(Object.keys(SCHEDULE_MAP));
  for (let i = 1; i < allSlots.length; i++) {
    const prev = allSlots[i - 1];
    const curr = allSlots[i];
    const prevMin = (prev.scheduledHour < 6 ? prev.scheduledHour + 24 : prev.scheduledHour) * 60 + prev.scheduledMinute;
    const currMin = (curr.scheduledHour < 6 ? curr.scheduledHour + 24 : curr.scheduledHour) * 60 + curr.scheduledMinute;
    const diff = currMin - prevMin;
    expect(diff).toBeGreaterThanOrEqual(15);
  }
});
```

### 6.5 統合テスト

| テスト | 確認項目 |
|-------|---------|
| 通知スケジューリング | 新時間帯で通知がスケジュールされる |
| LLM Nudge生成 | 新時間帯でLLM Nudgeが生成される |
| キャッシュマッチング | 新時間帯でキャッシュがヒットする |

### 6.6 E2Eテスト（Maestro）

| テスト | 確認項目 |
|-------|---------|
| オンボーディング | 問題選択後に通知がスケジュールされる |
| 通知タップ | Nudge Cardが表示される |

---

## 7. デプロイ手順

### 7.1 手順（バージョン分岐による安全デプロイ）

```
[Step 1] Backend先行デプロイ（バージョン分岐で旧クライアント保護）
    ↓
[Step 2] iOS App Store提出・審査
    ↓
[Step 3] iOS リリース
```

**Step 1: Backend先行デプロイ**
1. `scheduleMap.js`に`getScheduleMap(appVersion)`と旧/新両方の定義を追加
2. `/nudge/today`で`X-App-Version`ヘッダー読み取り・分岐
3. `generateNudges.js`でユーザーごとのアプリバージョン参照
4. Staging環境でテスト（両バージョンのリクエストで検証）
5. Production環境にデプロイ

**Step 2: iOS App Store提出**
1. `ProblemType.swift`を更新
2. `X-App-Version`ヘッダー送信を追加
3. テスト実行
4. App Store提出

**Step 3: iOS リリース**
1. App Store審査通過後リリース
2. 旧クライアントは引き続き旧スケジュールで動作（バージョン分岐で保護）
3. 新クライアントは新スケジュールで動作

### 7.2 バージョン分岐実装（Backend）

**方針:** クライアントバージョンに応じて旧/新SCHEDULE_MAPを分岐する（Feature Flagは使用しない、バージョン分岐のみ）

```javascript
// scheduleMap.js
import semver from 'semver';  // 既存依存: package.jsonに含まれる

const OLD_SCHEDULE_MAP = {
  staying_up_late: ['20:00', '21:00', '22:00', '23:00', '00:00', '01:00'],
  cant_wake_up: ['06:00', '06:15', '06:30', '08:00', '22:15'],
  // ... 旧設定（全13問題）
};

const NEW_SCHEDULE_MAP = {
  staying_up_late: ['20:00', '22:00', '23:30', '00:00', '01:00'],
  cant_wake_up: ['06:00', '06:45', '07:15'],
  // ... 新設定（全13問題）
};

// 新スケジュール適用の最小バージョン
const NEW_SCHEDULE_MIN_VERSION = '1.6.0';

/**
 * クライアントバージョンに応じたSCHEDULE_MAPを返す
 * @param {string} appVersion - クライアントのアプリバージョン（例: "1.5.0", "1.6.0"）
 * @returns {Object} 該当バージョン用のSCHEDULE_MAP
 */
export function getScheduleMap(appVersion) {
  // バージョン未指定 or パース不可 → 旧設定（安全側に倒す）
  if (!appVersion || !semver.valid(semver.coerce(appVersion))) {
    return OLD_SCHEDULE_MAP;
  }
  // 1.6.0未満は旧設定
  if (semver.lt(semver.coerce(appVersion), NEW_SCHEDULE_MIN_VERSION)) {
    return OLD_SCHEDULE_MAP;
  }
  return NEW_SCHEDULE_MAP;
}

// ⚠️ 廃止予定: 直接参照禁止。全てgetScheduleMap()経由に移行
// @deprecated Use getScheduleMap(appVersion) instead
export const SCHEDULE_MAP = NEW_SCHEDULE_MAP;
```

### 7.2.1 バージョン分岐が必要なエンドポイント

| エンドポイント | ファイル | 用途 | X-App-Version必須 |
|--------------|---------|------|------------------|
| `GET /api/mobile/nudge/today` | `apps/api/src/routes/mobile/nudge.js` | LLM Nudge取得 | ✅ 必須 |
| `POST /api/mobile/nudge/trigger` | `apps/api/src/routes/mobile/nudge.js` | サーバーNudge発火 | ❌ 不要（iOS側でスケジュール） |
| Cron Job（generateNudges） | `apps/api/src/jobs/generateNudges.js` | LLM Nudge生成 | ⚠️ ユーザーごとにアプリバージョンをDB参照 |

### 7.2.2 iOS側変更（全APIリクエスト共通化）

```swift
// APIClient.swift または共通リクエスト設定
extension URLRequest {
    mutating func addStandardHeaders() {
        setValue(AppConfig.appVersion, forHTTPHeaderField: "X-App-Version")
        // ... 他の共通ヘッダー
    }
}

// LLMNudgeService.swift
var request = URLRequest(url: url)
request.addStandardHeaders()
```

### 7.2.3 Cron Job対応（generateNudges）

```javascript
// generateNudges.js
async function generateNudgesForUser(userId) {
  // ユーザーの最新アプリバージョンをDBから取得
  const user = await getUserProfile(userId);
  const appVersion = user.app_version || '1.0.0';
  const scheduleMap = getScheduleMap(appVersion);
  // ... scheduleMapを使用してLLM Nudge生成
}
```

**注意:** ユーザーの`app_version`は`/api/mobile/profile`更新時に保存される（既存機能）。

### 7.2.4 バージョン分岐ロジック

| クライアントバージョン | Backend応答 | Day1（iOS） | Day2+（LLM） | 結果 |
|---------------------|-------------|-------------|--------------|------|
| 1.5.x以前 | OLD_SCHEDULE_MAP | 旧スケジュール | 旧スケジュール | ✅ 一致 |
| 1.6.0以降 | NEW_SCHEDULE_MAP | 新スケジュール | 新スケジュール | ✅ 一致 |
| バージョン未指定 | OLD_SCHEDULE_MAP | 旧スケジュール | 旧スケジュール | ✅ 安全側 |

### 7.3 ロールバック計画

| シナリオ | 対応 | 即時性 |
|---------|------|--------|
| Backend問題（新スケジュール） | `NEW_SCHEDULE_MIN_VERSION`を`99.0.0`に変更してデプロイ | ✅ 即時（全ユーザーに旧スケジュール適用） |
| iOS問題（新アプリ） | App Storeでバージョン取り下げ + 次回iOS修正 | ⚠️ 数時間 |
| 両方問題 | Backendロールバック + iOS取り下げ | ⚠️ 数時間 |

### 7.4 旧設定削除条件

| 条件 | 閾値 | アクション |
|------|------|----------|
| iOS 1.6.0以降の更新率 | 95%以上 | `OLD_SCHEDULE_MAP`削除可、`getScheduleMap`簡素化 |
| 重大バグ発生 | - | 即時ロールバック |
| ユーザー苦情 | 5件以上/日 | 調査・判断 |

---

## 8. リスクと対策

| リスク | 影響 | 対策 |
|-------|------|------|
| iOS/Backend不一致 | LLM Nudgeが間違った時間に表示 | 両方同時にデプロイ、テストで確認 |
| テスト失敗 | ビルドエラー | テストを先に修正 |
| ユーザー混乱 | 通知時間が変わる | リリースノートで説明 |

---

## 9. 承認チェックリスト

| 項目 | 状態 |
|------|------|
| [ ] エビデンスベースの設計確認 | |
| [ ] 時間帯重複なし確認（全スロット15分以上間隔） | |
| [ ] iOS/Backend一致確認（自動テストで検証） | |
| [ ] テスト計画確認（間隔検証・一致検証・バージョン分岐テスト含む） | |
| [ ] バージョン分岐実装確認（getScheduleMap + X-App-Version） | |
| [ ] デプロイ手順確認 | |
| [ ] ロールバック手順確認 | |
| [ ] リスク対策確認 | |

---

## 10. レビュー履歴

| 日付 | レビュアー | 結果 | 指摘事項 |
|------|----------|------|---------|
| 2026-02-02 | Codex (gpt-5.2-codex) | ❌ 3 blocking, 2 advisory | 方針矛盾、デプロイ順、ロールバック、テスト不足 |
| 2026-02-02 | Claude Code | 修正完了 | 上記全て対応 |
| 2026-02-02 | Codex (gpt-5.2-codex) | ❌ 1 blocking | Feature Flagがグローバルのみで旧iOSユーザー不整合 |
| 2026-02-02 | Claude Code | 修正完了 | バージョン分岐（getScheduleMap + X-App-Versionヘッダー）追加 |
| 2026-02-02 | Codex (gpt-5.2-codex) | ❌ 2 blocking, 2 advisory | Flag/分岐二重化、ヘッダースコープ不明、compareVersions未定義、SCHEDULE_MAP直参照 |
| 2026-02-02 | Claude Code | 修正完了 | Feature Flag廃止、エンドポイントスコープ明記、semver使用明記、deprecation注記追加 |
| 2026-02-02 | Codex (gpt-5.2-codex) | ❌ 1 blocking | Feature Flag関連の記述が残存（5.4対策、6.2テスト、9チェックリスト） |
| 2026-02-02 | Claude Code | 修正完了 | Feature Flag記述を全て削除、バージョン分岐に統一 |
| 2026-02-02 | Codex (gpt-5.2-codex) | ⚠️ 0 blocking, 2 advisory | 3.2間隔分析のtrim前/後不明、3.3の10問題=30回の前提不明 |
| 2026-02-02 | Claude Code | 修正完了 | trim前を明記、夜更かし含む場合の数値を追記 |

---

**最終更新:** 2026-02-02
