// Launch-surface copy, fully localized EN + JA (spec29 + Dais 2026-06-16:
// "EN version all English, JA version all Japanese, completely separate/localized").
// Every visible string for /install, /me, /lm and /life-manager lives here so each
// page/component just reads strings[locale]. Copy is hand-written natural English and
// natural Japanese — NOT machine translation of one from the other. No fake numbers,
// no internal jargon. Keep the two dictionaries the SAME SHAPE.

import type { LaunchLocale } from './launchLocale';

export const launchStrings = {
  en: {
    nav: {
      install: 'Install',
      me: 'Me',
      dashboard: 'Dashboard',
      lifeManager: 'Life Manager',
      langLabel: 'Language',
      en: 'EN',
      ja: '日本語',
    },

    lm: {
      metaTitle: 'Life Manager: Get started',
      metaDesc:
        'Life Manager: connect your Google Calendar, add your phone, and it calls you before you need to leave. $20/mo.',
      eyebrow: 'Life Manager · $20/mo',
      soonTitle: 'Web sign-up is coming soon',
      soonBody:
        'Life Manager launches on Telegram first. Tap below to start on Telegram — name, calendar, phone, done. The web version is coming soon.',
      soonCta: 'Start on Telegram',
      heroTitle: 'Never be late again.',
      heroBody:
        'Sign in, connect your Google Calendar, add your phone. Life Manager then handles travel time, calls you before you leave, asks on Telegram when a location is unclear, and drafts your late-notices. 24/7.',
      stepAria: (i: number, n: number) => `step ${i} of ${n}`,
      login: {
        title: 'Sign in to start',
        body: 'Life Manager keeps you on time by phone. $20/mo.',
        button: 'Continue with Google',
      },
      name: {
        title: 'What should it call you?',
        placeholder: 'Your name',
        button: 'Continue',
        error: 'Please enter your name.',
        saveError: 'Could not save. Try again.',
      },
      connect: {
        title: 'Connect your Calendar',
        body: 'Connect your Google Calendar below. Life Manager reads your schedule, asks you on Telegram when something is unclear, and acts only with your approval.',
        calendar: 'Google Calendar',
        gmail: 'Gmail',
        button: 'Continue',
        stateConnected: 'connected ✓',
        stateConnecting: 'connecting…',
        stateConnect: 'connect →',
        error: 'Connection failed.',
      },
      phone: {
        title: 'Your phone number',
        body: 'Life Manager calls 10 minutes before each event with route guidance.',
        placeholder: '8012345678',
        button: 'Continue',
        error: 'Enter a valid phone number for the selected country.',
        saveError: 'Could not save. Try again.',
      },
      pay: {
        titlePrefix: 'You’re set, ',
        titleFallback: 'friend',
        bodyPre: 'Subscribe to activate 24/7 management. ',
        bodyStrong: '$20/mo.',
        button: 'Subscribe for $20/mo',
        notReady:
          'Checkout is being finalized. We’ll email you the secure $20/mo link shortly.',
        seeDashboard: 'See my dashboard',
      },
      dashboard: {
        eyebrow: 'your life manager',
        connectedSuffix: ', connected',
        you: 'You',
        pills: { calendar: 'Calendar', gmail: 'Gmail', phone: 'Phone' },
        callBtn: { idle: '📞 Call me now (test)', calling: 'Calling you…', done: '✓ Calling — pick up!', error: 'Could not call. Check your number.' },
        skills: [
          { title: 'Travel blocks', desc: 'Travel time goes in before every event.' },
          { title: '10 & 5-min calls', desc: 'It calls twice before each event with route guidance.' },
          {
            title: 'Location asks',
            desc: 'No location? It asks you on Telegram, and your reply updates the event.',
          },
          {
            title: 'Late-notice',
            desc: 'Running late? It drafts a note to the attendees and sends once you approve.',
          },
        ],
        liveBadge: 'live',
        footnote:
          'All four run 24/7 on its own server. Live per-event telemetry lands here next.',
      },
    },

    lifeManager: {
      metaTitle: 'Life Manager',
      metaDesc:
        'Life Manager runs your whole day: wake, sleep, work, commute, meditation. It reads your Google Calendar, blocks out travel time before every event, and phones you 10 and 5 minutes before you need to leave. Each call gets sharper. Nothing to open.',
      heroHeadline: 'Life Manager',
      heroSubtext:
        'Life Manager runs your day so you stop oversleeping and stop showing up late. It reads your calendar, blocks out travel time, and phones you 10 and 5 minutes before you need to leave. Each call gets sharper. If you are going to be late, it drafts the message to whoever is waiting and sends it the moment you say OK. $20/mo. Nothing to open.',
      heroPrimary: 'Get started, $20/mo',
      heroSecondary: 'See how it works',
      asset: {
        wake: '09:30 · call, 10 min before · "time to move"',
        travel1: '09:35 · call, 5 min before · "leave now or you’re late"',
        sync: '09:40 · travel to Team Sync, 20 min',
        travel2: '10:00 · Team Sync',
        lunch: '12:30 · Lunch with Mai · asked where once, remembered it',
        caption: 'Two calls before every event, each one sharper ↑',
      },
      featuresTitle: 'Four skills, one job: you stop being late',
      featuresIntro:
        'Life Manager runs your whole life: wake, sleep, meetings, commute, meditation, work. Every event, every time. It runs four skills on its own server and works your calendar by phone and Telegram. $20/mo.',
      liveLabel: 'live',
      features: [
        {
          id: 'travel',
          label: 'Calendar',
          headline: 'It blocks out your travel time',
          body: 'Every morning Life Manager looks at your day and adds a travel-time block before each event, so your commute is always on the calendar. Move a 10:00 dentist appointment and the travel time moves with it.',
        },
        {
          id: 'call',
          label: 'Phone',
          headline: 'It calls you 10 and 5 minutes before you leave',
          body: 'Life Manager phones your real number twice before you need to leave, and the second call is sharper than the first. At 10 minutes it tells you to move. At 5 it tells you to leave right now. It names the event, the place, and the route, in the language of your phone’s country. Wake, sleep, work, commute, meditation: it calls for every event and skips none.',
        },
        {
          id: 'ask',
          label: 'Telegram',
          headline: 'No location? It asks you',
          body: 'When an event has no place attached, Life Manager messages you on Telegram to ask where it is. Reply with the address and it updates the event for you.',
        },
        {
          id: 'notify',
          label: 'Attendees',
          headline: 'Running late? It warns the people waiting',
          body: 'When your travel time says you will not make it, Life Manager writes a short heads-up to the people in the event and shows it to you first. Reply OK and it sends.',
        },
      ],
      travelTitle: 'How travel blocks work',
      travelCols: { step: 'Step', what: 'What it does', api: 'API' },
      travelRows: [
        { what: 'Reads today’s timed calendar events', api: 'GCal REST v3' },
        { what: 'Finds the events with no travel block yet', api: 'Life Manager' },
        { what: 'Asks Google Maps for the transit route to each one', api: 'Maps Directions' },
        {
          what: 'Drops the [Travel] block so it ends right when the event starts',
          api: 'GCal REST v3',
        },
      ],
      travelNotePre: 'Travel blocks never duplicate. Run the skill again and it finds the existing block by its "[Travel]" prefix and the ',
      travelNoteCode: 'anicca_travel_block',
      travelNotePost: ' property.',
      onTimeTitle: 'Scheduled calls, no polling',
      onTimeBodyPre:
        'A small planner reads your calendar every few minutes and books three one-shot calls per event, at exactly ',
      onTimeBodyCode: 'leave time − 10 / − 5 min',
      onTimeBodyPost: '. Leave time is the [Travel] block start when the event has a location, otherwise the event start. Each call deletes itself after it fires.',
      onTimeResult: 'Two calls per event, the second more urgent. No wasted checks.',
      gettingStartedTitle: 'Getting started',
      gettingStartedSteps: [
        { link: 'Start onboarding', rest: '. Sign in with Google and tell it your name.' },
        { link: '', rest: 'Connect Google Calendar (one click, via Composio).' },
        { link: '', rest: 'Add your phone so it can call you 10 and 5 minutes before every event. Share live location if you want.' },
        {
          link: '',
          restPre: 'Subscribe: ',
          restStrong: '$20/mo',
          restPost: '. Open Google Calendar tomorrow morning and your travel blocks are already there.',
        },
      ],
      cardGetStartedEyebrow: 'get started',
      cardGetStartedTitle: 'Life Manager, $20/mo',
      cardGetStartedDesc: 'Sign in with Google, give your name, connect Calendar, add your phone, share location if you want. Done.',
      cardColonyEyebrow: 'open source',
      cardColonyTitle: 'Life Manager Skill (OSS)',
      cardColonyDesc: 'The same skill, free — run it locally on your own OpenClaw. Clone the repo, add your keys, done. On GitHub.',
      startTitle: 'Start in two taps',
      startIntro: 'Scan to open the Telegram bot, or set it up on the web. Either way: connect Calendar, add your phone, and Life Manager calls you before you need to leave.',
      startPhoneEyebrow: 'on your phone',
      startPhoneTitle: 'Scan to start on Telegram',
      startPhoneDesc: 'Opens @LifeManagerBotbot — tap Start, type your name, connect Calendar, add your phone. No links to type.',
      startPhoneLink: 'Or open the bot directly',
      startWebEyebrow: 'on the web',
      startWebTitle: 'Start on the web',
      startWebDesc: 'Web sign-up is coming soon. Start on Telegram for now — scan the code on the left.',
      startWebCta: 'Coming soon',
    },
  },

  ja: {
    nav: {
      install: 'インストール',
      me: 'マイページ',
      dashboard: 'ダッシュボード',
      lifeManager: 'ライフマネージャー',
      langLabel: '言語',
      en: 'EN',
      ja: '日本語',
    },

    lm: {
      metaTitle: 'ライフマネージャー：はじめる',
      metaDesc:
        'ライフマネージャー。Google カレンダーをつなぎ、電話番号を登録すれば、出発前に電話で遅刻を防ぐ。月 $20。',
      eyebrow: 'ライフマネージャー · 月 $20',
      soonTitle: 'ウェブ登録は近日公開',
      soonBody:
        'Life Manager はまず Telegram で公開。下をタップして Telegram で開始 — 名前・カレンダー・電話で完了。ウェブ版は近日公開。',
      soonCta: 'Telegram で始める',
      heroTitle: 'もう、遅刻しない。',
      heroBody:
        'ログインして、Google カレンダーをつなぎ、電話番号を登録するだけ。移動時間の確保も、出発前の電話も、場所の確認も、遅刻連絡も、ライフマネージャーが引き受ける。24/7。',
      stepAria: (i: number, n: number) => `ステップ ${i} / ${n}`,
      login: {
        title: 'ログインして始める',
        body: 'ライフマネージャーが、電話で遅刻を防ぐ。月 $20。',
        button: 'Google で続ける',
      },
      name: {
        title: 'あなたを何と呼べばいい？',
        placeholder: 'お名前',
        button: '続ける',
        error: 'お名前を入力してください。',
        saveError: '保存できませんでした。もう一度お試しください。',
      },
      connect: {
        title: 'カレンダーをつなぐ',
        body: 'Google カレンダーを接続。ライフマネージャーが予定を読み、不明点は Telegram で聞き、承認を得てから動く。',
        calendar: 'Google カレンダー',
        gmail: 'Gmail',
        button: '続ける',
        stateConnected: '接続済み ✓',
        stateConnecting: '接続中…',
        stateConnect: '接続する →',
        error: '接続に失敗しました。',
      },
      phone: {
        title: '電話番号',
        body: '出発の 10 分前と 5 分前に、ルートを案内する電話をかける。',
        placeholder: '09012345678',
        button: '続ける',
        error: '選択した国の有効な電話番号を入力してください。',
        saveError: '保存できませんでした。もう一度お試しください。',
      },
      pay: {
        titlePrefix: '準備完了です、',
        titleFallback: 'あなた',
        bodyPre: 'サブスクで 24/7 の管理を有効化。',
        bodyStrong: '月 $20。',
        button: 'サブスクに登録（月 $20）',
        notReady:
          '決済を準備中です。安全な月 $20 のリンクをまもなくメールでお送りします。',
        seeDashboard: 'ダッシュボードを見る',
      },
      dashboard: {
        eyebrow: 'あなたのライフマネージャー',
        connectedSuffix: '、接続済み',
        you: 'あなた',
        pills: { calendar: 'カレンダー', gmail: 'Gmail', phone: '電話' },
        callBtn: { idle: '📞 今すぐ電話させる（テスト）', calling: '発信中…', done: '✓ 発信しました。出てください！', error: '発信できませんでした。番号を確認してください。' },
        skills: [
          { title: '移動時間の確保', desc: '各予定の前に、移動時間を自動で入れる。' },
          { title: '10分・5分前の電話', desc: '各予定の前に2回、ルートを案内する電話をかける。' },
          {
            title: '場所の確認',
            desc: '場所が未入力なら、Telegram で確認する。返信すれば予定を更新する。',
          },
          {
            title: '遅刻連絡',
            desc: '遅れそうなとき、出席者への一言を下書きする。あなたが承認すれば送る。',
          },
        ],
        liveBadge: '稼働中',
        footnote:
          '4 つすべてが自分のサーバーで 24/7 動く。予定ごとのライブ・テレメトリは近日ここに表示。',
      },
    },

    lifeManager: {
      metaTitle: 'ライフマネージャー',
      metaDesc:
        'ライフマネージャーが、あなたの一日をまわす。起床から就寝、仕事も通勤も瞑想も。Google カレンダーを読んで、予定の前に移動時間を入れ、出発の 10 分前と 5 分前に電話する。近づくほど声は急かす。開くアプリはない。',
      heroHeadline: 'ライフマネージャー',
      heroSubtext:
        'ライフマネージャーが一日をまわすから、もう寝坊しないし、遅刻もしない。カレンダーを読んで移動時間を入れ、出発の 10 分前と 5 分前に電話する。近づくほど声は急かす。間に合わないときは、待っている相手への連絡文を下書きして、あなたが OK と返した瞬間に送る。電話と Telegram だけ。月 $20。開くアプリはない。',
      heroPrimary: 'はじめる（月 $20）',
      heroSecondary: '仕組みを見る',
      asset: {
        wake: '09:30 · 10 分前の電話 ·「そろそろ動いて」',
        travel1: '09:35 · 5 分前の電話 ·「今すぐ出て」',
        sync: '09:35 · 5 分前の電話 ·「今すぐ出ないと遅刻」',
        travel2: '09:40 · チームシンクへの移動 20 分',
        lunch: '10:00 · チームシンク',
        caption: 'どの予定の前にも 2 回。近づくほど急かす ↑',
      },
      featuresTitle: '4 つのスキル、ひとつの仕事。もう遅刻しない',
      featuresIntro:
        'ライフマネージャーが生活をまるごとまわす。起床も就寝も、会議も通勤も瞑想も仕事も。どの予定も、毎回。4 つのスキルを自分のサーバーで動かして、電話と Telegram でカレンダーを回す。月 $20。',
      liveLabel: '稼働中',
      features: [
        {
          id: 'travel',
          label: 'カレンダー',
          headline: '移動時間を、勝手に押さえる',
          body: '毎朝、ライフマネージャーがその日の予定を見て、それぞれの前に移動時間のブロックを入れる。これで通勤がいつもカレンダーに乗る。10:00 の歯医者をずらせば、移動時間も一緒に動く。',
        },
        {
          id: 'call',
          label: '電話',
          headline: '出発の 10 分前と 5 分前に電話する',
          body: '出発の前に、ライフマネージャーがあなたの番号へ 2 回かける。あとの電話ほど急かす。10 分前は「そろそろ動いて」。5 分前は「今すぐ出て」。予定の名前と場所と行き方を、あなたの電話の国のことばで話す。起床も就寝も、仕事も通勤も瞑想も。どの予定でもかけて、ひとつも飛ばさない。',
        },
        {
          id: 'ask',
          label: 'Telegram',
          headline: '場所がなければ、聞いてくる',
          body: '予定に場所が入っていないと、ライフマネージャーが Telegram で「ここどこ？」と聞く。住所を返信すれば、そのまま予定に書き込む。',
        },
        {
          id: 'notify',
          label: '出席者',
          headline: '遅れそうなら、待つ人に知らせる',
          body: '移動時間から間に合わないと分かると、ライフマネージャーが待っている相手への短い連絡文を書いて、先にあなたに見せる。「OK」と返せば送る。',
        },
      ],
      travelTitle: '移動ブロックの仕組み',
      travelCols: { step: 'ステップ', what: 'やること', api: 'API' },
      travelRows: [
        { what: '今日の時刻つき予定を読む', api: 'GCal REST v3' },
        { what: '移動ブロックがまだ無い予定を探す', api: 'ライフマネージャー' },
        { what: 'それぞれの経路を Google マップに聞く', api: 'Maps Directions' },
        {
          what: '予定が始まる時刻ちょうどに終わるよう [移動] ブロックを入れる',
          api: 'GCal REST v3',
        },
      ],
      travelNotePre: '移動ブロックは重複しない。もう一度スキルを動かしても、「[移動]」のプレフィックスと ',
      travelNoteCode: 'anicca_travel_block',
      travelNotePost: ' プロパティで既存のブロックを見つける。',
      onTimeTitle: '予約して鳴らす。ポーリングはしない',
      onTimeBodyPre:
        '小さなプランナーが数分おきにカレンダーを読んで、予定ごとに 2 本の電話を ',
      onTimeBodyCode: '出発時刻 − 10 / − 5 分',
      onTimeBodyPost: ' ちょうどに予約する。出発時刻は、場所のある予定なら [移動] ブロックの開始、なければ予定の開始。鳴り終わった電話は自分で消える。',
      onTimeResult: '予定ごとに 2 本、あとの電話ほど急かす。無駄な確認はしない。',
      gettingStartedTitle: 'はじめかた',
      gettingStartedSteps: [
        { link: 'オンボーディングを開始', rest: '。Google でログインして、名前を伝える。' },
        { link: '', rest: 'Google カレンダーをつなぐ（Composio でワンクリック）。' },
        { link: '', rest: '電話番号を登録すれば、予定の 10 分前と 5 分前に電話がくる。位置情報は任意でつなげる。' },
        {
          link: '',
          restPre: '登録する：',
          restStrong: '月 $20',
          restPost: '。翌朝カレンダーを開けば、移動ブロックはもう入っている。',
        },
      ],
      cardGetStartedEyebrow: 'はじめる',
      cardGetStartedTitle: 'ライフマネージャー（月 $20）',
      cardGetStartedDesc: 'Google でログイン、名前を伝え、カレンダーをつなぎ、電話番号を登録。位置情報は任意。これで完了。',
      cardColonyEyebrow: 'オープンソース',
      cardColonyTitle: 'ライフマネージャー スキル（OSS）',
      cardColonyDesc: '同じスキルを無料で — 自分の OpenClaw でローカル実行。リポジトリを clone して鍵を入れるだけ。GitHub にある。',
      startTitle: '2タップで始める',
      startIntro: 'スキャンして Telegram ボットを開くか、ウェブで設定。どちらでも：カレンダーをつなぎ、電話番号を登録すれば、出発前にライフマネージャーが電話します。',
      startPhoneEyebrow: 'スマホで',
      startPhoneTitle: 'スキャンして Telegram で開始',
      startPhoneDesc: '@LifeManagerBotbot が開きます — 開始をタップ、名前を入力、カレンダー接続、電話番号を登録。リンク入力は不要。',
      startPhoneLink: 'ボットを直接開く',
      startWebEyebrow: 'ウェブで',
      startWebTitle: 'ウェブで開始',
      startWebDesc: 'ウェブ登録は近日公開。今は左のコードを読み取って Telegram で始めてね。',
      startWebCta: '近日公開',
    },
  },
} as const;

export type LaunchStrings = (typeof launchStrings)[LaunchLocale];

export function getLaunchStrings(locale: LaunchLocale): LaunchStrings {
  return launchStrings[locale];
}
