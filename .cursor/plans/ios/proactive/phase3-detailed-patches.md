# Phase 3 詳細パッチ仕様書

> 作成日: 2025-01-18
> 目的: phase3-implementation-spec.md の補完として、各機能のAS-IS/TO-BE/具体的パッチを記載

---

## 目次

1. [通知タップ → NudgeCardView フロー](#1-通知タップ--nudgecardview-フロー)
2. [課題追加シート](#2-課題追加シート)
3. [testNotification メソッド](#3-testnotification-メソッド)
4. [NudgeContent 英語版翻訳](#4-nudgecontent-英語版翻訳)
5. [深掘り質問 英語版翻訳](#5-深掘り質問-英語版翻訳)
6. [Tell Anicca（メモリ機能）](#6-tell-aniccaメモリ機能)
7. [カスタム問題サポート](#7-カスタム問題サポート)
8. [ProblemType.swift ローカライズ](#8-problemtypeswift-ローカライズ)
9. [まとめ](#9-まとめ)

---

## 1. 通知タップ → NudgeCardView フロー

### AS-IS（現状）

**✅ 完全に実装済み**

**AppDelegate.swift (L122-148)**:
```swift
func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse, withCompletionHandler completionHandler: @escaping () -> Void) {
    // ...
    if ProblemNotificationScheduler.isProblemNudge(identifier: notificationIdentifier) {
        switch identifier {
        case UNNotificationDefaultActionIdentifier,
             NotificationScheduler.Action.startConversation.rawValue:
            if let nudgeContent = ProblemNotificationScheduler.nudgeContent(from: content.userInfo) {
                Task { @MainActor in
                    AppState.shared.showNudgeCard(nudgeContent)
                }
            }
        // ...
        }
    }
}
```

**MainTabView.swift (L32-50)**:
```swift
.fullScreenCover(item: $appState.pendingNudgeCard) { content in
    NudgeCardView(
        content: content,
        onPositiveAction: { appState.dismissNudgeCard() },
        onNegativeAction: { appState.dismissNudgeCard() },
        onFeedback: { isPositive in /* TODO: Analytics */ },
        onDismiss: { appState.dismissNudgeCard() }
    )
}
```

**NudgeCardView.swift**: 完全実装済み（1ボタン/2ボタンモード、フィードバックボタン）

### TO-BE

変更不要

### パッチ

なし（実装済み）

---

## 2. 課題追加シート

### AS-IS（現状）

**MyPathTabView.swift**:
- AddProblemSheetは**存在しない**
- `userProblems`は`appState.userProfile.struggles`を使用（L48-49）
- 課題追加UIなし
- DeepDiveSheetViewに削除ボタンなし

**StrugglesStepView.swift**（オンボーディング用）:
- FlowLayout + chipButton パターンが実装済み
- 複数選択（`Set<String>`）+ 次へボタン

**UserProfile.swift**:
- `struggles` と `problems` は同じ配列（L93-96でaliasとして定義）

### TO-BE

1. MyPathTabViewに「+」ボタン追加（navigation bar）
2. AddProblemSheetView を新規作成
   - 13個の問題タイプをFlowLayoutチップで表示
   - 既に選択済みの問題は非表示（フィルタ）
   - 複数選択可能（Set<String>）
   - 「追加」ボタンで一括追加
3. DeepDiveSheetViewに「この問題を削除」ボタン追加
   - AlertDialogで確認

### パッチ

#### MyPathTabView.swift - State追加

```swift
// L6に追加
@State private var showAddSheet = false
```

#### MyPathTabView.swift - Toolbar追加

```swift
// L40の.navigationTitle("My Path")の後に追加
.toolbar {
    ToolbarItem(placement: .topBarTrailing) {
        Button(action: { showAddSheet = true }) {
            Image(systemName: "plus")
                .foregroundStyle(AppTheme.Colors.buttonSelected)
        }
    }
}
.sheet(isPresented: $showAddSheet) {
    AddProblemSheetView()
}
```

#### 新規: AddProblemSheetView

```swift
// MARK: - AddProblemSheetView
struct AddProblemSheetView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss

    @State private var selected: Set<String> = []

    private let allProblems: [String] = [
        "staying_up_late", "cant_wake_up", "self_loathing",
        "rumination", "procrastination", "anxiety",
        "lying", "bad_mouthing", "porn_addiction",
        "alcohol_dependency", "anger", "obsessive",
        "loneliness"
    ]

    private var availableProblems: [String] {
        let current = Set(appState.userProfile.problems)
        return allProblems.filter { !current.contains($0) }
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Text(String(localized: "add_problem_title"))
                    .font(.title2.weight(.semibold))
                    .foregroundStyle(AppTheme.Colors.label)
                    .padding(.top, 24)

                Text(String(localized: "add_problem_subtitle"))
                    .font(.subheadline)
                    .foregroundStyle(AppTheme.Colors.secondaryLabel)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)

                if availableProblems.isEmpty {
                    emptyStateView
                } else {
                    ScrollView {
                        FlowLayout(spacing: 12) {
                            ForEach(availableProblems, id: \.self) { key in
                                chipButton(key: key)
                            }
                        }
                        .padding(.horizontal, 24)
                    }
                }

                Spacer()

                PrimaryButton(
                    title: String(localized: "add_problem_add_button"),
                    isEnabled: !selected.isEmpty,
                    style: .large
                ) {
                    addSelectedProblems()
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 32)
            }
            .background(AppBackground())
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: { dismiss() }) {
                        Image(systemName: "xmark")
                            .foregroundStyle(AppTheme.Colors.secondaryLabel)
                    }
                }
            }
        }
    }

    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 48))
                .foregroundStyle(AppTheme.Colors.buttonSelected)
            Text(String(localized: "add_problem_all_selected"))
                .font(.headline)
                .foregroundStyle(AppTheme.Colors.label)
        }
        .padding(40)
    }

    @ViewBuilder
    private func chipButton(key: String) -> some View {
        let isSelected = selected.contains(key)
        Button {
            if isSelected {
                selected.remove(key)
            } else {
                selected.insert(key)
            }
        } label: {
            Text(NSLocalizedString("problem_\(key)", comment: ""))
                .font(.system(size: 16, weight: .medium))
                .fixedSize(horizontal: true, vertical: false)
                .padding(.horizontal, 20)
                .padding(.vertical, 14)
                .background(isSelected ? AppTheme.Colors.buttonSelected : AppTheme.Colors.buttonUnselected)
                .foregroundStyle(isSelected ? AppTheme.Colors.buttonTextSelected : AppTheme.Colors.label)
                .clipShape(Capsule())
        }
        .buttonStyle(.plain)
    }

    private func addSelectedProblems() {
        var profile = appState.userProfile
        profile.problems.append(contentsOf: selected)
        appState.updateUserProfile(profile, sync: true)
        dismiss()
    }
}
```

#### DeepDiveSheetView - 削除ボタン追加

```swift
// DeepDiveSheetView に以下を追加

// L118の後に State 追加
@State private var showDeleteAlert = false
@EnvironmentObject private var appState: AppState

// L163の .padding(.bottom, 40) の前に追加
// 削除ボタン
Button(role: .destructive, action: { showDeleteAlert = true }) {
    HStack {
        Image(systemName: "trash")
        Text(String(localized: "deep_dive_delete_problem"))
    }
    .font(.subheadline.weight(.medium))
    .foregroundStyle(.red)
}
.padding(.top, 24)
.padding(.horizontal, 20)
.alert(String(localized: "deep_dive_delete_alert_title"), isPresented: $showDeleteAlert) {
    Button(String(localized: "common_cancel"), role: .cancel) { }
    Button(String(localized: "common_delete"), role: .destructive) {
        deleteProblem()
    }
} message: {
    Text(String(localized: "deep_dive_delete_alert_message"))
}

// private func 追加
private func deleteProblem() {
    var profile = appState.userProfile
    profile.problems.removeAll { $0 == problem.rawValue }
    appState.updateUserProfile(profile, sync: true)
    dismiss()
}
```

### ローカライズキー

| Key | 日本語 | English |
|-----|--------|---------|
| `add_problem_title` | 向き合いたい問題を追加 | Add Problems to Face |
| `add_problem_subtitle` | 追加したい問題を選択してください | Select the problems you want to add |
| `add_problem_add_button` | 追加する | Add |
| `add_problem_all_selected` | すべての問題が選択されています | All problems are already selected |
| `deep_dive_delete_problem` | この問題を削除 | Delete this problem |
| `deep_dive_delete_alert_title` | 問題を削除しますか？ | Delete this problem? |
| `deep_dive_delete_alert_message` | この問題は My Path から削除されます | This problem will be removed from My Path |

---

## 3. testNotification メソッド

### AS-IS（現状）

**ProblemNotificationScheduler.swift** (存在する):
- `scheduleNotifications(for:)` - 複数問題をスケジュール
- `cancelAllNotifications()` - 全てキャンセル
- `testNotification` メソッドは**存在しない**

### TO-BE

デバッグ/テスト用に、指定した問題の通知を即座（5秒後）に発火するメソッドを追加。

### パッチ

```swift
// L79の後（cancelAllNotifications関数の後）に追加

#if DEBUG
/// テスト用: 指定した問題の通知を5秒後に発火
func testNotification(for problem: ProblemType) async {
    let content = NudgeContent.contentForToday(for: problem)

    let notificationContent = UNMutableNotificationContent()
    notificationContent.title = problem.notificationTitle
    notificationContent.body = content.notificationText
    notificationContent.categoryIdentifier = Category.problemNudge.rawValue
    notificationContent.sound = .default

    notificationContent.userInfo = [
        "problemType": problem.rawValue,
        "notificationText": content.notificationText,
        "detailText": content.detailText,
        "variantIndex": content.variantIndex
    ]

    if #available(iOS 15.0, *) {
        notificationContent.interruptionLevel = .active
    }

    let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 5, repeats: false)
    let identifier = "TEST_PROBLEM_\(problem.rawValue)_\(Date().timeIntervalSince1970)"
    let request = UNNotificationRequest(
        identifier: identifier,
        content: notificationContent,
        trigger: trigger
    )

    do {
        try await center.add(request)
        logger.info("Test notification scheduled for \(problem.rawValue)")
    } catch {
        logger.error("Failed to schedule test notification: \(error.localizedDescription)")
    }
}
#endif
```

---

## 4. NudgeContent 英語版翻訳

### AS-IS（現状）

**NudgeContent.swift**:
- 日本語ハードコード
- 13問題タイプ × 通知文言(1-3バリアント) × 詳細文言(1-3バリアント)
- 計65+の文言

### TO-BE

ローカライズキーを使用して言語切り替え対応。

### パッチ（NudgeContent.swift）

```swift
// notificationMessages をローカライズ化
static func notificationMessages(for problem: ProblemType) -> [String] {
    switch problem {
    case .stayingUpLate:
        return [
            String(localized: "nudge_staying_up_late_notification_1"),
            String(localized: "nudge_staying_up_late_notification_2"),
            String(localized: "nudge_staying_up_late_notification_3")
        ]
    case .cantWakeUp:
        return [
            String(localized: "nudge_cant_wake_up_notification_1"),
            String(localized: "nudge_cant_wake_up_notification_2"),
            String(localized: "nudge_cant_wake_up_notification_3")
        ]
    // ... 他の問題も同様のパターン
    }
}

static func detailMessages(for problem: ProblemType) -> [String] {
    switch problem {
    case .stayingUpLate:
        return [
            String(localized: "nudge_staying_up_late_detail_1"),
            String(localized: "nudge_staying_up_late_detail_2"),
            String(localized: "nudge_staying_up_late_detail_3")
        ]
    // ... 他の問題も同様のパターン
    }
}
```

### ローカライズキー

#### staying_up_late (夜更かし)

| Key | 日本語 | English |
|-----|--------|---------|
| `nudge_staying_up_late_notification_1` | スクロールより、呼吸。 | Breathe, don't scroll. |
| `nudge_staying_up_late_notification_2` | その「あと5分だけ」で、何年失ってきた？ | How many years have you lost to "just 5 more minutes"? |
| `nudge_staying_up_late_notification_3` | 明日の自分、泣くよ。 | Tomorrow's you will regret this. |
| `nudge_staying_up_late_detail_1` | 夜更かしは明日の自分を傷つける行為。今夜は画面を閉じよう。 | Staying up late hurts tomorrow's you. Close that screen tonight. |
| `nudge_staying_up_late_detail_2` | 睡眠不足の脳は酔っ払いと同じ判断力。明日の自分を守るために、今夜は休もう。 | A sleep-deprived brain has the judgment of a drunk. Rest tonight to protect tomorrow's you. |
| `nudge_staying_up_late_detail_3` | 今スクロールしてる内容、明日覚えてる？でも睡眠不足は確実に残る。 | Will you remember what you're scrolling? But the sleep deprivation will definitely stay. |

#### cant_wake_up (起きられない)

| Key | 日本語 | English |
|-----|--------|---------|
| `nudge_cant_wake_up_notification_1` | 起きないと、今日が始まらん。 | Your day won't start until you get up. |
| `nudge_cant_wake_up_notification_2` | あと5分の君、信用ゼロ。 | The "5 more minutes" you has zero credibility. |
| `nudge_cant_wake_up_notification_3` | Stay Mediocre | Stay Mediocre |
| `nudge_cant_wake_up_detail_1` | 布団の中で何も変わらない。まず足を床につけよう。 | Nothing changes under the blanket. Put your feet on the floor first. |
| `nudge_cant_wake_up_detail_2` | 「あと5分」を何回言った？今起きれば、今日の自分を好きになれる。 | How many times have you said "5 more minutes"? Get up now, and you'll like today's you. |
| `nudge_cant_wake_up_detail_3` | 平凡なままでいい？今起きれば、今日は違う1日になる。 | Want to stay average? Get up now, and today will be different. |

#### self_loathing (自己嫌悪)

| Key | 日本語 | English |
|-----|--------|---------|
| `nudge_self_loathing_notification_1` | 今日も生きてる。それだけで十分。 | You're alive today. That's enough. |
| `nudge_self_loathing_notification_2` | 自分を責めるのは、もうやめていい。 | It's okay to stop blaming yourself. |
| `nudge_self_loathing_notification_3` | あなたは思ってるより、ずっといい人だよ。 | You're a much better person than you think. |
| `nudge_self_loathing_detail_1` | 自己嫌悪は、自分を良くしようとしている証拠。でもその方法は逆効果。今日できた小さなことを1つ思い出してみて。 | Self-loathing shows you want to improve. But it's counterproductive. Remember one small thing you did well today. |
| `nudge_self_loathing_detail_2` | 完璧じゃなくていい。今のあなたで十分。 | You don't have to be perfect. You're enough as you are. |
| `nudge_self_loathing_detail_3` | 自分に厳しすぎる。他の人にするように、自分にも優しくしていい。 | You're too hard on yourself. Be kind to yourself like you would to others. |

#### rumination (反芻思考)

| Key | 日本語 | English |
|-----|--------|---------|
| `nudge_rumination_notification_1` | 今、何を感じてる？ | What are you feeling right now? |
| `nudge_rumination_notification_2` | Are you present right now? | Are you present right now? |
| `nudge_rumination_notification_3` | 朝の5分、瞑想してみない？ | Why not meditate for 5 minutes this morning? |
| `nudge_rumination_detail_1` | 頭の中のループに気づいた？気づいたなら、もう半分解決してる。今この瞬間に戻ろう。 | Noticed the loop in your head? Noticing it means you're halfway there. Come back to this moment. |
| `nudge_rumination_detail_2` | 過去でも未来でもなく、今ここにいる？深呼吸して、今の身体の感覚に意識を向けてみて。 | Are you here now, not in the past or future? Take a deep breath and notice how your body feels. |
| `nudge_rumination_detail_3` | 反芻を止める最も効果的な方法は瞑想。今朝5分だけ、呼吸に集中してみよう。 | Meditation is the most effective way to stop rumination. Focus on your breath for just 5 minutes. |

#### procrastination (先延ばし)

| Key | 日本語 | English |
|-----|--------|---------|
| `nudge_procrastination_notification_1` | 5分だけ。それだけでいい。 | Just 5 minutes. That's all you need. |
| `nudge_procrastination_notification_2` | また自分との約束、破る？ | Breaking another promise to yourself? |
| `nudge_procrastination_notification_3` | やらない理由、全部言い訳。 | Every reason not to do it is an excuse. |
| `nudge_procrastination_detail_1` | 完璧にやる必要はない。5分だけ始めれば、続けられる。 | You don't have to do it perfectly. Start for 5 minutes and you can keep going. |
| `nudge_procrastination_detail_2` | 先延ばしは未来の自分を苦しめる。今やれば、未来の自分が感謝する。 | Procrastination hurts future you. Do it now and future you will thank you. |
| `nudge_procrastination_detail_3` | 本当にできない？それとも、やりたくないだけ？正直になろう。 | Can't you really do it? Or do you just not want to? Be honest. |

#### anxiety (不安)

| Key | 日本語 | English |
|-----|--------|---------|
| `nudge_anxiety_notification_1` | 今この瞬間、あなたは安全。 | In this moment, you are safe. |
| `nudge_anxiety_notification_2` | 今、何を感じてる？ | What are you feeling right now? |
| `nudge_anxiety_notification_3` | 深呼吸。4秒吸って、4秒止めて、4秒吐く。 | Deep breath. Inhale 4 seconds, hold 4, exhale 4. |
| `nudge_anxiety_detail_1` | 不安は未来への恐れ。でも今この瞬間は、何も起きていない。深呼吸して、今に戻ろう。 | Anxiety is fear of the future. But nothing is happening right now. Breathe and come back to now. |
| `nudge_anxiety_detail_2` | 不安に気づいた？気づいたなら、それを観察してみて。不安は来て、去っていく。 | Noticed your anxiety? Watch it. Anxiety comes and goes. |
| `nudge_anxiety_detail_3` | 身体を落ち着かせれば、心も落ち着く。今すぐやってみて。 | Calm your body, calm your mind. Try it now. |

#### lying (嘘)

| Key | 日本語 | English |
|-----|--------|---------|
| `nudge_lying_notification_1` | 今日は正直に生きる日。 | Today is a day to live honestly. |
| `nudge_lying_detail_1` | 嘘は一時的に楽でも、長期的には自分を苦しめる。今日は誠実でいよう。 | Lies may be easy short-term, but they hurt you long-term. Be truthful today. |

#### bad_mouthing (悪口)

| Key | 日本語 | English |
|-----|--------|---------|
| `nudge_bad_mouthing_notification_1` | 今日は誰かを傷つける言葉を使わない。 | No hurtful words today. |
| `nudge_bad_mouthing_notification_2` | その言葉、自分に言われたらどう感じる？ | How would you feel if someone said that to you? |
| `nudge_bad_mouthing_detail_1` | 悪口は言った瞬間気持ちいいかもしれない。でも後から自己嫌悪が来る。今日は善い言葉だけ。 | Gossip feels good in the moment. But self-loathing follows. Only kind words today. |
| `nudge_bad_mouthing_detail_2` | 言う前に一呼吸。相手の立場に立ってみよう。 | Take a breath before speaking. Put yourself in their shoes. |

#### porn_addiction (ポルノ依存)

| Key | 日本語 | English |
|-----|--------|---------|
| `nudge_porn_addiction_notification_1` | 誘惑に勝てば、明日の自分が変わる。 | Beat the temptation and tomorrow's you will change. |
| `nudge_porn_addiction_notification_2` | 本当にそれが欲しい？それとも逃げたいだけ？ | Do you really want it? Or are you just escaping? |
| `nudge_porn_addiction_detail_1` | 今の衝動は一時的。5分待てば、衝動は去る。その5分を乗り越えよう。 | This urge is temporary. Wait 5 minutes and it'll pass. Get through those 5 minutes. |
| `nudge_porn_addiction_detail_2` | ポルノは一時的な逃避。根本の問題は解決しない。今何から逃げようとしてる？ | Porn is temporary escape. It doesn't solve the root problem. What are you running from? |

#### alcohol_dependency (アルコール依存)

| Key | 日本語 | English |
|-----|--------|---------|
| `nudge_alcohol_dependency_notification_1` | 今夜は飲まない。それだけで勝ち。 | Don't drink tonight. That alone is a win. |
| `nudge_alcohol_dependency_notification_2` | 飲まなくても、リラックスできる。 | You can relax without drinking. |
| `nudge_alcohol_dependency_detail_1` | 1日だけ。今夜だけ我慢しよう。明日の朝、自分を誇れる。 | Just today. Just tonight. You'll be proud tomorrow morning. |
| `nudge_alcohol_dependency_detail_2` | お酒なしでストレス解消する方法を試してみて。散歩、深呼吸、音楽。 | Try stress relief without alcohol. A walk, deep breaths, music. |

#### anger (怒り)

| Key | 日本語 | English |
|-----|--------|---------|
| `nudge_anger_notification_1` | 怒りは自分を傷つける。深呼吸。 | Anger hurts you. Take a deep breath. |
| `nudge_anger_notification_2` | 3秒待ってから、話そう。 | Wait 3 seconds before speaking. |
| `nudge_anger_detail_1` | 怒りを持ち続けるのは、自分が毒を飲んで相手が死ぬのを待つようなもの。手放そう。 | Holding onto anger is like drinking poison expecting the other person to die. Let it go. |
| `nudge_anger_detail_2` | 怒りに任せて話すと後悔する。3秒だけ待とう。 | Speaking in anger leads to regret. Wait just 3 seconds. |

#### obsessive (強迫)

| Key | 日本語 | English |
|-----|--------|---------|
| `nudge_obsessive_notification_1` | 完璧じゃなくていい。手放していい。 | It doesn't have to be perfect. You can let go. |
| `nudge_obsessive_notification_2` | その考え、何回目？ | How many times have you thought that? |
| `nudge_obsessive_notification_3` | 考えすぎてない？ | Aren't you overthinking? |
| `nudge_obsessive_detail_1` | その考え、本当に重要？今手放しても、何も悪いことは起きない。 | Is that thought really important? Nothing bad happens if you let it go now. |
| `nudge_obsessive_detail_2` | 同じことを考え続けても、答えは変わらない。今は手放して、後で考えよう。 | Thinking the same thing won't change the answer. Let go now, think later. |
| `nudge_obsessive_detail_3` | 考えることと、実際に行動することは違う。今は考えるのをやめて、動いてみよう。 | Thinking and acting are different. Stop thinking, start moving. |

#### loneliness (孤独)

| Key | 日本語 | English |
|-----|--------|---------|
| `nudge_loneliness_notification_1` | 一人じゃない。誰かがあなたを想ってる。 | You're not alone. Someone is thinking of you. |
| `nudge_loneliness_notification_2` | 大切な人に、一言送ってみない？ | Why not send a message to someone you care about? |
| `nudge_loneliness_detail_1` | 孤独を感じても、それは真実じゃない。今日、誰かに連絡してみない？ | Feeling lonely doesn't make it true. Why not reach out to someone today? |
| `nudge_loneliness_detail_2` | つながりは待っていても来ない。自分から動こう。 | Connection won't come to you. Make the first move. |

---

## 5. 深掘り質問 英語版翻訳

> ⚠️ **重要**: このセクションは**廃止**。オープンエンド形式の質問ではなく、**選択肢形式**の質問を使用すること。
>
> **正しいローカライズキー**: `phase3-implementation-spec.md` の Section 6.4 を参照。
> - 日本語: `deepdive_{problem}_q{n}` + `deepdive_{problem}_q{n}_opt{m}`
> - 英語: 同上（Section 6.4に完全版あり）

### AS-IS（現状）

MyPathTabView.swift L184-292 に日本語ハードコード（65質問）→ **オープンエンド形式は廃止**

### TO-BE

**選択肢形式**のローカライズキーを使用（`phase3-implementation-spec.md` Section 6.4参照）

### パッチ

```swift
enum DeepDiveQuestions {
    static func questions(for problem: ProblemType) -> [String] {
        switch problem {
        case .stayingUpLate:
            return [
                String(localized: "deep_dive_staying_up_late_q1"),
                String(localized: "deep_dive_staying_up_late_q2"),
                String(localized: "deep_dive_staying_up_late_q3"),
                String(localized: "deep_dive_staying_up_late_q4"),
                String(localized: "deep_dive_staying_up_late_q5")
            ]
        // ... 他の問題も同様のパターン
        }
    }
}
```

### ローカライズキー

#### staying_up_late

| Key | 日本語 | English |
|-----|--------|---------|
| `deep_dive_staying_up_late_q1` | 夜更かしをやめられない本当の理由は何だと思う？ | What do you think is the real reason you can't stop staying up late? |
| `deep_dive_staying_up_late_q2` | その時間に何をしてる？スマホ？SNS？YouTube？ | What are you doing at that time? Phone? Social media? YouTube? |
| `deep_dive_staying_up_late_q3` | 理想の就寝時間は何時？なぜその時間？ | What's your ideal bedtime? Why that time? |
| `deep_dive_staying_up_late_q4` | 夜更かしをやめたら、明日の自分はどう変わると思う？ | How do you think tomorrow's you will change if you stop staying up late? |
| `deep_dive_staying_up_late_q5` | 今夜、就寝時間を守るために何ができる？ | What can you do tonight to stick to your bedtime? |

#### cant_wake_up

| Key | 日本語 | English |
|-----|--------|---------|
| `deep_dive_cant_wake_up_q1` | 理想の起床時間は何時？ | What's your ideal wake-up time? |
| `deep_dive_cant_wake_up_q2` | 起きられない朝、何を感じてる？ | What do you feel on mornings you can't get up? |
| `deep_dive_cant_wake_up_q3` | 前日の夜、何時に寝てる？ | What time do you go to bed the night before? |
| `deep_dive_cant_wake_up_q4` | 起きた後、最初にしたいことは何？ | What's the first thing you want to do after waking up? |
| `deep_dive_cant_wake_up_q5` | 朝が楽しみになるとしたら、何がある？ | What would make you look forward to mornings? |

#### self_loathing

| Key | 日本語 | English |
|-----|--------|---------|
| `deep_dive_self_loathing_q1` | 自分を責める時、何について責めてる？ | When you blame yourself, what are you blaming yourself for? |
| `deep_dive_self_loathing_q2` | その基準は誰が決めたもの？ | Who set those standards? |
| `deep_dive_self_loathing_q3` | 友達が同じ状況だったら、何て言う？ | If a friend was in the same situation, what would you say? |
| `deep_dive_self_loathing_q4` | 今日、自分を許せることは1つある？ | Is there one thing you can forgive yourself for today? |
| `deep_dive_self_loathing_q5` | 自分の良いところを3つ挙げるとしたら？ | What are 3 good things about yourself? |

#### rumination

| Key | 日本語 | English |
|-----|--------|---------|
| `deep_dive_rumination_q1` | 同じ考えが頭の中でループする時、何について考えてる？ | When the same thoughts loop in your head, what are you thinking about? |
| `deep_dive_rumination_q2` | その考えを止められない理由は何だと思う？ | Why do you think you can't stop those thoughts? |
| `deep_dive_rumination_q3` | 考えることで何か解決してる？ | Is thinking about it solving anything? |
| `deep_dive_rumination_q4` | 今この瞬間、身体はどう感じてる？ | Right now, how does your body feel? |
| `deep_dive_rumination_q5` | 5分間、呼吸だけに集中できる？ | Can you focus only on breathing for 5 minutes? |

#### procrastination

| Key | 日本語 | English |
|-----|--------|---------|
| `deep_dive_procrastination_q1` | 今、先延ばしにしていることは何？ | What are you procrastinating on right now? |
| `deep_dive_procrastination_q2` | なぜそれを避けてる？本当の理由は？ | Why are you avoiding it? What's the real reason? |
| `deep_dive_procrastination_q3` | 5分だけやるとしたら、何から始める？ | If you were to do it for just 5 minutes, where would you start? |
| `deep_dive_procrastination_q4` | それを終わらせた自分を想像してみて。どう感じる？ | Imagine yourself having finished it. How does that feel? |
| `deep_dive_procrastination_q5` | 今すぐできる最小の一歩は何？ | What's the smallest step you can take right now? |

#### anxiety

| Key | 日本語 | English |
|-----|--------|---------|
| `deep_dive_anxiety_q1` | 今、何について不安を感じてる？ | What are you anxious about right now? |
| `deep_dive_anxiety_q2` | その不安は現実に起きてる？それとも想像？ | Is that anxiety happening in reality? Or is it imagined? |
| `deep_dive_anxiety_q3` | 最悪のケースが起きたら、どう対処する？ | If the worst case happens, how would you cope? |
| `deep_dive_anxiety_q4` | 今この瞬間、安全？ | Are you safe right now? |
| `deep_dive_anxiety_q5` | 深呼吸を3回してみて。何か変わった？ | Try 3 deep breaths. Did anything change? |

#### lying

| Key | 日本語 | English |
|-----|--------|---------|
| `deep_dive_lying_q1` | 最近、嘘をついたのはいつ？ | When was the last time you lied? |
| `deep_dive_lying_q2` | なぜ嘘をつく必要があった？ | Why did you feel the need to lie? |
| `deep_dive_lying_q3` | 本当のことを言ったらどうなってた？ | What would have happened if you told the truth? |
| `deep_dive_lying_q4` | 誠実でいることの難しさは何？ | What makes being honest difficult? |
| `deep_dive_lying_q5` | 今日、正直でいられる小さな機会は何？ | What's a small opportunity to be honest today? |

#### bad_mouthing

| Key | 日本語 | English |
|-----|--------|---------|
| `deep_dive_bad_mouthing_q1` | 最近、誰かの悪口を言った？ | Have you said something bad about someone recently? |
| `deep_dive_bad_mouthing_q2` | なぜその人について話したくなった？ | Why did you want to talk about that person? |
| `deep_dive_bad_mouthing_q3` | 悪口を言った後、どう感じた？ | How did you feel after badmouthing them? |
| `deep_dive_bad_mouthing_q4` | その人に直接言えることはある？ | Is there something you could say directly to them? |
| `deep_dive_bad_mouthing_q5` | 今日、誰かを褒める機会は何？ | What's an opportunity to compliment someone today? |

#### porn_addiction

| Key | 日本語 | English |
|-----|--------|---------|
| `deep_dive_porn_addiction_q1` | ポルノを見たくなるのはどんな時？ | When do you feel the urge to watch porn? |
| `deep_dive_porn_addiction_q2` | その時、何から逃げようとしてる？ | What are you trying to escape from at that moment? |
| `deep_dive_porn_addiction_q3` | 見た後、どう感じる？ | How do you feel after watching? |
| `deep_dive_porn_addiction_q4` | 本当に欲しいものは何？ | What do you really want? |
| `deep_dive_porn_addiction_q5` | 衝動が来た時、代わりにできることは何？ | When the urge comes, what can you do instead? |

#### alcohol_dependency

| Key | 日本語 | English |
|-----|--------|---------|
| `deep_dive_alcohol_dependency_q1` | お酒を飲みたくなるのはどんな時？ | When do you feel the urge to drink? |
| `deep_dive_alcohol_dependency_q2` | お酒なしでリラックスする方法は何？ | How can you relax without alcohol? |
| `deep_dive_alcohol_dependency_q3` | 飲まなかった翌朝、どう感じる？ | How do you feel the morning after not drinking? |
| `deep_dive_alcohol_dependency_q4` | お酒がなくても楽しめる活動は何？ | What activities can you enjoy without alcohol? |
| `deep_dive_alcohol_dependency_q5` | 今週、1日だけ飲まない日を作れる？ | Can you have one alcohol-free day this week? |

#### anger

| Key | 日本語 | English |
|-----|--------|---------|
| `deep_dive_anger_q1` | 最近、怒りを感じたのはいつ？ | When was the last time you felt angry? |
| `deep_dive_anger_q2` | 怒りの下にある感情は何？（傷つき？恐れ？） | What emotion is under the anger? (Hurt? Fear?) |
| `deep_dive_anger_q3` | 怒りを持ち続けると誰が一番傷つく？ | Who gets hurt most when you hold onto anger? |
| `deep_dive_anger_q4` | その怒りを手放すために何ができる？ | What can you do to let go of that anger? |
| `deep_dive_anger_q5` | 怒りを感じた時、3秒待てる？ | When you feel angry, can you wait 3 seconds? |

#### obsessive

| Key | 日本語 | English |
|-----|--------|---------|
| `deep_dive_obsessive_q1` | 何について考えすぎてる？ | What are you overthinking about? |
| `deep_dive_obsessive_q2` | その考えをコントロールしたい？それとも手放したい？ | Do you want to control those thoughts? Or let them go? |
| `deep_dive_obsessive_q3` | 完璧じゃなくていいとしたら、何が変わる？ | What would change if it didn't have to be perfect? |
| `deep_dive_obsessive_q4` | 今、手放しても大丈夫なことは何？ | What's okay to let go of right now? |
| `deep_dive_obsessive_q5` | 考えることと行動すること、どちらに時間を使ってる？ | Which do you spend more time on—thinking or acting? |

#### loneliness

| Key | 日本語 | English |
|-----|--------|---------|
| `deep_dive_loneliness_q1` | 孤独を感じるのはどんな時？ | When do you feel lonely? |
| `deep_dive_loneliness_q2` | つながりたい人は誰？ | Who do you want to connect with? |
| `deep_dive_loneliness_q3` | 最後に誰かに連絡したのはいつ？ | When was the last time you reached out to someone? |
| `deep_dive_loneliness_q4` | 一人でいることと孤独を感じることの違いは？ | What's the difference between being alone and feeling lonely? |
| `deep_dive_loneliness_q5` | 今日、誰かに一言メッセージを送れる？ | Can you send someone a message today? |

---

## 6. Tell Anicca（メモリ機能）

### AS-IS（現状）

**存在しない**:
- Memory.swift モデル
- Tell Anicca UI（DeepDiveSheetViewの一部として計画）
- メモリ保存/読み込み機能

### TO-BE

DeepDiveSheetView に「Tell Anicca」テキストフィールドを追加:
- 空文字は保存しない
- 保存時にトリム
- 各問題タイプごとに最大1つのメモリ

### パッチ

#### 新規: Memory.swift

```swift
import Foundation

/// ユーザーが各問題について Anicca に伝えたいこと
struct Memory: Codable, Identifiable {
    let id: UUID
    let problemType: String
    let text: String
    let createdAt: Date
    let updatedAt: Date

    init(problemType: ProblemType, text: String) {
        self.id = UUID()
        self.problemType = problemType.rawValue
        self.text = text.trimmingCharacters(in: .whitespacesAndNewlines)
        self.createdAt = Date()
        self.updatedAt = Date()
    }
}

// MARK: - MemoryStore
final class MemoryStore: ObservableObject {
    static let shared = MemoryStore()

    @Published private(set) var memories: [String: Memory] = [:]  // problemType -> Memory

    private let userDefaultsKey = "anicca_memories"

    private init() {
        loadFromStorage()
    }

    /// メモリを保存（空文字は保存しない）
    func save(text: String, for problem: ProblemType) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            // 空文字の場合は削除
            memories.removeValue(forKey: problem.rawValue)
            saveToStorage()
            return
        }

        let memory = Memory(problemType: problem, text: trimmed)
        memories[problem.rawValue] = memory
        saveToStorage()
    }

    /// 特定の問題のメモリを取得
    func memory(for problem: ProblemType) -> Memory? {
        return memories[problem.rawValue]
    }

    /// 特定の問題のメモリを削除
    func delete(for problem: ProblemType) {
        memories.removeValue(forKey: problem.rawValue)
        saveToStorage()
    }

    private func saveToStorage() {
        if let encoded = try? JSONEncoder().encode(Array(memories.values)) {
            UserDefaults.standard.set(encoded, forKey: userDefaultsKey)
        }
    }

    private func loadFromStorage() {
        guard let data = UserDefaults.standard.data(forKey: userDefaultsKey),
              let decoded = try? JSONDecoder().decode([Memory].self, from: data) else {
            return
        }
        memories = Dictionary(uniqueKeysWithValues: decoded.map { ($0.problemType, $0) })
    }
}
```

#### DeepDiveSheetView - Tell Anicca 追加

```swift
// DeepDiveSheetView に追加

// State追加
@State private var memoryText: String = ""
@StateObject private var memoryStore = MemoryStore.shared

// onAppear で既存メモリを読み込み
.onAppear {
    memoryText = memoryStore.memory(for: problem)?.text ?? ""
}

// UI追加（質問リストの後、削除ボタンの前）
// Tell Anicca セクション
VStack(alignment: .leading, spacing: 12) {
    HStack {
        Text(String(localized: "deep_dive_tell_anicca_title"))
            .font(.headline)
            .foregroundStyle(AppTheme.Colors.label)
        Spacer()
        if !memoryText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            Button(action: saveMemory) {
                Text(String(localized: "common_save"))
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(AppTheme.Colors.buttonSelected)
            }
        }
    }

    Text(String(localized: "deep_dive_tell_anicca_subtitle"))
        .font(.caption)
        .foregroundStyle(AppTheme.Colors.secondaryLabel)

    TextEditor(text: $memoryText)
        .frame(minHeight: 100)
        .padding(12)
        .background(AppTheme.Colors.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: 12))
}
.padding(.horizontal, 20)
.padding(.top, 24)

// 保存関数
private func saveMemory() {
    memoryStore.save(text: memoryText, for: problem)
}
```

### ローカライズキー

| Key | 日本語 | English |
|-----|--------|---------|
| `deep_dive_tell_anicca_title` | Aniccaに伝える | Tell Anicca |
| `deep_dive_tell_anicca_subtitle` | この問題について、Aniccaに知っておいてほしいことを書いてください | Write anything you want Anicca to know about this problem |

---

## 7. カスタム問題サポート

### AS-IS（現状）

ProblemNotificationScheduler.swift:
- `scheduleNotifications(for problems: [String])` は `ProblemType(rawValue:)` でパースできるものだけ処理
- カスタム問題（ユーザー定義）は**サポートなし**

### TO-BE

**Phase 3ではカスタム問題は未実装**（13問題タイプのみ）

スペックによると、カスタム問題は将来の機能として計画されているが、Phase 3では13問題タイプのみ。

### パッチ

**変更不要**（Phase 3では13問題タイプのみ）

---

## 8. ProblemType.swift ローカライズ

### AS-IS（現状）

**ローカライズ済み**:
- `displayName` → `String(localized: "problem_\(self.rawValue)")`

**ハードコード**:
- `positiveButtonText` → 日本語直書き（L80-108）
- `negativeButtonText` → 日本語直書き（L112-138）
- `notificationTitle` → 日本語直書き（L193-222）

### TO-BE

すべてローカライズキーを使用

### パッチ

```swift
// positiveButtonText をローカライズ
var positiveButtonText: String {
    String(localized: "problem_\(self.rawValue)_positive_button")
}

// negativeButtonText をローカライズ
var negativeButtonText: String? {
    guard !hasSingleButton else { return nil }
    return String(localized: "problem_\(self.rawValue)_negative_button")
}

// notificationTitle をローカライズ
var notificationTitle: String {
    String(localized: "problem_\(self.rawValue)_notification_title")
}
```

### ローカライズキー

| Key | 日本語 | English |
|-----|--------|---------|
| `problem_staying_up_late_positive_button` | 明日を守る 💪 | Protect Tomorrow 💪 |
| `problem_staying_up_late_negative_button` | 傷つける | Hurt Myself |
| `problem_staying_up_late_notification_title` | 就寝 | Bedtime |
| `problem_cant_wake_up_positive_button` | 今日を始める ☀️ | Start Today ☀️ |
| `problem_cant_wake_up_negative_button` | 逃げる | Escape |
| `problem_cant_wake_up_notification_title` | 起床 | Wake Up |
| `problem_self_loathing_positive_button` | 自分を許す 🤍 | Forgive Myself 🤍 |
| `problem_self_loathing_notification_title` | Self-Compassion | Self-Compassion |
| `problem_rumination_positive_button` | 今に戻る 🧘 | Return to Now 🧘 |
| `problem_rumination_negative_button` | 考え続ける | Keep Thinking |
| `problem_rumination_notification_title` | 今ここに | Be Present |
| `problem_procrastination_positive_button` | 5分やる ⚡ | Do 5 Minutes ⚡ |
| `problem_procrastination_negative_button` | 後回し | Later |
| `problem_procrastination_notification_title` | 今すぐ | Now |
| `problem_anxiety_positive_button` | 深呼吸する 🌬️ | Take a Breath 🌬️ |
| `problem_anxiety_notification_title` | 安心 | Peace |
| `problem_lying_positive_button` | 誠実でいる 🤝 | Be Honest 🤝 |
| `problem_lying_negative_button` | 嘘をつく | Tell a Lie |
| `problem_lying_notification_title` | 誠実 | Honesty |
| `problem_bad_mouthing_positive_button` | 善い言葉を使う 💬 | Use Kind Words 💬 |
| `problem_bad_mouthing_negative_button` | 悪口を言う | Badmouth |
| `problem_bad_mouthing_notification_title` | 善い言葉 | Kind Words |
| `problem_porn_addiction_positive_button` | 誘惑に勝つ 💪 | Beat Temptation 💪 |
| `problem_porn_addiction_negative_button` | 負ける | Give In |
| `problem_porn_addiction_notification_title` | 克服 | Overcome |
| `problem_alcohol_dependency_positive_button` | 今夜は飲まない 🍵 | No Drinks Tonight 🍵 |
| `problem_alcohol_dependency_negative_button` | 飲む | Drink |
| `problem_alcohol_dependency_notification_title` | 禁酒 | Sobriety |
| `problem_anger_positive_button` | 手放す 🕊️ | Let Go 🕊️ |
| `problem_anger_negative_button` | 怒り続ける | Stay Angry |
| `problem_anger_notification_title` | 平静 | Calm |
| `problem_obsessive_positive_button` | 手放す 🌿 | Let Go 🌿 |
| `problem_obsessive_negative_button` | 考え続ける | Keep Obsessing |
| `problem_obsessive_notification_title` | 解放 | Release |
| `problem_loneliness_positive_button` | 誰かに連絡する 📱 | Reach Out 📱 |
| `problem_loneliness_notification_title` | つながり | Connection |

---

## 9. まとめ

### 検証完了項目

| # | 項目 | 状態 | 必要な作業 |
|---|------|------|-----------|
| 1 | 通知タップ → NudgeCardView | ✅ 実装済み | なし |
| 2 | 課題追加シート | ❌ 未実装 | AddProblemSheetView新規作成、削除ボタン追加 |
| 3 | testNotification | ❌ 未実装 | DEBUGメソッド追加 |
| 4 | NudgeContent英語版 | ❌ 未実装 | ローカライズキー追加（約45キー） |
| 5 | 深掘り質問英語版 | ❌ 未実装 | ローカライズキー追加（65キー） |
| 6 | Tell Anicca | ❌ 未実装 | Memory.swift新規、UI追加 |
| 7 | カスタム問題 | N/A | Phase 3では未実装（将来機能） |
| 8 | ProblemType.swiftローカライズ | ❌ 未実装 | ローカライズキー追加（約30キー） |

### 新規ファイル

- `Memory.swift` - メモリモデルとストア
- `AddProblemSheetView` - MyPathTabView.swift内に追加

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `MyPathTabView.swift` | +ボタン、AddProblemSheet、削除ボタン、Tell Anicca |
| `ProblemNotificationScheduler.swift` | testNotification追加 |
| `ProblemType.swift` | ローカライズ化 |
| `NudgeContent.swift` | ローカライズ化 |
| `Localizable.strings (ja)` | 約140キー追加 |
| `Localizable.strings (en)` | 約140キー追加 |

### ローカライズキー総数

- UI系: 約10キー
- NudgeContent: 約45キー
- 深掘り質問: 65キー
- ProblemType: 約30キー
- **合計: 約150キー**
