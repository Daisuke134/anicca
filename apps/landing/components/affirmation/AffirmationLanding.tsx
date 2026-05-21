/* eslint-disable react/no-unescaped-entities */
import Image from 'next/image';
import Link from 'next/link';
import PhoneFrame from './PhoneFrame';

type Locale = 'en' | 'ja';

const APP_STORE_URL =
  'https://apps.apple.com/us/app/daily-affirmations-anicca/id6755129214';

type Copy = {
  navBack: string;
  navLang: string;
  eyebrow: string;
  heroLine1: React.ReactNode;
  heroLine2: React.ReactNode;
  heroSub: string;
  ctaPrimary: string;
  rating: string;
  ratingMeta: string;
  badges: string[];
  proofRow: string;

  storyEyebrow: string;
  storyHeading: React.ReactNode;
  storyBody: string;

  notesEyebrow: string;
  notesHeading: React.ReactNode;
  notesBody: string;
  notes: { time: string; text: string }[];

  showcaseEyebrow: string;
  showcaseHeading: React.ReactNode;
  showcase: { title: string; body: string; img: string }[];

  voicesEyebrow: string;
  voicesHeading: React.ReactNode;
  voicesBody: string;
  voices: { line: string; tag: string }[];

  vsEyebrow: string;
  vsHeading: React.ReactNode;
  vsThemHeader: string;
  vsRows: { label: string; them: string; us: string }[];

  pricingEyebrow: string;
  pricingHeading: React.ReactNode;
  free: { name: string; price: string; bullets: string[] };
  pro: { name: string; price: string; sub: string; bullets: string[]; cta: string };

  faqEyebrow: string;
  faqHeading: React.ReactNode;
  faq: { q: string; a: string }[];

  closeEyebrow: string;
  closeLine: React.ReactNode;
  closeBody: string;
  closeCta: string;
  closeMeta: string;
  closeBack: string;
};

const COPY: Record<Locale, Copy> = {
  en: {
    navBack: '← anicca.ai',
    navLang: 'JA',
    eyebrow: 'Anicca · iOS · Health & Wellness',
    heroLine1: (
      <>
        you don't<br />have to be<br />okay
      </>
    ),
    heroLine2: <em className="not-italic text-gold/90">right now.</em>,
    heroSub:
      "Anicca is a quiet companion on your phone. When the spiral starts — at 11:47pm, in line at the pharmacy, the second you open Instagram — a single line of kindness arrives. You don't have to open an app. It finds you.",
    ctaPrimary: 'Download on the App Store',
    rating: '4.8',
    ratingMeta: 'App Store · Health & Fitness',
    badges: [
      'iOS 15+',
      'No streaks',
      'No tracker',
      'No guilt',
      'Private by design',
    ],
    proofRow:
      'Featured in soft-life TikTok · As gentle as a friend who has done the work',

    storyEyebrow: 'I. The premise',
    storyHeading: (
      <>
        Every other affirmation app<br />
        <em className="text-mist">waits for you to open it.</em>
      </>
    ),
    storyBody:
      "The spiral does not wait. It comes at midnight, at red lights, in the bathroom mirror. By the time you remember to open the journaling app, the moment has passed. Anicca was built backwards: the affirmation arrives at the spiral. Not a habit, not a streak — a knock on the door.",

    notesEyebrow: 'II. A day with Anicca',
    notesHeading: (
      <>
        One line of kindness,<br />
        <em className="text-mist">at the right moment.</em>
      </>
    ),
    notesBody:
      "Anicca learns the shape of your day. She doesn't bother you when you're fine — she shows up when the wave comes.",
    notes: [
      {
        time: '07:42',
        text: 'You woke up tired. Today does not have to be efficient. It has to be lived.',
      },
      {
        time: '14:18',
        text: 'You re-read the message you sent. It was kind. Stop checking it.',
      },
      {
        time: '23:51',
        text: 'The story your mind is telling you at this hour is not the truth. Sleep is allowed to be the answer.',
      },
    ],

    showcaseEyebrow: 'III. Three screens, three feelings',
    showcaseHeading: (
      <>
        Built like a <em className="text-mist">monastery</em>,<br />
        moves like an <em className="text-mist">app</em>.
      </>
    ),
    showcase: [
      {
        title: 'Tell it what hurts',
        body: 'Onboard in 90 seconds. Pick what you carry — anxiety, self-doubt, grief, late nights. Anicca calibrates to the exact shape of your weather.',
        img: '/screenshots/en/onboarding.png',
      },
      {
        title: 'It arrives at the spiral',
        body: 'Not a digest. Not a daily push at 8am. Anicca learns when your mind unravels and meets you there — once, briefly, gently.',
        img: '/screenshots/en/notification.png',
      },
      {
        title: 'A small lighter feeling',
        body: 'Tap to read. Thumb up if it lands. Cards become more you. Nothing to track. Nothing to lose.',
        img: '/screenshots/en/nudge-card.png',
      },
    ],

    voicesEyebrow: 'IV. The voice',
    voicesHeading: (
      <>
        Lines you might<br />
        <em className="text-mist">actually keep.</em>
      </>
    ),
    voicesBody:
      'Real Anicca cards. Tap a thumb up if it lands; the model writes more like that one.',
    voices: [
      {
        line: 'You are allowed to disappoint people who never asked how you were.',
        tag: 'boundaries · 22:14',
      },
      {
        line: 'The version of you from a year ago would be proud you are still here.',
        tag: 'self-love · 09:02',
      },
      {
        line: 'A storm is not a sign that you built the house wrong.',
        tag: 'grief · 03:38',
      },
      {
        line: 'You can want the thing and not be ready for the thing on the same day.',
        tag: 'manifestation · 07:55',
      },
      {
        line: 'Rest is not the reward for finishing. It is the requirement for continuing.',
        tag: 'burnout · 18:40',
      },
      {
        line: 'Anicca means impermanence. The feeling you are in right now is also passing.',
        tag: 'anxiety · 23:47',
      },
    ],

    vsEyebrow: 'V. Why it works',
    vsHeading: (
      <>
        Not another <em className="text-mist">habit tracker</em>.
      </>
    ),
    vsThemHeader: 'Other apps',
    vsRows: [
      { label: 'Trigger', them: 'You remember to open it', us: 'It opens itself, gently' },
      { label: 'Cadence', them: 'Daily push at 8:00am', us: 'When the spiral actually arrives' },
      { label: 'Length', them: 'A 10-minute session', us: 'A single line, 4 seconds' },
      { label: 'Failure', them: 'Streak broken, guilt installed', us: 'Nothing to break' },
      { label: 'Voice', them: 'Crush your goals!', us: "You don't have to be okay right now" },
    ],

    pricingEyebrow: 'VI. Pricing',
    pricingHeading: (
      <>
        Free to download.<br />
        <em className="text-mist">Pro if it helps.</em>
      </>
    ),
    free: {
      name: 'Free',
      price: '$0',
      bullets: [
        'Onboarding & calibration',
        '3 affirmation cards / week',
        'Daily reading feed',
      ],
    },
    pro: {
      name: 'Anicca Pro',
      price: '$9.99 / mo',
      sub: 'or $49.99 / year (save 58%)',
      bullets: [
        'Unlimited cards (1–3 per day, learned)',
        'Voice sessions — talk it out',
        'Lock-screen widget',
        '13 themes incl. shadow work, manifestation, grief',
        'Cancel anytime, no questions',
      ],
      cta: 'Start with the App Store',
    },

    faqEyebrow: 'VII. Questions',
    faqHeading: <>Things people ask.</>,
    faq: [
      {
        q: 'Is this religious?',
        a: 'Anicca borrows one Pāli word — the Buddhist word for impermanence. The app is for anyone who wakes up tired. No belief required.',
      },
      {
        q: 'Will I get notified all day?',
        a: '1–3 notifications per day, max. You can pause everything from the lock-screen. Quiet hours are respected automatically.',
      },
      {
        q: 'Is my data shared?',
        a: 'No. Onboarding stays on-device where possible. The model never sees your messages, photos, or contacts. Cancel and your records are deleted within 30 days.',
      },
      {
        q: 'What if I miss a day?',
        a: 'Nothing happens. There are no streaks, no scores, no shame. Anicca will be there tomorrow.',
      },
      {
        q: 'Can I use it offline?',
        a: 'Yes. Your reading feed is cached on the device — open it without signal at the worst moment of the day.',
      },
      {
        q: 'Why is it AI-personalised?',
        a: 'Because grief, burnout, and self-doubt sound different in different people. Thumb up the lines that land; the model writes more like those.',
      },
    ],

    closeEyebrow: 'VIII. Take it with you',
    closeLine: (
      <>
        "Sabbe sankhārā aniccā."<br />
        <em className="text-mist">All conditioned things shall pass.</em>
      </>
    ),
    closeBody:
      'Including the feeling you are sitting in right now. Anicca is the small voice that reminds you of that — at the exact hour you forget.',
    closeCta: 'Download on the App Store',
    closeMeta: 'iOS 15+ · Free · Anicca Pro from $9.99 / mo',
    closeBack: '← back to anicca.ai',
  },

  ja: {
    navBack: '← anicca.ai',
    navLang: 'EN',
    eyebrow: 'アニッチャ · iOS · Health & Wellness',
    heroLine1: (
      <>
        今夜は<br />無理しなくて<br />いい
      </>
    ),
    heroLine2: <em className="not-italic text-gold/90">— 大丈夫。</em>,
    heroSub:
      'アニッチャ は、あなたのスマホに静かに住む同伴者。心が崩れ始めた瞬間 — 23:47、レジ待ちの列、Instagram を開いた瞬間 — 一言だけ、やさしさが届く。アプリを開く必要はない。向こうから来る。',
    ctaPrimary: 'App Store で入手',
    rating: '4.8',
    ratingMeta: 'App Store · ヘルスケア / フィットネス',
    badges: ['iOS 15+', 'ストリークなし', '記録なし', '罪悪感なし', 'プライバシー優先'],
    proofRow: 'soft-life TikTok で話題 · 大人の友達みたいに、やさしい',

    storyEyebrow: 'I. 前提',
    storyHeading: (
      <>
        他の アファメーション アプリは、<br />
        <em className="text-mist">あなたが開くのを待つ。</em>
      </>
    ),
    storyBody:
      'けれど、心の渦は待たない。真夜中、信号待ち、洗面台の鏡。ジャーナルアプリを開こうと思いついた頃には、もう波は過ぎている。アニッチャ は逆向きに作られた — 渦のほうに、アファメーション が届く。習慣でもストリークでもなく、ノックのように。',

    notesEyebrow: 'II. アニッチャ と過ごす一日',
    notesHeading: (
      <>
        一行のやさしさ、<br />
        <em className="text-mist">ちょうどいい瞬間に。</em>
      </>
    ),
    notesBody:
      'アニッチャ はあなたの一日の形を学ぶ。元気なときは黙っている。波が来たときに、そっと現れる。',
    notes: [
      { time: '07:42', text: '疲れて目が覚めた。今日は効率的でなくていい。生きていればいい。' },
      { time: '14:18', text: 'さっき送ったメッセージを読み返した。やさしかった。確認するのをやめていい。' },
      { time: '23:51', text: 'この時間に頭が話している物語は、本当のことではない。眠ることが答えでも構わない。' },
    ],

    showcaseEyebrow: 'III. 3 つの画面、3 つの感覚',
    showcaseHeading: (
      <>
        作りは <em className="text-mist">寺院</em>、<br />
        動きは <em className="text-mist">アプリ</em>。
      </>
    ),
    showcase: [
      {
        title: '何が痛むかを教えて',
        body: '90 秒で初期設定。今あなたが抱えているもの — 不安、自己否定、悲しみ、夜更かし — を選ぶ。アニッチャ はあなたの天気の形に合わせる。',
        img: '/screenshots/ja/onboarding.png',
      },
      {
        title: '渦のほうに届く',
        body: 'まとめ通知ではなく、朝 8 時の定刻通知でもない。心がほどける時間を学習し、その瞬間に、一度だけ、静かに現れる。',
        img: '/screenshots/ja/notification.png',
      },
      {
        title: '少しだけ、軽くなる',
        body: 'タップして読む。沁みたら親指を上げる。カードはあなたに似ていく。記録するものは何もない。失うものも何もない。',
        img: '/screenshots/ja/nudge-card.png',
      },
    ],

    voicesEyebrow: 'IV. 言葉',
    voicesHeading: (
      <>
        実際に届くかもしれない<br />
        <em className="text-mist">一行たち。</em>
      </>
    ),
    voicesBody: '実際に アニッチャ から届くカード。沁みたら親指を上げると、モデルはそれに似た一行をもっと書きます。',
    voices: [
      { line: 'あなたの体調を一度も訊かなかった人を、がっかりさせていい。', tag: '境界線 · 22:14' },
      { line: '一年前のあなたは、今もここにいるあなたを誇りに思っている。', tag: 'セルフラブ · 09:02' },
      { line: '嵐は、家の建て方を間違えたという証拠ではない。', tag: '悲しみ · 03:38' },
      { line: 'それを欲しがることと、まだその準備ができていないことは、同じ日に成立していい。', tag: 'マニフェステーション · 07:55' },
      { line: '休息は、終わらせたご褒美ではない。続けるための条件。', tag: 'バーンアウト · 18:40' },
      { line: 'アニッチャ は無常という意味。今あなたが感じているこの感覚も、過ぎていく。', tag: '不安 · 23:47' },
    ],

    vsEyebrow: 'V. 効く理由',
    vsHeading: (
      <>
        ただの <em className="text-mist">習慣トラッカー</em> ではない。
      </>
    ),
    vsThemHeader: '他のアプリ',
    vsRows: [
      { label: 'きっかけ', them: 'あなたが思い出してアプリを開く', us: '向こうから、そっと開く' },
      { label: '頻度', them: '毎朝 8:00 の定刻通知', us: '実際に渦が来た瞬間' },
      { label: '長さ', them: '10 分のセッション', us: '一行、4 秒' },
      { label: '失敗', them: 'ストリーク途切れる、罪悪感が住みつく', us: '途切れるものがない' },
      { label: '声色', them: '目標を粉砕しろ!', us: '今夜は無理しなくていい' },
    ],

    pricingEyebrow: 'VI. 料金',
    pricingHeading: (
      <>
        ダウンロードは無料。<br />
        <em className="text-mist">役に立ったら Pro で。</em>
      </>
    ),
    free: {
      name: 'Free',
      price: '¥0',
      bullets: ['初期設定 & キャリブレーション', '週 3 枚のカード', '読み返しフィード'],
    },
    pro: {
      name: 'Anicca Pro',
      price: '¥1,500 / 月',
      sub: 'または ¥7,800 / 年 (58% off)',
      bullets: [
        '無制限のカード (1日 1〜3 枚、学習)',
        'ボイスセッション — 声に出して話す',
        'ロック画面ウィジェット',
        '13 のテーマ (シャドウワーク、マニフェステーション、悲しみ等)',
        'いつでも解約、説明不要',
      ],
      cta: 'App Store で始める',
    },

    faqEyebrow: 'VII. よくある質問',
    faqHeading: <>聞かれること。</>,
    faq: [
      {
        q: '宗教ですか?',
        a: 'パーリ語をひとつだけ借りています — 仏教の「無常」という言葉。アプリ自体は、疲れて目覚めるすべての人のためのものです。信仰は不要。',
      },
      {
        q: '一日中通知が来ますか?',
        a: '1 日に 1〜3 回まで。ロック画面から全部止められます。おやすみ時間は自動で尊重します。',
      },
      {
        q: 'データは共有されますか?',
        a: 'いいえ。可能な限り端末内で完結します。モデルがあなたのメッセージや写真、連絡先を見ることはありません。解約後 30 日以内に記録は削除されます。',
      },
      {
        q: '一日休んだら?',
        a: '何も起きません。ストリークもスコアも罰もありません。アニッチャ は、明日もそこにいます。',
      },
      {
        q: 'オフラインでも使えますか?',
        a: 'はい。読み返しフィードは端末にキャッシュされます。電波がない、最悪のタイミングでも開けます。',
      },
      {
        q: 'なぜ AI でパーソナライズなんですか?',
        a: '悲しみ、燃え尽き、自己否定は、人によって響く言葉が違うから。沁みた一行に親指を上げると、モデルはそれに似た一行をもっと書きます。',
      },
    ],

    closeEyebrow: 'VIII. 持ち帰る',
    closeLine: (
      <>
        「諸行無常。」<br />
        <em className="text-mist">構築されたすべては、移ろう。</em>
      </>
    ),
    closeBody:
      '今あなたが座っているその感覚も含めて。アニッチャ は、それをあなたが忘れる正確な時刻に、静かに思い出させる小さな声。',
    closeCta: 'App Store で入手',
    closeMeta: 'iOS 15+ · 無料 · Anicca Pro は ¥1,500 / 月から',
    closeBack: '← anicca.ai に戻る',
  },
};

const SOFT_HEADING = '"opsz" 144, "SOFT" 100';
const SOFT_QUOTE = '"opsz" 96, "SOFT" 80';
const SOFT_BIG_NUM = '"opsz" 144';

export default function AffirmationLanding({ locale }: { locale: Locale }) {
  const t = COPY[locale];
  const otherLocale = locale === 'en' ? 'ja' : 'en';
  const otherPath = otherLocale === 'en' ? '/affirmation-app' : '/affirmation-app/ja';
  const badgeSrc = locale === 'en' ? '/app-store-badge-en.svg' : '/app-store-badge-ja.svg';
  const fontClass = locale === 'ja' ? 'font-serif-jp' : 'font-soft';

  return (
    <div lang={locale} className={fontClass}>
      <div className="relative min-h-dvh bg-[#fdf7ee] text-ink">
        {/* Mini-nav */}
        <header className="sticky top-0 z-40 border-b border-ink/5 bg-[#fdf7ee]/80 backdrop-blur">
          <div className="mx-auto flex h-12 max-w-6xl items-center justify-between px-5">
            <Link
              href="/"
              className="font-mono-ui text-[11px] uppercase tracking-[0.22em] text-mist hover:text-ink"
            >
              {t.navBack}
            </Link>
            <p className="font-soft text-[14px] italic text-ink">anicca</p>
            <Link
              href={otherPath}
              className="font-mono-ui text-[11px] uppercase tracking-[0.22em] text-mist hover:text-ink"
            >
              {t.navLang}
            </Link>
          </div>
        </header>

        {/* HERO */}
        <section className="relative overflow-hidden">
          <div
            aria-hidden
            className="absolute inset-x-0 top-0 -z-0 h-[120%]"
            style={{
              background:
                'radial-gradient(ellipse at 75% 0%, rgba(244, 196, 138, 0.55) 0%, rgba(247, 222, 196, 0.30) 25%, transparent 55%), radial-gradient(ellipse at 10% 30%, rgba(204, 178, 220, 0.18) 0%, transparent 45%)',
            }}
          />

          <div className="relative mx-auto grid min-h-[88dvh] max-w-6xl grid-cols-12 items-center gap-x-6 gap-y-12 px-5 py-16 md:py-24">
            <div className="col-span-12 md:col-span-7">
              <p className="font-mono-ui text-[10px] uppercase tracking-[0.3em] text-mist">
                {t.eyebrow}
              </p>

              <h1
                className="mt-7 font-soft text-[64px] leading-[0.92] tracking-[-0.04em] text-ink sm:text-[88px] md:text-[112px]"
                style={{ fontVariationSettings: SOFT_HEADING }}
              >
                {t.heroLine1}{' '}
                <span className="block">{t.heroLine2}</span>
              </h1>

              <p className="mt-9 max-w-xl text-[18px] leading-[1.6] text-ink-soft sm:text-[20px]">
                {t.heroSub}
              </p>

              <div className="mt-10 flex flex-wrap items-center gap-x-5 gap-y-4">
                <a href={APP_STORE_URL} target="_blank" rel="noopener noreferrer">
                  <Image
                    src={badgeSrc}
                    alt={t.ctaPrimary}
                    width={168}
                    height={56}
                    className="h-14 w-auto"
                  />
                </a>
                <div className="flex items-center gap-2">
                  <span
                    className="font-soft text-[22px] italic text-ink"
                    style={{ fontVariationSettings: '"opsz" 96' }}
                  >
                    ★ {t.rating}
                  </span>
                  <span className="font-mono-ui text-[10px] uppercase tracking-[0.2em] text-mist">
                    {t.ratingMeta}
                  </span>
                </div>
              </div>

              <ul className="mt-7 flex flex-wrap gap-x-3 gap-y-2 font-mono-ui text-[10px] uppercase tracking-[0.2em] text-mist">
                {t.badges.map((b) => (
                  <li key={b} className="rounded-full border border-ink/15 px-3 py-1.5">
                    {b}
                  </li>
                ))}
              </ul>
            </div>

            <div className="col-span-12 flex justify-center md:col-span-5 md:justify-end">
              <div className="relative">
                <PhoneFrame
                  src={t.showcase[1].img}
                  alt="Anicca app — incoming notification"
                  variant="lockscreen"
                  width={280}
                  priority
                  tilt="right"
                />
                <div
                  className="pointer-events-none absolute -left-12 top-[18%] hidden w-[260px] rounded-2xl bg-white/90 p-3 shadow-2xl backdrop-blur md:block"
                  style={{ boxShadow: '0 18px 40px -12px rgba(20,20,30,0.35)' }}
                >
                  <div className="flex items-start gap-2.5">
                    <Image
                      src="/anicca-app-icon.png"
                      alt="Anicca app icon"
                      width={28}
                      height={28}
                      className="mt-0.5 h-7 w-7 shrink-0 rounded-md"
                    />
                    <div className="min-w-0">
                      <p className="font-mono-ui text-[10px] uppercase tracking-[0.18em] text-mist">
                        anicca · now
                      </p>
                      <p className="mt-0.5 truncate font-soft text-[13px] italic text-ink">
                        {t.notes[2].text.slice(0, 64)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mx-auto max-w-6xl border-t border-ink/10 px-5 py-5">
            <p className="text-center font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
              {t.proofRow}
            </p>
          </div>
        </section>

        {/* STORY */}
        <section className="relative px-5 py-28 sm:py-36">
          <div className="mx-auto grid max-w-6xl grid-cols-12 gap-x-6 gap-y-10">
            <div className="col-span-12 md:col-span-4">
              <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
                {t.storyEyebrow}
              </p>
            </div>
            <div className="col-span-12 md:col-span-8">
              <h2
                className="font-soft text-[42px] leading-[1.05] tracking-[-0.02em] text-ink sm:text-[56px]"
                style={{ fontVariationSettings: SOFT_HEADING }}
              >
                {t.storyHeading}
              </h2>
              <p className="mt-8 max-w-2xl text-[19px] leading-[1.65] text-ink-soft sm:text-[21px]">
                {t.storyBody}
              </p>
            </div>
          </div>
        </section>

        {/* DAY-WITH */}
        <section className="relative bg-[#f6ecdc] px-5 py-28 sm:py-36">
          <div
            aria-hidden
            className="absolute inset-0 -z-0 opacity-50"
            style={{
              background:
                'radial-gradient(ellipse at 20% 20%, rgba(244, 196, 138, 0.25) 0%, transparent 50%)',
            }}
          />
          <div className="relative mx-auto grid max-w-6xl grid-cols-12 gap-x-6 gap-y-10">
            <div className="col-span-12 md:col-span-4">
              <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
                {t.notesEyebrow}
              </p>
              <h2
                className="mt-3 font-soft text-[40px] leading-[1.05] tracking-[-0.02em] text-ink sm:text-[52px]"
                style={{ fontVariationSettings: SOFT_HEADING }}
              >
                {t.notesHeading}
              </h2>
              <p className="mt-6 max-w-sm text-[16px] leading-[1.65] text-ink-soft">
                {t.notesBody}
              </p>
            </div>
            <div className="col-span-12 md:col-span-8">
              <ul className="space-y-4">
                {t.notes.map((n, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-5 rounded-2xl border border-ink/8 bg-white/70 p-5 backdrop-blur sm:p-6"
                    style={{ boxShadow: '0 8px 24px -16px rgba(20,20,30,0.18)' }}
                  >
                    <div className="shrink-0">
                      <p className="font-mono-ui text-[11px] uppercase tracking-[0.2em] text-mist">
                        {n.time}
                      </p>
                      <p className="font-mono-ui text-[10px] uppercase tracking-[0.18em] text-gold">
                        anicca
                      </p>
                    </div>
                    <p
                      className="font-soft text-[18px] leading-[1.55] text-ink sm:text-[20px]"
                      style={{ fontVariationSettings: SOFT_QUOTE }}
                    >
                      "{n.text}"
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* SHOWCASE */}
        <section className="relative px-5 py-28 sm:py-36">
          <div className="mx-auto max-w-6xl">
            <div className="grid grid-cols-12 gap-x-6 gap-y-10">
              <div className="col-span-12 md:col-span-4">
                <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
                  {t.showcaseEyebrow}
                </p>
                <h2
                  className="mt-3 font-soft text-[40px] leading-[1.05] tracking-[-0.02em] text-ink sm:text-[52px]"
                  style={{ fontVariationSettings: SOFT_HEADING }}
                >
                  {t.showcaseHeading}
                </h2>
              </div>
              <div className="col-span-12 md:col-span-8" />
            </div>

            <div className="mt-16 grid grid-cols-1 gap-12 sm:grid-cols-3">
              {t.showcase.map((s, i) => (
                <div key={s.title} className="flex flex-col items-center text-center">
                  <PhoneFrame
                    src={s.img}
                    alt={s.title}
                    width={220}
                    tilt={i === 0 ? 'left' : i === 2 ? 'right' : 'none'}
                  />
                  <p className="mt-7 font-mono-ui text-[11px] uppercase tracking-[0.22em] text-mist">
                    {String(i + 1).padStart(2, '0')}
                  </p>
                  <h3
                    className="mt-2 font-soft text-[24px] italic text-ink"
                    style={{ fontVariationSettings: '"opsz" 96' }}
                  >
                    {s.title}
                  </h3>
                  <p className="mt-3 max-w-xs text-[15px] leading-[1.6] text-ink-soft">
                    {s.body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* VOICES */}
        <section className="relative bg-ink px-5 py-28 text-cream sm:py-36">
          <div className="mx-auto max-w-6xl">
            <div className="grid grid-cols-12 gap-x-6 gap-y-10">
              <div className="col-span-12 md:col-span-4">
                <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-cream/55">
                  {t.voicesEyebrow}
                </p>
                <h2
                  className="mt-3 font-soft text-[40px] leading-[1.05] tracking-[-0.02em] text-cream sm:text-[52px]"
                  style={{ fontVariationSettings: SOFT_HEADING }}
                >
                  {t.voicesHeading}
                </h2>
                <p className="mt-6 max-w-sm text-[15px] leading-[1.65] text-cream/70">
                  {t.voicesBody}
                </p>
              </div>
              <div className="col-span-12 md:col-span-8">
                <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {t.voices.map((v, i) => (
                    <li
                      key={i}
                      className="rounded-2xl border border-cream/10 bg-cream/[0.04] p-6 transition-colors hover:bg-cream/[0.07]"
                    >
                      <p
                        className="font-soft text-[19px] leading-[1.45] italic text-cream sm:text-[21px]"
                        style={{ fontVariationSettings: '"opsz" 96, "SOFT" 100' }}
                      >
                        "{v.line}"
                      </p>
                      <p className="mt-4 font-mono-ui text-[10px] uppercase tracking-[0.2em] text-cream/45">
                        {v.tag}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* VS */}
        <section className="relative px-5 py-28 sm:py-36">
          <div className="mx-auto max-w-6xl">
            <div className="grid grid-cols-12 gap-x-6 gap-y-10">
              <div className="col-span-12 md:col-span-4">
                <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
                  {t.vsEyebrow}
                </p>
                <h2
                  className="mt-3 font-soft text-[40px] leading-[1.05] tracking-[-0.02em] text-ink sm:text-[52px]"
                  style={{ fontVariationSettings: SOFT_HEADING }}
                >
                  {t.vsHeading}
                </h2>
              </div>
              <div className="col-span-12 md:col-span-8">
                <table className="w-full border-collapse text-left">
                  <thead>
                    <tr className="border-b border-ink/15 font-mono-ui text-[10px] uppercase tracking-[0.2em] text-mist">
                      <th className="py-3 pr-3 font-normal"> </th>
                      <th className="py-3 pr-3 font-normal">{t.vsThemHeader}</th>
                      <th className="py-3 font-normal">{locale === 'ja' ? 'アニッチャ' : 'Anicca'}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {t.vsRows.map((r, i) => (
                      <tr key={i} className="border-b border-ink/10">
                        <td className="py-5 pr-3 font-mono-ui text-[11px] uppercase tracking-[0.18em] text-mist">
                          {r.label}
                        </td>
                        <td
                          className="py-5 pr-3 font-soft text-[16px] text-mist line-through decoration-ink/15"
                          style={{ fontVariationSettings: '"opsz" 96' }}
                        >
                          {r.them}
                        </td>
                        <td
                          className="py-5 font-soft text-[18px] italic text-ink"
                          style={{ fontVariationSettings: SOFT_QUOTE }}
                        >
                          {r.us}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        {/* PRICING */}
        <section className="relative bg-[#f6ecdc] px-5 py-28 sm:py-36">
          <div className="mx-auto max-w-6xl">
            <div className="grid grid-cols-12 gap-x-6 gap-y-10">
              <div className="col-span-12 md:col-span-4">
                <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
                  {t.pricingEyebrow}
                </p>
                <h2
                  className="mt-3 font-soft text-[40px] leading-[1.05] tracking-[-0.02em] text-ink sm:text-[52px]"
                  style={{ fontVariationSettings: SOFT_HEADING }}
                >
                  {t.pricingHeading}
                </h2>
              </div>
              <div className="col-span-12 grid gap-5 md:col-span-8 md:grid-cols-2">
                <div className="rounded-3xl border border-ink/10 bg-white/60 p-7 backdrop-blur">
                  <p className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-mist">
                    {t.free.name}
                  </p>
                  <p
                    className="mt-4 font-soft text-[42px] tracking-tight text-ink"
                    style={{ fontVariationSettings: SOFT_BIG_NUM }}
                  >
                    {t.free.price}
                  </p>
                  <ul className="mt-6 space-y-2.5 text-[14px] text-ink-soft">
                    {t.free.bullets.map((b) => (
                      <li key={b} className="flex items-start gap-2">
                        <span className="mt-2 inline-block h-1 w-1 shrink-0 rounded-full bg-ink/30" />
                        {b}
                      </li>
                    ))}
                  </ul>
                </div>

                <div
                  className="relative rounded-3xl bg-ink p-7 text-cream"
                  style={{ boxShadow: '0 24px 48px -16px rgba(20,20,30,0.4)' }}
                >
                  <p className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-gold">
                    {t.pro.name}
                  </p>
                  <p
                    className="mt-4 font-soft text-[42px] tracking-tight text-cream"
                    style={{ fontVariationSettings: SOFT_BIG_NUM }}
                  >
                    {t.pro.price}
                  </p>
                  <p className="mt-1 font-mono-ui text-[11px] uppercase tracking-[0.18em] text-cream/55">
                    {t.pro.sub}
                  </p>
                  <ul className="mt-6 space-y-2.5 text-[14px] text-cream/85">
                    {t.pro.bullets.map((b) => (
                      <li key={b} className="flex items-start gap-2">
                        <span className="mt-2 inline-block h-1 w-1 shrink-0 rounded-full bg-gold" />
                        {b}
                      </li>
                    ))}
                  </ul>
                  <a
                    href={APP_STORE_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-7 inline-flex items-center gap-2 rounded-full bg-gold px-5 py-3 font-mono-ui text-[11px] uppercase tracking-[0.2em] text-ink transition-opacity hover:opacity-90"
                  >
                    {t.pro.cta} →
                  </a>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="relative px-5 py-28 sm:py-36">
          <div className="mx-auto max-w-6xl">
            <div className="grid grid-cols-12 gap-x-6 gap-y-10">
              <div className="col-span-12 md:col-span-4">
                <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
                  {t.faqEyebrow}
                </p>
                <h2
                  className="mt-3 font-soft text-[40px] leading-[1.05] tracking-[-0.02em] text-ink sm:text-[52px]"
                  style={{ fontVariationSettings: SOFT_HEADING }}
                >
                  {t.faqHeading}
                </h2>
              </div>
              <div className="col-span-12 md:col-span-8">
                <ul className="divide-y divide-ink/10 border-y border-ink/10">
                  {t.faq.map((f, i) => (
                    <li key={i} className="grid grid-cols-12 items-baseline gap-4 py-7">
                      <span className="col-span-1 font-mono-ui text-[11px] uppercase tracking-[0.2em] text-mist">
                        {String(i + 1).padStart(2, '0')}
                      </span>
                      <div className="col-span-11">
                        <p
                          className="font-soft text-[20px] italic text-ink sm:text-[22px]"
                          style={{ fontVariationSettings: SOFT_QUOTE }}
                        >
                          {f.q}
                        </p>
                        <p className="mt-3 max-w-2xl text-[15px] leading-[1.65] text-ink-soft sm:text-[16px]">
                          {f.a}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* CLOSING */}
        <section className="relative overflow-hidden bg-ink px-5 py-32 text-cream sm:py-44">
          <div
            aria-hidden
            className="absolute inset-0 -z-0"
            style={{
              background:
                'radial-gradient(ellipse at 50% 100%, rgba(214, 167, 92, 0.18) 0%, transparent 60%)',
            }}
          />
          <div className="relative mx-auto max-w-3xl text-center">
            <p className="font-mono-ui text-[10px] uppercase tracking-[0.3em] text-cream/55">
              {t.closeEyebrow}
            </p>
            <p
              className="mt-8 font-soft text-[40px] italic leading-[1.15] text-cream sm:text-[60px]"
              style={{ fontVariationSettings: SOFT_HEADING }}
            >
              {t.closeLine}
            </p>
            <p className="mx-auto mt-6 max-w-xl text-[17px] leading-[1.65] text-cream/75 sm:text-[19px]">
              {t.closeBody}
            </p>
            <div className="mt-12 flex flex-wrap items-center justify-center gap-6">
              <a href={APP_STORE_URL} target="_blank" rel="noopener noreferrer">
                <Image
                  src={badgeSrc}
                  alt={t.closeCta}
                  width={180}
                  height={60}
                  className="h-14 w-auto"
                />
              </a>
              <p className="font-mono-ui text-[11px] uppercase tracking-[0.2em] text-cream/55">
                {t.closeMeta}
              </p>
            </div>
            <Link
              href="/"
              className="mt-12 inline-block border-b border-cream/30 font-mono-ui text-[11px] uppercase tracking-[0.2em] text-cream/70 hover:border-gold hover:text-gold"
            >
              {t.closeBack}
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
