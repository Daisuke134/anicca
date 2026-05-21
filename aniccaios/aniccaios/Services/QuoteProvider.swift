import Foundation

/// Talk画面の「今日の一言」用。固定30件から day-of-year で1件を返す（パーソナライズ無し）。
final class QuoteProvider {
    static let shared = QuoteProvider()
    private init() {}
    
    func todayQuote(preferredLanguage: LanguagePreference, date: Date, calendar: Calendar = .current) -> String {
        let dayOfYear = calendar.ordinality(of: .day, in: .year, for: date) ?? 1
        let index = (dayOfYear - 1) % Self.quotesEnglish.count
        switch preferredLanguage {
        case .ja:
            return Self.quotesJapanese[index]
        case .en, .de, .fr, .es, .ptBR:
            return Self.quotesEnglish[index]
        }
    }
    
    /// 簡易版: 言語設定を自動検出して今日のQuoteを返す
    func todayQuote() -> String {
        let language = LanguagePreference.detectDefault()
        return todayQuote(preferredLanguage: language, date: Date())
    }
    
    // 30 fixed quotes (quotes-v3.md)
    private static let quotesEnglish: [String] = [
        "Even when you hate yourself, you still deserve gentleness.",
        "You don't have to fix your whole life tonight. One honest step is enough.",
        "The part of you that's hurting is also the part that wants to heal.",
        "You've criticized yourself for years. What if you tried kindness instead?",
        "This is a moment of suffering. May you be kind to yourself.",
        "There is no amount of self-improvement that can make up for a lack of self-acceptance.",
        "Stop beating yourself up for beating yourself up. Just notice, and begin again.",
        "You're not a broken person. You're a healing one.",
        "This breath is the only one that matters right now.",
        "You are not your thoughts. You are the one watching them.",
        "Your senses are always in the present. Return to them when you feel lost.",
        "Your mind is the sky. Thoughts and feelings are merely weather.",
        "The past is gone. The future is not yet. Only this moment is real.",
        "Everything changes. Even this feeling will pass.",
        "Behind all your thoughts, there is a stillness that never leaves.",
        "Today is enough. Tomorrow will take care of itself.",
        "Small changes, repeated, become who you are.",
        "The best time to start was yesterday. The second best time is now.",
        "When you act on your values, happiness follows. Not the other way around.",
        "Courage isn't having no fear. It's moving gently toward what matters.",
        "A jug fills drop by drop. So does a life of meaning.",
        "First, tend to yourself. Then you can tend to others.",
        "You don't need to eliminate negative thoughts. Take them with you and do what matters.",
        "Pain is part of life. Suffering alone is optional.",
        "Your struggles don't define you. How you meet them does.",
        "What you resist persists. What you accept transforms.",
        "You don't have to fight your emotions. Try letting them be.",
        "You only lose what you cling to.",
        "Anger will only burn you. Let it go, not for them, but for yourself.",
        "Like a broken bell that makes no sound, find peace in stillness."
    ]
    
    private static let quotesJapanese: [String] = [
        "自分を嫌いな時でも、あなたは優しくされる価値がある。",
        "今夜、人生のすべてを直す必要はない。誠実な一歩で、十分。",
        "傷ついている部分は、癒されたいと願っている部分でもある。",
        "何年も自分を責めてきた。今度は、優しさを試してみない？",
        "今、苦しいんだね。自分に優しくしていいんだよ。",
        "どれだけ自分を改善しても、自己受容の代わりにはならない。",
        "自分を責めすぎていることを、また責めないで。ただ気づいて、また始めよう。",
        "壊れた人間じゃない。癒えていく途中の人間だ。",
        "今、この呼吸だけが大切。",
        "あなたは思考ではない。思考を見ている存在だ。",
        "五感はいつも今この瞬間にある。迷ったら、感覚に戻ろう。",
        "心は空。思考や感情は、ただ通り過ぎる雲。",
        "過去はもう終わった。未来はまだ来ていない。今だけが、本当。",
        "すべては変わる。この気持ちも、必ず過ぎていく。",
        "どんな思考の奥にも、静けさがある。それは消えない。",
        "今日一日で、十分。明日は明日が面倒を見てくれる。",
        "小さな変化の積み重ねが、あなた自身になる。",
        "始めるのに一番いいタイミングは昨日だった。二番目にいいのは、今。",
        "自分の価値観に沿って動くと、幸せはあとからついてくる。",
        "勇気とは、恐れがないことじゃない。大切なことに向かって、静かに進むこと。",
        "水瓶は一滴ずつ満ちていく。意味のある人生も同じ。",
        "まず自分を整えること。それから他の人に手を差し伸べられる。",
        "ネガティブな思考を消す必要はない。連れていって、大切なことをしよう。",
        "痛みは人生の一部。でも、一人で苦しむ必要はない。",
        "苦しみがあなたを定義するのではない。苦しみとどう向き合うかが、あなたを定義する。",
        "抵抗するものは続く。受け入れるものは変わっていく。",
        "感情と戦わなくていい。ただ、そこにいることを許そう。",
        "失うのは、しがみついているものだけ。",
        "怒りは自分を焼くだけ。手放すのは、相手のためじゃなく、自分のため。",
        "割れた鐘のように静かに。そこに、安らぎがある。"
    ]
}









