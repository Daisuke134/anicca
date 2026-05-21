export interface Verse {
  id: number;
  text: string;
  textJa: string;
  source: string;
  chapter: string;
  verseNumber: string;
  isPremium: boolean;
}

export const verses: Verse[] = [
  {
    id: 1,
    text: "Hatred never ceases by hatred; by love alone is it healed.",
    textJa: "憎しみは憎しみによって消えない。愛によってのみ癒される。",
    source: "Dhammapada",
    chapter: "Chapter 1 (Yamaka Vagga)",
    verseNumber: "Verse 5",
    isPremium: false,
  },
  {
    id: 2,
    text: "All things are impermanent. Work out your salvation with diligence.",
    textJa: "すべては無常である。怠ることなく精進せよ。",
    source: "Dhammapada",
    chapter: "Chapter 20 (Magga Vagga)",
    verseNumber: "Verse 277",
    isPremium: false,
  },
  {
    id: 3,
    text: "Wisdom springs from meditation; without meditation wisdom wanes.",
    textJa: "智慧は瞑想から生まれる。瞑想なくして智慧は衰える。",
    source: "Dhammapada",
    chapter: "Chapter 20 (Magga Vagga)",
    verseNumber: "Verse 282",
    isPremium: false,
  },
  {
    id: 4,
    text: "The mind is everything. What you think, you become.",
    textJa: "心がすべてである。あなたが考えること、それがあなたになる。",
    source: "Dhammapada",
    chapter: "Chapter 1 (Yamaka Vagga)",
    verseNumber: "Verse 1-2",
    isPremium: false,
  },
  {
    id: 5,
    text: "Better than a thousand hollow words is one word that brings peace.",
    textJa: "千の空虚な言葉より、平和をもたらす一言のほうが優れている。",
    source: "Dhammapada",
    chapter: "Chapter 8 (Sahassa Vagga)",
    verseNumber: "Verse 100",
    isPremium: false,
  },
  {
    id: 6,
    text: "Let go of the past, let go of the future. Live fully in the present.",
    textJa: "過去を手放し、未来を手放せ。今この瞬間を十全に生きよ。",
    source: "Dhammapada",
    chapter: "Chapter 24 (Tanha Vagga)",
    verseNumber: "Verse 348",
    isPremium: false,
  },
  {
    id: 7,
    text: "Peace comes from within. Do not seek it without.",
    textJa: "平和は内側からやってくる。外に求めてはならない。",
    source: "Dhammapada",
    chapter: "Traditional Teaching",
    verseNumber: "Paraphrased",
    isPremium: false,
  },
  {
    id: 8,
    text: "Wander alone like a rhinoceros horn.",
    textJa: "犀の角のように、ただひとり歩め。",
    source: "Khaggavisana Sutta",
    chapter: "Rhinoceros Sutra",
    verseNumber: "",
    isPremium: false,
  },
  {
    id: 9,
    text: "You yourself must strive. The Buddhas only point the way.",
    textJa: "あなた自身が精進しなければならない。仏陀はただ道を指し示すだけだ。",
    source: "Dhammapada",
    chapter: "Chapter 20 (Magga Vagga)",
    verseNumber: "Verse 276",
    isPremium: false,
  },
  {
    id: 10,
    text: "There is no fire like passion, no shark like hatred, no snare like folly, no torrent like greed.",
    textJa: "貪欲のような炎なく、憎しみのような猛獣なく、愚かさのような罠なく、欲のような激流なし。",
    source: "Dhammapada",
    chapter: "Chapter 18 (Mala Vagga)",
    verseNumber: "Verse 251",
    isPremium: false,
  },
  {
    id: 11,
    text: "As a solid rock is unshaken by wind, so are the wise unmoved by praise or blame.",
    textJa: "岩が風に揺るがないように、賢者は称賛にも非難にも動じない。",
    source: "Dhammapada",
    chapter: "Chapter 6 (Pandita Vagga)",
    verseNumber: "Verse 81",
    isPremium: true,
  },
  {
    id: 12,
    text: "The wise control their body, speech, and mind. They are truly well-governed.",
    textJa: "賢者は体と言葉と心を制御する。彼らこそ真に自分を治める者だ。",
    source: "Dhammapada",
    chapter: "Chapter 6 (Pandita Vagga)",
    verseNumber: "Verse 80",
    isPremium: true,
  },
  {
    id: 13,
    text: "Those who are free of resentful thoughts surely find peace.",
    textJa: "恨みの思いから解放された者は、必ず平和を見出す。",
    source: "Dhammapada",
    chapter: "Chapter 1 (Yamaka Vagga)",
    verseNumber: "Verse 6",
    isPremium: true,
  },
  {
    id: 14,
    text: "Health is the greatest gift, contentment the greatest wealth, faithfulness the best relationship.",
    textJa: "健康は最高の贈り物、知足は最高の富、誠実さは最善の関係だ。",
    source: "Dhammapada",
    chapter: "Chapter 15 (Sukha Vagga)",
    verseNumber: "Verse 204",
    isPremium: true,
  },
  {
    id: 15,
    text: "Action speaks louder than thought. Put your wisdom into practice today.",
    textJa: "行動は思考よりも雄弁だ。今日、智慧を実践に移せ。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 16,
    text: "Do not dwell in the past, do not dream of the future, concentrate the mind on the present moment.",
    textJa: "過去に囚われず、未来を夢見ず、現在の瞬間に心を集中させよ。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 17,
    text: "A healthy body supports a healthy mind. Cherish both.",
    textJa: "健康な体は健康な心を支える。両方を大切にせよ。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 18,
    text: "What matters most: how you loved, lived, and let go.",
    textJa: "最も大切なことは、いかに愛し、いかに生き、いかに手放したか。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 19,
    text: "Giving brings the giver the greatest joy.",
    textJa: "与えることは、与える者に最大の喜びをもたらす。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 20,
    text: "Share your light freely. It diminishes not by giving.",
    textJa: "あなたの光を惜しみなく分け与えよ。与えても光は減らない。",
    source: "Dhammapada",
    chapter: "Chapter 1",
    verseNumber: "Verse 1",
    isPremium: true,
  },
  {
    id: 21,
    text: "The foot feels the foot when it feels the ground.",
    textJa: "足は地面を踏むとき、足自身を感じる。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 22,
    text: "Set your heart on doing good. Do it over and over again, and you will be filled with joy.",
    textJa: "善を行うことに心を定めよ。繰り返し行えば、喜びで満たされる。",
    source: "Dhammapada",
    chapter: "Chapter 9 (Papa Vagga)",
    verseNumber: "Verse 118",
    isPremium: true,
  },
  {
    id: 23,
    text: "Little by little, drop by drop, the wise fill themselves with good.",
    textJa: "少しずつ、一滴一滴と、賢者は自らを善で満たしていく。",
    source: "Dhammapada",
    chapter: "Chapter 9 (Papa Vagga)",
    verseNumber: "Verse 122",
    isPremium: true,
  },
  {
    id: 24,
    text: "Conquer anger with kindness, evil with good, greed with generosity.",
    textJa: "怒りは優しさで、悪は善で、貪欲は寛大さで征服せよ。",
    source: "Dhammapada",
    chapter: "Chapter 17 (Kodha Vagga)",
    verseNumber: "Verse 223",
    isPremium: true,
  },
  {
    id: 25,
    text: "Pure thoughts bring happiness that follows like an ever-present shadow.",
    textJa: "清らかな思いは、離れない影のように幸福をもたらす。",
    source: "Dhammapada",
    chapter: "Chapter 1 (Yamaka Vagga)",
    verseNumber: "Verse 2",
    isPremium: true,
  },
  {
    id: 26,
    text: "The past is already gone, the future is not yet here. There's only one moment for you to live.",
    textJa: "過去はすでに去り、未来はまだ来ていない。あなたが生きられる瞬間はただ一つ。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 27,
    text: "Few cross to the other shore. Most wander on this side.",
    textJa: "彼岸に渡る者は少ない。多くはこちら岸をさまよい続ける。",
    source: "Dhammapada",
    chapter: "Chapter 6 (Pandita Vagga)",
    verseNumber: "Verse 85",
    isPremium: true,
  },
  {
    id: 28,
    text: "Even death is not to be feared by one who has lived wisely.",
    textJa: "賢く生きた者にとって、死さえも恐れるべきものではない。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 29,
    text: "Our thoughts today shape who we become tomorrow.",
    textJa: "今日の思いが、明日のあなたをつくる。",
    source: "Dhammapada",
    chapter: "Chapter 1",
    verseNumber: "Verse 1-2",
    isPremium: true,
  },
  {
    id: 30,
    text: "Holding anger is like holding a hot coal. You burn yourself.",
    textJa: "怒りを持ち続けることは、熱い炭を掴み続けるようなもの。傷つくのはあなた自身だ。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 31,
    text: "If you knew what I know about the power of giving, you would not let a single meal pass without sharing it in some way.",
    textJa: "与えることの力を私のように知っていれば、一度の食事も誰かと分かち合わずには過ごせないだろう。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 32,
    text: "Thousands of candles can be lit from a single candle, and the life of the candle will not be shortened.",
    textJa: "一本のろうそくから何千本ものろうそくを灯せる。そのろうそくの寿命は縮まない。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 33,
    text: "Whatever a monk keeps pursuing with his thinking and pondering, that becomes the inclination of his awareness.",
    textJa: "修行者が思考と熟考で追い求めるものは、その意識の傾向となる。",
    source: "Majjhima Nikaya",
    chapter: "Two Kinds of Thought",
    verseNumber: "MN 19",
    isPremium: true,
  },
  {
    id: 34,
    text: "Better it is to live one day seeing the rise and fall of things than to live a hundred years without ever seeing the rise and fall of things.",
    textJa: "物事の生滅を見て一日生きることは、物事の生滅を見ずに百年生きることより優れている。",
    source: "Dhammapada",
    chapter: "Chapter 8 (Sahassa Vagga)",
    verseNumber: "Verse 113",
    isPremium: true,
  },
  {
    id: 35,
    text: "Irrigators channel water; fletchers straighten arrows; carpenters shape wood; the wise discipline themselves.",
    textJa: "水路を引く者は水を導き、矢師は矢を真っ直ぐにし、大工は木を削る。賢者は自らを律する。",
    source: "Dhammapada",
    chapter: "Chapter 6 (Pandita Vagga)",
    verseNumber: "Verse 80",
    isPremium: true,
  },
  {
    id: 36,
    text: "If you find a wise critic to point out your faults, follow him as you would a guide to hidden treasure.",
    textJa: "あなたの過ちを指摘してくれる賢い批評家がいれば、隠された宝への案内人として従え。",
    source: "Dhammapada",
    chapter: "Chapter 6 (Pandita Vagga)",
    verseNumber: "Verse 76",
    isPremium: true,
  },
  {
    id: 37,
    text: "The greatest prayer is patience.",
    textJa: "最も偉大な祈りは、忍耐である。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 38,
    text: "Whatever has the nature of arising has the nature of ceasing.",
    textJa: "生じる性質を持つものはすべて、滅する性質を持つ。",
    source: "Majjhima Nikaya",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 39,
    text: "An idea that is developed and put into action is more important than an idea that exists only as an idea.",
    textJa: "発展させ行動に移したアイデアは、アイデアとしてのみ存在するものより重要だ。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 40,
    text: "Just as a snake sheds its skin, we must shed our past over and over again.",
    textJa: "蛇が脱皮するように、私たちも過去を何度も何度も脱ぎ捨てなければならない。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 41,
    text: "Three things cannot be long hidden: the sun, the moon, and the truth.",
    textJa: "三つのものは長く隠せない。太陽と、月と、真実だ。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 42,
    text: "To live a pure unselfish life, one must count nothing as one's own in the midst of abundance.",
    textJa: "清く利己心のない生を生きるには、豊かさの中にあっても何も自分のものと思ってはならない。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 43,
    text: "It is a man's own mind, not his enemy or foe, that lures him to evil ways.",
    textJa: "人を悪の道へ誘うのは、敵でも仇でもなく、その人自身の心だ。",
    source: "Dhammapada",
    chapter: "Chapter 1 (Yamaka Vagga)",
    verseNumber: "Verse 3",
    isPremium: true,
  },
  {
    id: 44,
    text: "In separateness lies the world's great misery; in compassion lies the world's true strength.",
    textJa: "分離の中に世界の大きな苦しみがある。慈悲の中に世界の真の力がある。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 45,
    text: "Radiate boundless love towards the entire world — above, below, and across — unhindered, without ill will, without enmity.",
    textJa: "上に、下に、四方八方に、全世界に向けて、無限の慈愛を放て。障害なく、悪意なく、敵意なく。",
    source: "Metta Sutta",
    chapter: "Karaniya Metta Sutta",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 46,
    text: "The secret of health for both mind and body is not to mourn for the past, worry about the future, or anticipate troubles, but to live in the present moment wisely and earnestly.",
    textJa: "心身の健康の秘訣は、過去を嘆かず、未来を憂えず、困難を予期せず、今この瞬間を賢く誠実に生きることだ。",
    source: "Buddha",
    chapter: "Traditional Teaching",
    verseNumber: "",
    isPremium: true,
  },
  {
    id: 47,
    text: "We are shaped by our thoughts; we become what we think. When the mind is pure, joy follows like a shadow that never departs.",
    textJa: "私たちは思いによって形作られる。思うことがそのままになる。心が清らかなとき、喜びは離れない影のように付き従う。",
    source: "Dhammapada",
    chapter: "Chapter 1 (Yamaka Vagga)",
    verseNumber: "Verse 1-2",
    isPremium: true,
  },
  {
    id: 48,
    text: "However many holy words you read, however many you speak, what good will they do you if you do not act on them?",
    textJa: "どれだけ多くの聖なる言葉を読み、語っても、それを実践しなければ何の意味があるのか？",
    source: "Dhammapada",
    chapter: "Chapter 1 (Yamaka Vagga)",
    verseNumber: "Verse 20",
    isPremium: true,
  },
  {
    id: 49,
    text: "Long is the night to him who is awake; long is a mile to him who is tired; long is life to the foolish who do not know the true law.",
    textJa: "目覚めている者には夜が長く、疲れた者には一里が長く、真の法を知らぬ愚者には生が長い。",
    source: "Dhammapada",
    chapter: "Chapter 5 (Bala Vagga)",
    verseNumber: "Verse 60",
    isPremium: true,
  },
  {
    id: 50,
    text: "One who acts on truth is happy in this world and beyond.",
    textJa: "真実に従って行動する者は、この世でも、来世でも幸福である。",
    source: "Dhammapada",
    chapter: "Chapter 13 (Loka Vagga)",
    verseNumber: "Verse 168",
    isPremium: true,
  },
];

export const stayPresentMessages = [
  "Are you present right now?",
  "Notice this moment.",
  "Where is your mind?",
  "Breathe. You are here.",
  "This too shall pass.",
  "Return to your breath.",
  "Feel your feet on the ground.",
  "What do you hear right now?",
  "Let thoughts pass like clouds.",
  "This moment is enough.",
];

export const stayPresentMessagesJa = [
  "今、ここにいますか？",
  "この瞬間に気づいてください。",
  "心はどこにありますか？",
  "息をして。あなたは今ここにいる。",
  "これもまた過ぎ去る。",
  "呼吸に戻りましょう。",
  "足が地面に触れているのを感じて。",
  "今、何が聞こえますか？",
  "思いを雲のように流して。",
  "この瞬間で十分。",
];

export const getFreeVerses = (): Verse[] => verses.filter(v => !v.isPremium);
export const getAllVerses = (): Verse[] => verses;

export const getLocalizedVerse = (verse: Verse, locale: string): string => {
  const lang = locale.toLowerCase().replace('_', '-').split('-')[0];
  if (lang === 'ja') return verse.textJa;
  return verse.text;
};

const SOURCE_JA: Record<string, string> = {
  'Dhammapada': '法句経',
  'Buddha': 'ブッダ',
  'Khaggavisana Sutta': '犀角経',
  'Majjhima Nikaya': '中部経典',
  'Metta Sutta': '慈悲経',
};

export const getLocalizedSource = (source: string, locale: string): string => {
  const lang = locale.toLowerCase().replace('_', '-').split('-')[0];
  if (lang !== 'ja') return source;
  return SOURCE_JA[source] ?? source;
};

export const getLocalizedChapter = (chapter: string, verseNumber: string, locale: string): string => {
  const lang = locale.toLowerCase().replace('_', '-').split('-')[0];
  if (lang !== 'ja') return verseNumber ? `${chapter}, ${verseNumber}` : chapter;
  // "Chapter 3 (Citta Vagga)" → "第3章（チッタ品）" style: keep chapter number, translate label
  const chapterMatch = chapter.match(/Chapter (\d+) \((.+)\)/);
  const verseMatch = verseNumber.match(/Verse (.+)/);
  const chapterNum = chapterMatch ? `第${chapterMatch[1]}章` : chapter;
  const versePart = verseMatch ? `第${verseMatch[1]}偈` : verseNumber;
  return versePart ? `${chapterNum}、${versePart}` : chapterNum;
};

export const getDailyVerse = (isPremium: boolean = false, date: Date = new Date()): Verse => {
  const availableVerses = isPremium ? verses : getFreeVerses();
  const dayOfYear = Math.floor(
    (date.getTime() - new Date(date.getFullYear(), 0, 0).getTime()) / (1000 * 60 * 60 * 24)
  );
  return availableVerses[dayOfYear % availableVerses.length];
};

export const getRandomStayPresentMessage = (): string => {
  return stayPresentMessages[Math.floor(Math.random() * stayPresentMessages.length)];
};
