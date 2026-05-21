import Foundation

nonisolated struct Affirmation: Sendable {
    let english: String
    let japanese: String

    func text(for language: AppLanguage) -> String {
        switch language {
        case .english: return english
        case .japanese: return japanese
        }
    }
}

nonisolated enum AffirmationData: Sendable {
    static let all: [Affirmation] = [
        Affirmation(english: "I am enough exactly as I am", japanese: "今の自分で十分だ"),
        Affirmation(english: "I choose peace over worry", japanese: "心配より平和を選ぶ"),
        Affirmation(english: "I am grateful for this moment", japanese: "この瞬間に感謝する"),
        Affirmation(english: "I deserve happiness and joy", japanese: "私は幸せと喜びに値する"),
        Affirmation(english: "My potential is limitless", japanese: "私の可能性は無限だ"),
        Affirmation(english: "I release what I cannot control", japanese: "コントロールできないものを手放す"),
        Affirmation(english: "Today I choose to be kind to myself", japanese: "今日は自分に優しくする"),
        Affirmation(english: "I am growing stronger every day", japanese: "毎日少しずつ強くなっている"),
        Affirmation(english: "I attract positivity and abundance", japanese: "ポジティブさと豊かさを引き寄せる"),
        Affirmation(english: "I am worthy of love and respect", japanese: "私は愛と尊敬に値する"),
        Affirmation(english: "Every challenge makes me stronger", japanese: "すべての試練が私を強くする"),
        Affirmation(english: "I trust the journey of my life", japanese: "人生の旅を信じている"),
        Affirmation(english: "I am surrounded by love", japanese: "愛に囲まれている"),
        Affirmation(english: "My heart is open to new experiences", japanese: "新しい経験に心を開いている"),
        Affirmation(english: "I am at peace with my past", japanese: "過去と和解している"),
        Affirmation(english: "I choose joy in every moment", japanese: "毎瞬間に喜びを選ぶ"),
        Affirmation(english: "I am creating the life I desire", japanese: "望む人生を創り出している"),
        Affirmation(english: "I forgive myself and set myself free", japanese: "自分を許し、自由にする"),
        Affirmation(english: "I am a magnet for miracles", japanese: "奇跡を引き寄せる存在だ"),
        Affirmation(english: "Today is full of possibilities", japanese: "今日は可能性に満ちている"),
        Affirmation(english: "I radiate confidence and grace", japanese: "自信と優雅さを放っている"),
        Affirmation(english: "I am exactly where I need to be", japanese: "今いるべき場所にいる"),
        Affirmation(english: "My mind is calm and clear", japanese: "心は穏やかで澄んでいる"),
        Affirmation(english: "I embrace change with open arms", japanese: "変化を両手を広げて受け入れる"),
        Affirmation(english: "I am grateful for my body and health", japanese: "自分の体と健康に感謝する"),
        Affirmation(english: "I let go of fear and embrace faith", japanese: "恐れを手放し、信頼を受け入れる"),
        Affirmation(english: "Every day is a fresh start", japanese: "毎日が新しいスタート"),
        Affirmation(english: "I am worthy of all good things", japanese: "すべての良いことに値する"),
        Affirmation(english: "I choose to see the good in people", japanese: "人の良いところを見ることを選ぶ"),
        Affirmation(english: "My life is a beautiful adventure", japanese: "私の人生は美しい冒険だ"),
        Affirmation(english: "I honor my own rhythm and pace", japanese: "自分のリズムとペースを大切にする"),
        Affirmation(english: "I am connected to the world around me", japanese: "周りの世界とつながっている"),
        Affirmation(english: "I welcome abundance into my life", japanese: "人生に豊かさを迎え入れる"),
        Affirmation(english: "I am proud of how far I have come", japanese: "ここまで来た自分を誇りに思う"),
        Affirmation(english: "I nurture my mind, body, and soul", japanese: "心と体と魂を大切にする"),
        Affirmation(english: "I am resilient and can handle anything", japanese: "回復力があり何でも乗り越えられる"),
        Affirmation(english: "I spread kindness wherever I go", japanese: "どこへ行っても優しさを広げる"),
        Affirmation(english: "My dreams are valid and achievable", japanese: "夢は正当で達成可能だ"),
        Affirmation(english: "I celebrate my small victories", japanese: "小さな勝利を祝う"),
        Affirmation(english: "I am filled with endless creativity", japanese: "無限の創造力に満ちている"),
        Affirmation(english: "I trust myself to make the right choices", japanese: "正しい選択をする自分を信じる"),
        Affirmation(english: "I am becoming the best version of myself", japanese: "最高の自分になりつつある"),
        Affirmation(english: "I choose gratitude over complaint", japanese: "不満より感謝を選ぶ"),
        Affirmation(english: "I am a source of light for others", japanese: "他の人にとっての光の源だ"),
        Affirmation(english: "I breathe in calm and breathe out tension", japanese: "穏やかさを吸い込み、緊張を吐き出す"),
        Affirmation(english: "I am open to receiving blessings", japanese: "恵みを受け取ることに心を開いている"),
        Affirmation(english: "I love the person I am becoming", japanese: "なりつつある自分を愛している"),
        Affirmation(english: "Every setback is a setup for a comeback", japanese: "すべての後退は復活への準備だ"),
        Affirmation(english: "I am patient with myself and my growth", japanese: "自分と自分の成長に忍耐強い"),
        Affirmation(english: "The universe supports my highest good", japanese: "宇宙は私の最善を支えてくれる"),
    ]

    static func random() -> Affirmation {
        all.randomElement() ?? all[0]
    }
}
