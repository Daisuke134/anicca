/**
 * trend-hunter configuration
 * ProblemType dictionary, rotation groups, virality thresholds
 */

export const PROBLEM_TYPES = [
  'staying_up_late', 'cant_wake_up', 'self_loathing', 'rumination',
  'procrastination', 'anxiety', 'lying', 'bad_mouthing',
  'porn_addiction', 'alcohol_dependency', 'anger', 'obsessive', 'loneliness',
];

// 3-group fixed rotation (v1)
export const ROTATION_GROUPS = [
  ['staying_up_late', 'cant_wake_up', 'self_loathing', 'rumination', 'procrastination'],
  ['anxiety', 'lying', 'bad_mouthing', 'porn_addiction'],
  ['alcohol_dependency', 'anger', 'obsessive', 'loneliness'],
];

// Per-source virality thresholds
export const VIRALITY_THRESHOLDS = {
  x: 1000,
  reddit: 100,
  tiktok: 10000,
  github: 50,
};

export const SIMILARITY_THRESHOLD = 0.7;

export const WARMUP_THRESHOLD = 50;

// ProblemType → search query dictionary
// Each ProblemType has empathy (personal struggle) and solution (how-to) queries
// in both Japanese and English
export const QUERY_DICT = {
  staying_up_late: {
    empathy_ja: '"また3時だ" OR "夜更かし やめられない" OR "寝なきゃいけないのに"',
    empathy_en: '"can\'t stop staying up late" OR "doom scrolling at 3am" OR "revenge bedtime procrastination"',
    solution_ja: '"夜更かし 直す方法" OR "早く寝る コツ" OR "睡眠 改善"',
    solution_en: '"how to fix sleep schedule" OR "screen time before bed" OR "stop staying up late"',
  },
  cant_wake_up: {
    empathy_ja: '"朝起きれない" OR "スヌーズ" OR "二度寝 やめられない"',
    empathy_en: '"can\'t wake up" OR "snooze button" OR "oversleeping every day"',
    solution_ja: '"朝活 コツ" OR "起きる方法" OR "目覚まし 効かない"',
    solution_en: '"how to wake up early" OR "morning routine tips" OR "stop hitting snooze"',
  },
  self_loathing: {
    empathy_ja: '"自分が嫌い" OR "自己嫌悪" OR "ダメな人間"',
    empathy_en: '"I hate myself" OR "self-loathing" OR "I\'m a failure"',
    solution_ja: '"自己肯定感 高める" OR "自分を好きになる" OR "セルフコンパッション"',
    solution_en: '"how to stop hating yourself" OR "self-compassion" OR "building self-worth"',
  },
  rumination: {
    empathy_ja: '"考えすぎ" OR "頭から離れない" OR "ぐるぐる思考"',
    empathy_en: '"can\'t stop overthinking" OR "intrusive thoughts" OR "ruminating all night"',
    solution_ja: '"考えすぎ 止める" OR "マインドフルネス" OR "反芻思考 対策"',
    solution_en: '"how to stop overthinking" OR "breaking the thought loop" OR "mindfulness for anxiety"',
  },
  procrastination: {
    empathy_ja: '"先延ばし" OR "やらなきゃいけないのに" OR "締め切り ギリギリ"',
    empathy_en: '"procrastination is ruining my life" OR "can\'t start anything" OR "always last minute"',
    solution_ja: '"先延ばし 克服" OR "やる気 出す方法" OR "タスク管理"',
    solution_en: '"how to stop procrastinating" OR "productivity tips" OR "overcoming procrastination"',
  },
  anxiety: {
    empathy_ja: '"不安 止まらない" OR "漠然とした不安" OR "将来が怖い"',
    empathy_en: '"anxiety is killing me" OR "constant worry" OR "can\'t stop being anxious"',
    solution_ja: '"不安 解消法" OR "不安障害 対処" OR "リラックス 方法"',
    solution_en: '"how to manage anxiety" OR "anxiety coping strategies" OR "grounding techniques"',
  },
  lying: {
    empathy_ja: '"嘘つき やめたい" OR "つい嘘をつく" OR "本当のことが言えない"',
    empathy_en: '"can\'t stop lying" OR "compulsive liar" OR "I lie about everything"',
    solution_ja: '"嘘 やめる方法" OR "正直になる" OR "自分に正直"',
    solution_en: '"how to stop lying" OR "overcoming compulsive lying" OR "being honest"',
  },
  bad_mouthing: {
    empathy_ja: '"悪口 やめられない" OR "陰口" OR "人の悪口ばかり"',
    empathy_en: '"I gossip too much" OR "can\'t stop talking about people" OR "why do I bad mouth"',
    solution_ja: '"悪口 やめる" OR "ポジティブ 会話" OR "批判 やめたい"',
    solution_en: '"how to stop gossiping" OR "positive communication" OR "stop being negative"',
  },
  porn_addiction: {
    empathy_ja: '"ポルノ やめたい" OR "依存 つらい"',
    empathy_en: '"porn addiction recovery" OR "nofap struggle" OR "can\'t quit"',
    solution_ja: '"ポルノ依存 克服" OR "NoFap" OR "依存 回復"',
    solution_en: '"how to quit porn" OR "nofap tips" OR "overcoming porn addiction"',
  },
  alcohol_dependency: {
    empathy_ja: '"お酒 やめたい" OR "飲みすぎ" OR "アルコール依存"',
    empathy_en: '"I drink too much" OR "alcoholism" OR "can\'t stop drinking"',
    solution_ja: '"禁酒 方法" OR "お酒 減らす" OR "ソバーキュリアス"',
    solution_en: '"how to stop drinking" OR "sober curious" OR "alcohol recovery"',
  },
  anger: {
    empathy_ja: '"怒り 抑えられない" OR "イライラ 止まらない" OR "キレてしまう"',
    empathy_en: '"anger issues" OR "I can\'t control my temper" OR "rage problems"',
    solution_ja: '"怒り コントロール" OR "アンガーマネジメント" OR "冷静になる方法"',
    solution_en: '"anger management tips" OR "how to control anger" OR "calming techniques"',
  },
  obsessive: {
    empathy_ja: '"強迫観念" OR "気になって仕方ない" OR "確認 やめられない"',
    empathy_en: '"OCD is exhausting" OR "obsessive thoughts" OR "can\'t stop checking"',
    solution_ja: '"強迫性障害 対処" OR "OCD 克服" OR "強迫行為 やめる"',
    solution_en: '"how to manage OCD" OR "obsessive thoughts coping" OR "ERP therapy"',
  },
  loneliness: {
    empathy_ja: '"孤独" OR "誰にも会いたくない" OR "一人がつらい"',
    empathy_en: '"so lonely" OR "I have no friends" OR "loneliness is killing me"',
    solution_ja: '"孤独 解消" OR "友達 作り方" OR "一人でも楽しむ"',
    solution_en: '"how to deal with loneliness" OR "making friends as adult" OR "overcoming isolation"',
  },
};

// TikTok hashtag filter keywords (recall-oriented, LLM filters for precision)
export const PROBLEM_TYPE_KEYWORDS = [
  'sleep', 'insomnia', 'nightowl', 'wakeup', 'morning',
  'selfcare', 'selflove', 'selfworth', 'mentalhealth',
  'overthinking', 'anxiety', 'worry', 'stress',
  'procrastination', 'productivity', 'motivation', 'lazy',
  'honesty', 'trust', 'lying',
  'anger', 'angermanagement', 'calm',
  'ocd', 'obsessive', 'intrusive',
  'lonely', 'loneliness', 'alone',
  'addiction', 'sober', 'nofap', 'recovery',
  'habit', 'routine', 'discipline', 'mindset',
  '夜更かし', '朝活', '不安', 'メンタル', '習慣', '依存',
  '自己嫌悪', '先延ばし', '孤独', '怒り',
];

// LLM fallback chain
export const LLM_CHAIN = [
  { model: 'gpt-4o', timeout: 30000 },
  { model: 'gpt-4o-mini', timeout: 20000 },
  { model: 'claude-3-5-haiku', timeout: 20000 },
];

// DLQ configuration
export const DLQ_CONFIG = {
  maxAttempts: 5,
  baseDelayMs: 60000,
  jitterMs: 30000,
  maxDelayMs: 3600000,
};

// TikTok regions to scan
export const TIKTOK_REGIONS = ['JP', 'US', 'GB'];

// TikTok industries that may contain mental health content
export const TIKTOK_RELEVANT_INDUSTRIES = ['Education', 'Life'];
