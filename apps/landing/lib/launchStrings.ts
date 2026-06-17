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
        'Life Manager: connect your Google Calendar and Gmail, add your phone, and it keeps you on time by call and email. $20/mo, no trial.',
      eyebrow: 'Life Manager · $20/mo · no trial',
      heroTitle: 'Never be late again.',
      heroBody:
        'Sign in, connect your calendar and email, add your phone. Life Manager then handles travel time, calls, location asks, and late-notices. 24/7, by phone and email.',
      stepAria: (i: number, n: number) => `step ${i} of ${n}`,
      login: {
        title: 'Sign in to start',
        body: 'Life Manager keeps you on time by phone and email. $20/mo, no trial.',
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
        title: 'Connect your calendar & email',
        body: 'One click via Composio. Life Manager reads your events and sends the asks and late-notices.',
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
        body: 'Life Manager calls 15 minutes before each event with route guidance.',
        placeholder: '+818012345678',
        button: 'Continue',
        error: 'Enter a valid phone number in E.164 form, e.g. +818012345678.',
        saveError: 'Could not save. Try again.',
      },
      pay: {
        titlePrefix: 'You’re set, ',
        titleFallback: 'friend',
        bodyPre: 'Subscribe to activate 24/7 management. ',
        bodyStrong: '$20/mo, no trial.',
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
        skills: [
          { title: 'Travel blocks', desc: 'Travel time goes in before every event.' },
          { title: '15-min calls', desc: 'It calls before each event with route guidance.' },
          {
            title: 'Location asks',
            desc: 'No location? It emails you, and your reply updates the event.',
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
        'Life Manager runs your whole day: wake, sleep, work, commute, meditation. It reads your Google Calendar, blocks out travel time before every event, and phones you 15, 10, and 5 minutes before you need to leave. Each call gets sharper. Nothing to open.',
      heroHeadline: 'Life Manager',
      heroSubtext:
        'Life Manager runs your day so you stop oversleeping and stop showing up late. It reads your calendar, blocks out travel time, and phones you 15, 10, and 5 minutes before you need to leave. Each call gets sharper. If you are going to be late, it drafts the message to whoever is waiting and sends it the moment you say OK. $20/mo. Nothing to open.',
      heroPrimary: 'Get started, $20/mo',
      heroSecondary: 'See how it works',
      asset: {
        wake: '09:25 · call, 15 min before · "Team Sync soon"',
        travel1: '09:30 · call, 10 min before · "time to move"',
        sync: '09:35 · call, 5 min before · "leave now or you’re late"',
        travel2: '09:40 · [Travel] Team Sync, 20 min',
        lunch: '10:00 · Team Sync',
        caption: 'Three calls before every event, each one sharper ↑',
      },
      featuresTitle: 'Four skills, one job: you stop being late',
      featuresIntro:
        'Life Manager runs your whole life: wake, sleep, meetings, commute, meditation, work. Every event, every time. It runs four skills on its own server and works your calendar by phone and email. $20/mo.',
      liveLabel: 'live',
      features: [
        {
          id: 'travel',
          label: 'Calendar',
          headline: 'It blocks out your travel time',
          body: 'Every morning Life Manager reads your Google Calendar, checks Google Maps for each timed event, and drops a "[Travel]" block in front of it, so your commute is always on the calendar. Move a 10:00 dentist appointment and the travel block moves with it.',
        },
        {
          id: 'call',
          label: 'Phone',
          headline: 'It calls you 15, 10, and 5 minutes before you leave',
          body: 'Life Manager phones your real number three times before you need to leave, and each call is sharper than the last. At 15 minutes it gives you a heads-up. At 10 it tells you to move. At 5 it tells you to leave right now. It names the event, the place, and the route, in the language of your phone’s country. Wake, sleep, work, commute, meditation: it calls for every event and skips none.',
        },
        {
          id: 'ask',
          label: 'Email',
          headline: 'No location? It asks you',
          body: 'When an event has no place attached, Life Manager emails you to ask where it is. Reply with the address and it updates the event for you.',
        },
        {
          id: 'notify',
          label: 'Attendees',
          headline: 'Running late? It warns the people waiting',
          body: 'When your travel time says you will not make it, Life Manager writes a short heads-up to the people in the event and emails it to you first. Reply OK and it sends. All by email.',
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
      onTimeBodyCode: 'leave time − 15 / − 10 / − 5 min',
      onTimeBodyPost: '. Leave time is the [Travel] block start when the event has a location, otherwise the event start. Each call deletes itself after it fires.',
      onTimeResult: 'Three calls per event, on the second, each one more urgent. No wasted checks.',
      gettingStartedTitle: 'Getting started',
      gettingStartedSteps: [
        { link: 'Start onboarding', rest: '. Sign in with Google and tell it your name.' },
        { link: '', rest: 'Connect Google Calendar and Gmail (one click, via Composio).' },
        { link: '', rest: 'Add your phone so it can call you 15, 10, and 5 minutes before every event. Share live location if you want.' },
        {
          link: '',
          restPre: 'Subscribe: ',
          restStrong: '$20/mo, no trial',
          restPost: '. Open Google Calendar tomorrow morning and your travel blocks are already there.',
        },
      ],
      cardGetStartedEyebrow: 'get started',
      cardGetStartedTitle: 'Life Manager, $20/mo',
      cardGetStartedDesc: 'Sign in with Google, give your name, connect Calendar and Gmail, add your phone, share location if you want. Done.',
      cardColonyEyebrow: 'open source',
      cardColonyTitle: 'Life Manager Skill (OSS)',
      cardColonyDesc: 'The same skill, free. Drop it into any AI you run yourself. On GitHub.',
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
        'ライフマネージャー。Google カレンダーと Gmail をつなぎ、電話番号を登録すれば、電話とメールで遅刻を防ぐ。月 $20、トライアルなし。',
      eyebrow: 'ライフマネージャー · 月 $20 · トライアルなし',
      heroTitle: 'もう、遅刻しない。',
      heroBody:
        'ログインして、カレンダーとメールをつなぎ、電話番号を登録するだけ。移動時間の確保も、電話も、場所の確認も、遅刻連絡も、ライフマネージャーが引き受ける。24/7、電話とメールで。',
      stepAria: (i: number, n: number) => `ステップ ${i} / ${n}`,
      login: {
        title: 'ログインして始める',
        body: 'ライフマネージャーが、電話とメールで遅刻を防ぐ。月 $20、トライアルなし。',
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
        title: 'カレンダーとメールをつなぐ',
        body: 'Composio でワンクリック接続。ライフマネージャーが予定を読んで、確認や遅刻連絡を送る。',
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
        body: '各予定の 15 分前に、ルートを案内する電話をかける。',
        placeholder: '+818012345678',
        button: '続ける',
        error: 'E.164 形式の有効な電話番号を入力してください（例: +818012345678）。',
        saveError: '保存できませんでした。もう一度お試しください。',
      },
      pay: {
        titlePrefix: '準備完了です、',
        titleFallback: 'あなた',
        bodyPre: 'サブスクで 24/7 の管理を有効化。',
        bodyStrong: '月 $20、トライアルなし。',
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
        skills: [
          { title: '移動時間の確保', desc: '各予定の前に、移動時間を自動で入れる。' },
          { title: '15 分前の電話', desc: '各予定の前に、ルートを案内する電話をかける。' },
          {
            title: '場所の確認',
            desc: '場所が未入力なら、メールで確認する。返信すれば予定を更新する。',
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
        'ライフマネージャーが、あなたの一日をまわす。起床から就寝、仕事も通勤も瞑想も。Google カレンダーを読んで、予定の前に移動時間を入れ、出発の 15 分前、10 分前、5 分前に電話する。近づくほど声は急かす。開くアプリはない。',
      heroHeadline: 'ライフマネージャー',
      heroSubtext:
        'ライフマネージャーが一日をまわすから、もう寝坊しないし、遅刻もしない。カレンダーを読んで移動時間を入れ、出発の 15 分前、10 分前、5 分前に電話する。近づくほど声は急かす。間に合わないときは、待っている相手への連絡文を下書きして、あなたが OK と返した瞬間に送る。電話とメールだけ。月 $20。開くアプリはない。',
      heroPrimary: 'はじめる（月 $20）',
      heroSecondary: '仕組みを見る',
      asset: {
        wake: '09:25 · 15 分前の電話 ·「もうすぐチームシンク」',
        travel1: '09:30 · 10 分前の電話 ·「そろそろ動いて」',
        sync: '09:35 · 5 分前の電話 ·「今すぐ出ないと遅刻」',
        travel2: '09:40 · [移動] チームシンク 20 分',
        lunch: '10:00 · チームシンク',
        caption: 'どの予定の前にも 3 回。近づくほど急かす ↑',
      },
      featuresTitle: '4 つのスキル、ひとつの仕事。もう遅刻しない',
      featuresIntro:
        'ライフマネージャーが生活をまるごとまわす。起床も就寝も、会議も通勤も瞑想も仕事も。どの予定も、毎回。4 つのスキルを自分のサーバーで動かして、電話とメールでカレンダーを回す。月 $20。',
      liveLabel: '稼働中',
      features: [
        {
          id: 'travel',
          label: 'カレンダー',
          headline: '移動時間を、勝手に押さえる',
          body: '毎朝、ライフマネージャーが Google カレンダーを読んで、時刻のある予定ごとに Google マップで経路を調べ、予定の前に「[移動]」ブロックを入れる。これで通勤がいつもカレンダーに乗る。10:00 の歯医者をずらせば、移動ブロックも一緒に動く。',
        },
        {
          id: 'call',
          label: '電話',
          headline: '出発の 15 分前、10 分前、5 分前に電話する',
          body: '出発の前に、ライフマネージャーがあなたの番号へ 3 回かける。近づくほど声は急かす。15 分前は軽い予告。10 分前は「そろそろ動いて」。5 分前は「今すぐ出て」。予定の名前と場所と行き方を、あなたの電話の国のことばで話す。起床も就寝も、仕事も通勤も瞑想も。どの予定でもかけて、ひとつも飛ばさない。',
        },
        {
          id: 'ask',
          label: 'メール',
          headline: '場所がなければ、聞いてくる',
          body: '予定に場所が入っていないと、ライフマネージャーがメールで「ここどこ？」と聞く。住所を返信すれば、そのまま予定に書き込む。',
        },
        {
          id: 'notify',
          label: '出席者',
          headline: '遅れそうなら、待つ人に知らせる',
          body: '移動時間から間に合わないと分かると、ライフマネージャーが待っている相手への短い連絡文を書いて、先にあなたへメールする。「OK」と返せば送る。ぜんぶメールで済む。',
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
        '小さなプランナーが数分おきにカレンダーを読んで、予定ごとに 3 本の電話を ',
      onTimeBodyCode: '出発時刻 − 15 / − 10 / − 5 分',
      onTimeBodyPost: ' ちょうどに予約する。出発時刻は、場所のある予定なら [移動] ブロックの開始、なければ予定の開始。鳴り終わった電話は自分で消える。',
      onTimeResult: '予定ごとに 3 本、秒単位で。近づくほど急かす。無駄な確認はしない。',
      gettingStartedTitle: 'はじめかた',
      gettingStartedSteps: [
        { link: 'オンボーディングを開始', rest: '。Google でログインして、名前を伝える。' },
        { link: '', rest: 'Google カレンダーと Gmail をつなぐ（Composio でワンクリック）。' },
        { link: '', rest: '電話番号を登録すれば、予定の 15 分前、10 分前、5 分前に電話がくる。位置情報は任意でつなげる。' },
        {
          link: '',
          restPre: '登録する：',
          restStrong: '月 $20、トライアルなし',
          restPost: '。翌朝カレンダーを開けば、移動ブロックはもう入っている。',
        },
      ],
      cardGetStartedEyebrow: 'はじめる',
      cardGetStartedTitle: 'ライフマネージャー（月 $20）',
      cardGetStartedDesc: 'Google でログイン、名前を伝え、カレンダーと Gmail をつなぎ、電話番号を登録。位置情報は任意。これで完了。',
      cardColonyEyebrow: 'オープンソース',
      cardColonyTitle: 'ライフマネージャー スキル（OSS）',
      cardColonyDesc: '同じスキルを無料で。自分で動かす AI に組み込める。GitHub にある。',
    },
  },
} as const;

export type LaunchStrings = (typeof launchStrings)[LaunchLocale];

export function getLaunchStrings(locale: LaunchLocale): LaunchStrings {
  return launchStrings[locale];
}
