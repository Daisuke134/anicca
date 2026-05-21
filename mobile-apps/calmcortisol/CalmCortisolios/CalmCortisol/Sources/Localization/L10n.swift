import Foundation

// iOS 15 compatible localization (Locale.current.language.languageCode is iOS 16+)
private var isJapanese: Bool {
    let lang = Locale.current.languageCode ?? "en"
    return lang.hasPrefix("ja")
}

struct L10n {
    // MARK: - Onboarding
    static var onboardingWelcomeTitle: String { isJapanese ? "CalmCortisol" : "CalmCortisol" }
    static var onboardingWelcomeSubtitle: String { isJapanese ? "ストレスを60秒でリセット" : "Reset Stress in 60 Seconds" }
    static var onboardingWelcomeCTA: String { isJapanese ? "始める" : "Get Started" }

    static var painSelectionTitle: String { isJapanese ? "今一番の悩みは？" : "What's bothering you most?" }
    static var painOptionWork: String { isJapanese ? "仕事のストレス" : "Work Stress" }
    static var painOptionSleep: String { isJapanese ? "眠れない" : "Can't Sleep" }
    static var painOptionAnxiety: String { isJapanese ? "不安・パニック" : "Anxiety / Panic" }
    static var painOptionAnger: String { isJapanese ? "怒り・イライラ" : "Anger / Irritation" }

    static var demoSessionTitle: String { isJapanese ? "体験してみましょう" : "Try a Quick Session" }
    static var demoSessionFeedbackYes: String { isJapanese ? "気持ちよかった" : "Felt Better" }
    static var demoSessionFeedbackNo: String { isJapanese ? "あまり変わらなかった" : "Not Much Change" }

    static var notificationTitle: String { isJapanese ? "AIがあなたを見守ります" : "AI Checks In On You" }
    static var notificationSubtitle: String { isJapanese ? "ストレスが高まる前に先手で介入" : "Intervene before stress spikes" }
    static var notificationAllow: String { isJapanese ? "通知を許可する" : "Allow Notifications" }
    static var notificationSkip: String { isJapanese ? "後で" : "Later" }

    // MARK: - Paywall
    static var paywallHeadline: String { isJapanese ? "無制限の安らぎ、自責ゼロ" : "Unlimited Calm, Zero Guilt" }
    static var paywallFreeTitle: String { isJapanese ? "無料プラン" : "Free Plan" }
    static var paywallFreeDesc: String { isJapanese ? "1日3回まで、ルールベース呼吸法" : "3 sessions/day, rule-based breathing" }
    static var paywallProTitle: String { isJapanese ? "Pro プラン" : "Pro Plan" }
    static var paywallProDesc: String { isJapanese ? "無制限 + AI推薦 + 就寝前セッション" : "Unlimited + AI recommendation + sleep pre-session" }
    static var paywallMonthly: String { isJapanese ? "月額 $9.99" : "$9.99/month" }
    static var paywallAnnual: String { isJapanese ? "年額 $49.99 (58%オフ)" : "$49.99/year (save 58%)" }
    static var paywallCTA: String { isJapanese ? "7日間無料トライアルを始める" : "Start 7-Day Free Trial" }
    static var paywallSkip: String { isJapanese ? "スキップ" : "Skip" }
    static var paywallRestore: String { isJapanese ? "購入を復元" : "Restore Purchases" }

    // MARK: - Main Dashboard
    static var dashboardTitle: String { isJapanese ? "今日のコルチゾール" : "Today's Cortisol" }
    static var dashboardMission: String { isJapanese ? "今日3回セッションしよう" : "Do 3 sessions today" }
    static var dashboardStartCTA: String { isJapanese ? "60秒セッションを始める" : "Start 60-sec Session" }
    static var dashboardSessionCount: String { isJapanese ? "今日のセッション" : "Today's Sessions" }

    // MARK: - Session
    static var sessionTitle: String { isJapanese ? "呼吸セッション" : "Breathing Session" }
    static var sessionComplete: String { isJapanese ? "セッション完了！" : "Session Complete!" }
    static var sessionFeedbackTitle: String { isJapanese ? "どう感じましたか？" : "How do you feel?" }
    static var sessionFeedbackBetter: String { isJapanese ? "楽になった 👍" : "Better 👍" }
    static var sessionFeedbackSame: String { isJapanese ? "あまり変わらない 👎" : "Same 👎" }

    // MARK: - Breathing Types
    static var breathingBoxName: String { isJapanese ? "ボックス呼吸" : "Box Breathing" }
    static var breathingBoxDescription: String { isJapanese ? "4秒×4フェーズ。集中と落ち着きに" : "4-count per phase. Focus & calm." }
    static var breathingFourSevenEightName: String { isJapanese ? "4-7-8 呼吸" : "4-7-8 Breathing" }
    static var breathingFourSevenEightDescription: String { isJapanese ? "睡眠と深いリラックスに" : "Sleep & deep relaxation." }
    static var breathingPhysiologicalSighName: String { isJapanese ? "生理的ため息" : "Physiological Sigh" }
    static var breathingPhysiologicalSighDescription: String { isJapanese ? "即効性の高い緊張解放" : "Quick tension release." }

    // MARK: - Breathing Phases
    static var breathingPhaseInhale: String { isJapanese ? "吸う" : "Inhale" }
    static var breathingPhaseInhale2: String { isJapanese ? "もう一度吸う" : "Inhale again" }
    static var breathingPhaseHold: String { isJapanese ? "止める" : "Hold" }
    static var breathingPhaseExhale: String { isJapanese ? "吐く" : "Exhale" }
    static var breathingPhaseLongExhale: String { isJapanese ? "長く吐く" : "Long exhale" }

    // MARK: - Settings
    static var settingsTitle: String { isJapanese ? "設定" : "Settings" }
    static var settingsPrivacyPolicy: String { isJapanese ? "プライバシーポリシー" : "Privacy Policy" }
    static var settingsTerms: String { isJapanese ? "利用規約" : "Terms of Use" }
    static var settingsRestore: String { isJapanese ? "購入を復元" : "Restore Purchases" }
    static var settingsVersion: String { isJapanese ? "バージョン" : "Version" }
}
