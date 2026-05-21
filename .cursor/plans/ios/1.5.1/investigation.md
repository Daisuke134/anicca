# v1.5.1 通知システム修正 Spec

## 調査日: 2026-01-30（改訂: 2026-01-30）

---

## 概要（What & Why）

ユーザーが複数の通知バグを報告：
1. Day 2 なのに LLM ナッジが届かない（全部ルールベース）
2. 深夜 2:30/3:30 AM に通知が届く
3. 6:30 AM に3つの通知が同時に届く
4. 1日の中で同じ通知が何回も繰り返される
5. Day 1 で Thompson Sampling が実行されランダム選択になる

**なぜ修正が必要か:** Anicca の核心機能は LLM パーソナライズナッジ。これが動いていないと、ユーザーは Day 1 のルールベースコンテンツを永遠に受け取り続け、解約率が上がる。

---

## DB 調査結果（2026-01-30 時点）

**Production cron は正常動作。LLM 生成も成功している。**

| 指標 | 値 |
|------|-----|
| `decision_point = 'llm_generation'` | 4,010件（96%） |
| `decision_point = 'rule_based'` | 219件（4%） |
| 合計 | 4,229件 |

**問題はサーバー側ではなく、iOS アプリ側にある。**

---

## As-Is（現状の問題）

### P1: レースコンディション — LLM ナッジが使われない（CRITICAL）

**場所:** `AppState.swift:105-121`, `AppState.swift:126-137`

**As-Is:**
```
App起動 → AppState.init()
  ├→ Task 1: fetchTodaysLLMNudges()     ← ネットワーク通信（500ms-5秒）
  └→ Task 2: migrateFromAlarmKit()       ← scheduleNotifications() を即実行
                                            LLMNudgeCache 空 → ルールベースで確定
                                            repeats: true → 毎日同じ内容

  [1-5秒後] fetchTodaysLLMNudges() 完了 → キャッシュ更新
            → しかし再スケジュールなし → LLMコンテンツは永遠に使われない
```

**証拠:** ユーザーが受信した全通知が `Localizable.strings` のハードコードテキストと一致。

| 通知テキスト | Localizable.strings キー |
|-------------|------------------------|
| "This moment of weakness doesn't define you." | `nudge_porn_addiction_notification_8` |
| "Every reason not to do it is an excuse." | `nudge_procrastination_notification_3` |
| "Return to Now" | `problem_rumination_notification_title` |
| "The thought is not you, let it pass." | `nudge_obsessive_notification_1` |
| "Get up now" | `problem_cant_wake_up_notification_title` |
| "Forgive yourself" | `problem_self_loathing_notification_title` |
| "Put the phone down" | `problem_staying_up_late_notification_title` |

**全 scheduleNotifications() 呼び出し箇所で同じ問題:**

| 呼び出し元 | ファイル | LLM fetch を await? |
|-----------|---------|-------------------|
| `markOnboardingComplete()` | `AppState.swift:146-148` | NO |
| `updateUserProfile()` | `AppState.swift:329-332` | NO |
| `checkAndResetMonthly...()` | `AppState.swift:696-698` | NO |
| `migrateFromAlarmKit()` | `AppState.swift:895` | NO |
| `deleteProblem()` | `MyPathTabView.swift:793-796` | NO |
| `saveStruggles()` | `AddProblemSheetView.swift:115` | NO |

---

### P2: 深夜 2-3 AM に通知が届く（HIGH）

**場所:** `ProblemType.swift:59-61`, `ProblemNotificationScheduler.swift:108-121`

**As-Is:**
- 3問題 × 5スロット = 15通知スロット
- 夜間 20:00-23:00 にスロット集中
- 60分間隔 enforcement が後ろに**カスケード（シフト）**し続ける
- `validTimeRange` が `nil` を返す → 時間制限なし（死コード）
- カスケード例: 22:30 → 23:30 → 00:30 → 01:30 → 02:30 → 03:30

---

### P3: 6:30 AM に3つの通知が同時到着（HIGH）

**場所:** `ProblemType.swift` (notificationSchedule), `ProblemNotificationScheduler.swift:108-121`

**As-Is:**
- `cantWakeUp`: (6,0), (6,15), (6,30) — wake window で15分間隔許可
- `anxiety`: (6,30) — 同時刻衝突
- 結果: 6:00, 6:15, 6:30 に3つの通知がほぼ同時に届く
- カスケードロジックが衝突を**シフト**で解消しようとする → 更なる問題を引き起こす

---

### P4: 同じ通知が1日に何回も繰り返される（MEDIUM）

**場所:** `NudgeContentSelector.swift`, `LLMNudgeCache.swift`

**As-Is:**
- Thompson Sampling が各タイムスロットで独立実行（Day 1 含む）
- Day 1 でも Beta(1,1) = 一様分布 = 事実上ランダム選択
- 「今日使用済みバリアント」のトラッキングなし
- `LLMNudgeCache.cacheByHour` キーが `"problem_hour"` → minute 無視 → キー衝突
- `getNudge()` が30分ファジーウィンドウ → 隣接スロットが同じナッジを返す

---

### P5: Day 1 が決定論的でない（HIGH）

**場所:** `NudgeContentSelector.swift:153-156`

**As-Is:**
- Day 1 でも Thompson Sampling が実行される（日付による分岐なし）
- Beta(1,1) の一様分布でバリアント選択 → 毎回ランダム
- 同じバリアントが複数スロットで選ばれる可能性あり
- ユーザーの初日体験が不安定

---

### P6: staying_up_late のスケジュールが不正（MEDIUM）

**場所:** `ProblemType.swift` (notificationSchedule)

**As-Is:**
- 現在: (20,30), (21,30), (22,30), (23,30), (7,30) — 7:30 AM が含まれている
- 7:30 AM は夜更かし防止の文脈で不適切
- 0:00/1:00 の深夜フォローアップは time-specific variant としてのみ存在（NudgeContentSelector 内）
- notificationSchedule 自体には 0:00/1:00 が含まれていない

---

## To-Be（修正後の設計）

### Fix P1: LLM fetch → 再スケジュールの保証 + `repeats: false` 移行

**方針:**
1. `fetchTodaysLLMNudges()` 完了後に必ず `scheduleNotifications()` を呼ぶ
2. `repeats: true` → `repeats: false` に変更（コンテンツ焼き付け問題の根本修正）

**`repeats: true` の問題:**
- `UNCalendarNotificationTrigger(repeats: true)` はスケジュール時にコンテンツを**焼き付ける**
- LLM fetch が後から完了しても、既にスケジュールされた通知のコンテンツは**更新されない**
- 結果: ユーザーは永遠にルールベースのハードコードテキストを受け取り続ける

```
App起動 → AppState.init()
  ├→ Task 1: fetchTodaysLLMNudges()
  │    → 成功: LLMNudgeCache 更新 → removeAllPending → scheduleNotifications() ← NEW
  │    → 失敗: ログ出力（ルールベースのまま）
  └→ Task 2: migrateFromAlarmKit() → scheduleNotifications()（初回、ルールベース）

結果: 初回はルールベースで即座にスケジュール → LLM 取得後に全削除→再スケジュール（最新コンテンツ）
```

**`repeats: false` への移行:**
```swift
// Before:
let trigger = UNCalendarNotificationTrigger(dateMatching: dateComponents, repeats: true)

// After:
let trigger = UNCalendarNotificationTrigger(dateMatching: dateComponents, repeats: false)
```
- 毎日 LLM fetch 後に `removeAllPendingNotificationRequests()` → `scheduleNotifications()` で再スケジュール
- LLM fetch は毎朝サーバー cron（5:00 JST）で生成済み → アプリ起動時に最新を取得

**変更ファイル:**
- `AppState.swift` — `fetchTodaysLLMNudges()` に再スケジュールロジック追加
- `ProblemNotificationScheduler.swift` — `repeats: true` → `repeats: false`

**未起動日対策（2日分スケジュール）:**
- `repeats: false` だとアプリ未起動日に翌日の通知が欠落する
- **対策:** スケジュール時に**今日+明日の2日分**をスケジュールする
- 今日分: LLM コンテンツ（取得済みなら）orルールベース
- 明日分: ルールベースのみ（LLM は未生成のため）
- 翌日アプリ起動時に明日分を LLM で再スケジュール（上書き）
- **最悪ケース:** 2日間アプリ未起動 → 2日目はルールベースで通知される（完全欠落よりマシ）

**追加検討:**
- `LLMNudgeCache` にディスク永続化を追加（UserDefaults）→ 次回起動時にキャッシュが残る
- フォアグラウンド復帰時にも fetch + 再スケジュール
- BGAppRefreshTask で日次再スケジュール（iOS がバックグラウンドで起こしてくれる、ただし保証なし）

---

### Fix P2: 深夜通知の防止

**方針:** `validTimeRange` を実装し、範囲外のスロットは**スキップ**する。カスケードしない。

```swift
// ProblemType.swift
var validTimeRange: (startHour: Int, startMinute: Int, endHour: Int, endMinute: Int)? {
    switch self {
    case .stayingUpLate, .pornAddiction:
        // 深夜許可: ピーク 22:00-01:00 の介入が核心
        return (startHour: 6, startMinute: 0, endHour: 1, endMinute: 30)  // 6:00-01:30（翌日跨ぎ）
    default:
        return (startHour: 6, startMinute: 0, endHour: 23, endMinute: 0)  // 6:00-23:00（23:00以降は sleep 問題のみ）
    }
}
```

**変更ファイル:**
- `ProblemType.swift` — `validTimeRange` の実装
- `ProblemNotificationScheduler.swift` — 範囲外スロットをスキップするロジック

---

### Fix P3: タイムスロット再設計 + カスケード削除

**方針:** 全13問題のタイムスロットを再設計し、どの組み合わせでも絶対にバッティングしない。カスケードロジックは完全削除。

**核心ルール:**
- 全67スロットがユニーク（同一時刻は存在しない）
- カスケード/シフトロジックは**完全削除**（そもそもバッティングしないので不要）

**間隔ルール（適用範囲別）:**

| 適用対象 | 最低間隔 | 根拠 |
|---------|---------|------|
| ルールベース固定スロット（異なる問題間） | **15分** | 設計で保証済み。全67スロットがユニーク |
| ルールベース固定スロット（同一問題内） | **30分以上** | 各問題のスロット設計で保証済み（cant_wake_up wake window の6:00-6:30のみ15分許可） |
| LLM プロンプト DON'T（異なる問題間） | **30分** | サーバーに指示。万が一近すぎる場合は `logIntervalWarnings` で警告（配信はそのまま） |
| LLM プロンプト（同一問題内） | **60分** | 既存ルール維持 |
| `logIntervalWarnings` 閾値 | **30分** | 30分未満で警告ログ出力 |

**新タイムスロット（全67スロット、バッティングゼロ）:**

| # | 問題タイプ | スロット1 | スロット2 | スロット3 | スロット4 | スロット5 | スロット6 |
|---|-----------|----------|----------|----------|----------|----------|----------|
| 1 | staying_up_late | 20:00 | 21:00 | 22:00 | 23:00 | 0:00 | 1:00 |
| 2 | porn_addiction | 20:30 | 21:30 | 22:30 | 23:30 | 0:30 | 1:30 |
| 3 | cant_wake_up | 6:00 | 6:15 | 6:30 | 8:00 | 22:15 |  |
| 4 | self_loathing | 7:00 | 12:00 | 14:45 | 17:00 | 19:00 |  |
| 5 | rumination | 8:30 | 18:00 | 19:30 | 21:15 | 22:45 |  |
| 6 | procrastination | 9:00 | 11:00 | 13:00 | 15:00 | 18:30 |  |
| 7 | anxiety | 7:30 | 10:00 | 14:00 | 17:30 | 20:45 |  |
| 8 | lying | 8:15 | 11:30 | 14:30 | 16:30 | 19:15 |  |
| 9 | bad_mouthing | 9:30 | 12:30 | 15:30 | 18:15 | 21:45 |  |
| 10 | alcohol_dependency | 16:00 | 17:15 | 18:45 | 19:45 | 20:15 |  |
| 11 | anger | 7:45 | 10:45 | 13:30 | 15:45 | 16:45 |  |
| 12 | obsessive | 8:45 | 10:30 | 12:15 | 14:15 | 17:45 |  |
| 13 | loneliness | 9:15 | 11:15 | 13:45 | 15:15 | 16:15 |  |

**変更ファイル:**
- `ProblemType.swift` — `notificationSchedule` を新タイムスロットに書き換え
- `ProblemNotificationScheduler.swift` — カスケードロジック完全削除

---

### Fix P4: 通知内容の重複排除

**方針:** Thompson Sampling に「今日使用済みバリアント」セットを渡し、未使用バリアントを優先。

```swift
// NudgeContentSelector.swift
func selectVariant(for problem: ProblemType, scheduledHour: Int,
                   usedVariants: Set<Int> = [])  // NEW parameter
```

**変更ファイル:**
- `NudgeContentSelector.swift` — 重複排除ロジック追加
- `LLMNudgeCache.swift` — `cacheByHour` 削除、`cacheByTime` のみ使用
- `ProblemNotificationScheduler.swift` — スケジュールループで使用済みバリアントを追跡

---

### Fix P5: Day 1 決定論的バリアント割り当て

**方針:** Day 1 は Thompson Sampling を使わない。各スロットに順番にバリアントを固定割り当てする。

**Day 1 ルール:**
- スロット 1 → バリアント 0
- スロット 2 → バリアント 1
- スロット 3 → バリアント 2
- スロット 4 → バリアント 3
- スロット 5 → バリアント 4
- スロット 6 → バリアント 5（6スロット問題: staying_up_late, porn_addiction のみ）
- 同じ日に同じバリアントは絶対に来ない
- **staying_up_late 例外（時間対応割り当て）:** スロット4-6は時刻依存テキストと一致させるため順番割り当てではなく時間対応割り当て（5,3,4）を使用:
  - スロット 4（23:00）→ バリアント 5: "Put down your phone. Now."（時間非依存）
  - スロット 5（0:00）→ バリアント 3: "It's past midnight..."（midnight = 0:00 ✅）
  - スロット 6（1:00）→ バリアント 4: "It's 1 AM..."（1 AM = 1:00 ✅）

**Day 2+ ルール:**
- LLM ナッジが存在 → LLM コンテンツを使用（Thompson Sampling 不要）
- LLM ナッジが無い → Thompson Sampling でバリアント選択（ただし usedVariants で重複排除）

**具体例: anxiety のみ選択、Day 1**

| スロット | 時間 | バリアント# | 通知テキスト |
|---------|------|-----------|-------------|
| 1 | 7:30 | 0 | "In this moment, you are safe." |
| 2 | 10:00 | 1 | "Anxiety lies. Right now, you are okay." |
| 3 | 14:00 | 2 | "You've survived 100% of your worst days." |
| 4 | 17:30 | 3 | "Name 3 things you can see right now." |
| 5 | 20:45 | 4 | "Your body is safe. Your mind is lying." |

**変更ファイル:**
- `NudgeContentSelector.swift` — Day 1 分岐追加（`isFirstDay` チェック）

---

### Fix P6: staying_up_late スケジュール修正

**方針:** 7:30 AM を削除。0:00 と 1:00 を正規スロットとして追加。合計6スロット。

**Before:**
```
(20,30), (21,30), (22,30), (23,30), (7,30)  — 5スロット
+ time-specific variant で 0:00/1:00 にアクセス可能（カスケード経由）
```

**After:**
```
(20,0), (21,0), (22,0), (23,0), (0,0), (1,0)  — 6スロット
7:30 AM は削除
0:00/1:00 は正規スロット（カスケード不要）
```

**porn_addiction も同様:**
```
Before: (20,0), (21,30), (22,30), (23,30), (7,30)
After:  (20,30), (21,30), (22,30), (23,30), (0,30), (1,30)  — 6スロット
```

**変更ファイル:**
- `ProblemType.swift` — `notificationSchedule` 修正
- `NudgeContentSelector.swift` — time-specific variant ロジックを調整（0:00/1:00 が正規スロットになったため）

---

## 最適通知タイミング（研究ベース）

Web検索で得られたベストプラクティス:

| 知見 | 根拠 | Anicca への適用 |
|------|------|----------------|
| 行動変容アプリは **8 PM 配信で3.5倍**のエンゲージメント | JMIR mHealth 2023 | evening スロットを重視（現状の設計と一致） |
| **1日3回バッチ配信**でストレス減少 | ScienceDirect バッチング研究 | 5回/日は多い可能性。将来的に3回に削減検討 |
| **週5回以上**で60%がアプリ削除 | UX研究 | 5回/日×7日=35回/週 → 疲労リスク高い |
| 依存症アプリは**渇望ピーク時が最適** | Springer JITAI研究 | staying_up_late/porn_addiction の夜間スロットは正しい |
| **21:00-8:00 は避けるべき**（一般アプリ） | Silent Hours研究 | staying_up_late/porn_addiction は例外（深夜が核心） |
| **パーソナライゼーションが最重要**（依存症） | Curb Health研究 | Day 2+ の LLM パーソナライズは正しい方向 |

**結論:** 現在の時間設計は研究と概ね一致。staying_up_late/porn_addiction の深夜許可は科学的に正当。将来的に頻度を5→3回に削減検討。

---

## 受け入れ条件

| # | 条件 | テスト可能 |
|---|------|-----------|
| 1 | Day 2+ ユーザーが LLM 生成コンテンツの通知を受け取る | YES |
| 2 | 深夜 0:00-5:59 に通知が届かない（staying_up_late/porn_addiction は 0:00-1:30 まで許可） | YES |
| 3 | 全問題のタイムスロットがユニーク（バッティングゼロ）。カスケードロジック削除済み | YES |
| 4 | 1日の中で同じ通知テキストが2回以上届かない | YES |
| 5 | LLM fetch 失敗時はルールベースにフォールバック（クラッシュしない） | YES |
| 6 | Day 1 は決定論的バリアント割り当て（スロット1→バリアント0, スロット2→バリアント1...） | YES |
| 7 | カスケードロジックが完全に削除されている | YES |
| 8 | staying_up_late は 20:00, 21:00, 22:00, 23:00, 0:00, 1:00 の6スロット（7:30 なし） | YES |
| 9 | `repeats: false` でスケジュールされている（LLM fetch 後に再スケジュール） | YES |
| 10 | LLM プロンプトに異なる問題間30分以上の DON'T が含まれている | YES |
| 11 | `logIntervalWarnings` が30分未満で警告する | YES |
| 12 | Debug: LLM カードプレビューボタンが実際の LLM 生成カードを表示する | YES |
| 13 | 13問題全選択時（67 > 64）、ソート順末尾3件ドロップ（日跨ぎ0:00-1:30は翌日=最遅扱い。ドロップ: porn 1:30, staying 1:00, porn 0:30） | YES |
| 14 | アプリ未起動日でも通知が届く（2日分スケジュール） | YES |
| 15 | 全バリアントの EN/JA ローカリゼーションが同数存在する（Localizable.strings） | YES |

---

## テストマトリックス

| # | To-Be | テスト名 | カバー |
|---|-------|----------|--------|
| 1 | LLM fetch 後に再スケジュール | `test_rescheduleAfterLLMFetch` | ✅ |
| 2 | LLM fetch 失敗時のフォールバック | `test_fallbackOnLLMFetchFailure` | ✅ |
| 3 | validTimeRange 外のスロットがスキップされる | `test_skipSlotsOutsideValidRange` | ✅ |
| 4 | 全スロットがユニーク（バッティングなし） | `test_allSlotsUnique_noDuplicates` | ✅ |
| 5 | カスケードロジックが存在しない | `test_noCascadeLogicExists` | ✅ |
| 6 | cant_wake_up の wake window が15分間隔 | `test_wakeWindowAllows15minInterval` | ✅ |
| 7 | Day 1 で決定論的バリアント割り当て | `test_day1DeterministicVariants` | ✅ |
| 8 | Day 1 で同じバリアントが重複しない | `test_day1NoDuplicateVariants` | ✅ |
| 9 | Day 2+ Thompson Sampling が使用済みバリアントを避ける | `test_day2AvoidUsedVariants` | ✅ |
| 10 | LLMNudgeCache がキー衝突しない | `test_cacheNoKeyCollision` | ✅ |
| 11 | フォアグラウンド復帰時に再 fetch | `test_refetchOnForegroundResume` | ✅ |
| 12 | staying_up_late が6スロット（7:30 なし、0:00/1:00 あり） | `test_stayingUpLate6Slots` | ✅ |
| 13 | 13問題全選択時に64通知制限内 | `test_allProblems64NotificationLimit` | ✅ |
| 14 | 複数問題選択時に時間重複なし | `test_multiProblemNoTimeOverlap` | ✅ |
| 15 | `repeats: false` でスケジュールされる | `test_notificationRepeatsIsFalse` | ✅ |
| 16 | LLM fetch 後に removeAll → 再スケジュール | `test_rescheduleRemovesAllFirst` | ✅ |
| 17 | LLM プロンプトに30分間隔 DON'T が含まれる | `test_promptContainsIntervalDontRule` | ✅ |
| 18 | `logIntervalWarnings` 閾値が30分 | `test_intervalWarningThreshold30min` | ✅ |
| 19 | 64上限時に時刻が最も遅いスロットからドロップ | `test_64LimitDropsLatestSlots` | ✅ |
| 20 | 2日分スケジュール（未起動日対策） | `test_schedules2DaysOfNotifications` | ✅ |
| 21 | 全バリアント EN/JA 同数存在 | `test_allVariantsHaveENandJALocalization` | ✅ |
| 22 | 6スロット問題の Day 1 割り当て（0-5順番） | `test_day1SixSlotProblemVariants0to5` | ✅ |

---

## 追加タスク: LLM Nudge Debug ビュー + カードプレビュー

**目的:** サーバーから取得した LLM ナッジを確認できる UI。LLM が正しく動いているか、ルールベースにフォールバックしていないかを視覚的に検証する。

### 既存の実装

| 機能 | 場所 | 状態 |
|------|------|------|
| 青ドット LLM インジケーター | `NudgeCardView.swift:54-60` | ✅ 実装済み |
| ルールベース Nudge テストボタン（13問題分） | `MyPathTabView.swift:351-371` | ✅ 実装済み |
| モック LLM テストボタン（ハードコード） | `MyPathTabView.swift:376-408` | ✅ 実装済み |
| `LLMNudgeCache.debugSummary()` | `LLMNudgeCache.swift:87-91` | ✅ 実装済み |

### 追加機能 1: Nudge 一覧デバッグビュー

`LLMNudgeDebugView.swift`（`#if DEBUG`）— 今日スケジュールされた全 Nudge を時系列テーブルで表示。

| 表示項目 | 説明 |
|---------|------|
| 時刻 | scheduledTime（時系列ソート） |
| 問題タイプ | ProblemType アイコン + 名前 |
| コンテンツ種別 | LLM / ルールベース |
| Hook テキスト | 通知タイトル |
| Content プレビュー | カード詳細の先頭50文字 |
| tone / reasoning | LLM の場合のみ表示 |

### 追加機能 2: LLM カードプレビューボタン

既存のルールベーステストボタン（13個）のLLM版。**1ボタンのみ。**

- `MyPathTabView` の Debug セクションに「🤖 LLM Nudge Preview」ボタンを追加
- タップ → `LLMNudgeCache` から最初の1件を取得 → `NudgeCardView` で表示
- キャッシュが空の場合 → 「LLM Nudge がまだ取得されていません」アラート
- **ハードコードではなく、サーバーが実際に生成した本物の LLM カード**を表示

### 変更ファイル

- `LLMNudgeCache.swift` — `allCachedNudges` public accessor 追加
- `MyPathTabView.swift` — Debug セクションに LLM プレビューボタン + 一覧ビューリンク追加
- 新規: `Views/Debug/LLMNudgeDebugView.swift`

---

## 追加タスク: LLM プロンプト DON'T + IntervalWarning 閾値変更（Backend）

### LLM プロンプトに DON'T を追加

**場所:** `apps/api/src/jobs/nudgeHelpers.js` — `buildPhase78Prompt()` 667-695行目付近

**現状:**
```
## Nudge Frequency Rules
- Minimum interval: 60 minutes between nudges
- Guideline: 4-8 nudges per day
```

**追加する DON'T（Nudge Frequency Rules セクションに挿入）:**
```
## Nudge Frequency Rules
- Minimum interval: 60 minutes between nudges (EXCEPT cant_wake_up wake window 06:00-06:30: 15 min allowed)
- NEVER schedule multiple nudges at the exact same time
- NEVER schedule nudges for different problem types within 30 minutes of each other
- When a user has multiple problems, view ALL scheduled nudges holistically and ensure no batting
- Guideline: 4-8 nudges per day
```

**Critical Rules セクション（690-695行目）にも追記:**
```
6. When scheduling for multiple problems, ensure at least 30 minutes between ANY two nudges across ALL problem types.
```

### `logIntervalWarnings` 閾値変更

**場所:** `apps/api/src/jobs/nudgeHelpers.js:409`

**Before:** `if (curr - prev < 60)` — 60分未満で警告
**After:** `if (curr - prev < 30)` — 30分未満で警告

**理由:** ルールベースの最小間隔が15分、LLM プロンプトの DON'T が30分。サーバーの警告閾値もこれに合わせる。

**変更ファイル:**
- `apps/api/src/jobs/nudgeHelpers.js` — プロンプト追記 + 閾値変更

---

## リリースフロー

```
Phase 2: 実装完了（TDD）
    ↓
Phase 3: テスト
    ↓
fastlane test — Unit/Integration 全パス
    ↓
fastlane build_for_device — 実機にインストール → ユーザー確認
    ↓
dev にマージ → main にマージ
    ↓
release/1.5.1 ブランチ作成
    ↓
fastlane set_version version:1.5.1
    ↓
What's New 作成（EN/JA）→ Fastfile に設定
    ↓
fastlane full_release（Archive → Upload → 審査提出 全自動）
    ↓
release/1.5.1 → dev にマージ（バージョン同期）
    ↓
完了
```

**重要:** What's New は `fastlane full_release` の**前に**準備する。ASC を開く必要はない。

---

## 境界（やらないこと）

- サーバー側の cron ロジック変更（正常動作確認済み）
- Thompson Sampling アルゴリズム自体の変更（Day 1 分岐と重複排除の追加のみ）
- 新しい問題タイプの追加
- Localizable.strings のコンテンツ変更（**ただし EN/JA 同数保証の確認は行う**）
- 通知頻度の削減（5→3回は将来検討）

---

## ローカリゼーション保証（EN/JA）

**通知テキスト・カード詳細の全バリアントが日本語/英語の両方で存在することを保証する。**

| 確認項目 | 件数 | 確認方法 |
|---------|------|---------|
| 通知テキスト（notification） | 13問題 × 各5-10バリアント = 106件 | `Localizable.strings` の `nudge_*_notification_*` キー |
| カード詳細（card detail） | 13問題 × 各5-10バリアント = 106件 | `Localizable.strings` の `nudge_*_detail_*` キー |
| 通知タイトル | 13件 | `problem_*_notification_title` キー |
| カードタイトル | 13件 | 問題タイプ名 |
| ボタンテキスト | 各問題1-2個 | `nudge_*_button_*` キー |

**保証方法:**
- 実装前に `en.lproj/Localizable.strings` と `ja.lproj/Localizable.strings` の nudge 関連キー数を比較
- 不一致があればビルド前に修正（実装中に確認では漏れる）
- テスト `test_allVariantsHaveENandJALocalization` で自動検証

---

## 実行手順

```bash
# テスト
cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 fastlane test

# 実機ビルド
cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 fastlane build_for_device
```

---

## 修正優先順位

| # | Fix | 優先度 | 複雑度 | 変更ファイル |
|---|-----|--------|--------|-------------|
| 1 | P1: レースコンディション + `repeats: false` 移行 | CRITICAL | Medium | `AppState.swift`, `ProblemNotificationScheduler.swift` |
| 2 | P5: Day 1 決定論的バリアント | HIGH | Low | `NudgeContentSelector.swift` |
| 3 | P3: タイムスロット再設計 + カスケード削除 | HIGH | Medium | `ProblemType.swift`, `ProblemNotificationScheduler.swift` |
| 4 | P2: 深夜通知防止（validTimeRange 実装） | HIGH | Low | `ProblemType.swift`, `ProblemNotificationScheduler.swift` |
| 5 | P6: staying_up_late スケジュール修正 | MEDIUM | Low | `ProblemType.swift`, `NudgeContentSelector.swift` |
| 6 | P4: 通知内容重複排除 | MEDIUM | Medium | `NudgeContentSelector.swift`, `LLMNudgeCache.swift`, `ProblemNotificationScheduler.swift` |
| 7 | Backend: LLM プロンプト DON'T + 閾値変更 | MEDIUM | Low | `apps/api/src/jobs/nudgeHelpers.js` |
| 8 | Debug: LLM Nudge 一覧ビュー + カードプレビュー | MEDIUM | Low | `LLMNudgeCache.swift`, `MyPathTabView.swift`, 新規 `LLMNudgeDebugView.swift` |

---

## リファレンス

- 全13問題タイプのタイミング・コンテンツ一覧: [`nudge-reference.md`](./nudge-reference.md)
- 最適通知タイミング研究:
  - [JMIR mHealth 2023](https://mhealth.jmir.org/2023/1/e38342) — 飲酒削減アプリ、8PM で3.5倍効果
  - [ScienceDirect バッチング研究](https://www.sciencedirect.com/science/article/abs/pii/S0747563219302596) — 1日3回でストレス減少
  - [Springer JITAI 研究](https://link.springer.com/article/10.1007/s40429-020-00322-y) — 依存症の Just-in-Time 介入
  - [Curb Health](https://www.curb.health/post/research-designing-the-perfect-notification-for-an-app-to-support-people-quitting-addictive-habits) — 依存症アプリ通知設計
