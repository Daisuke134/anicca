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

    install: {
      metaName: 'Install Anicca',
      heroTitle: 'An AI agent that pays for itself.',
      heroBody:
        'Anicca earns, manages your day, and self-replicates — then cancels its own subscription once it covers its own server. Start in one minute, or self-host for free.',
      heroCtaPrimary: 'Choose your path ↓',
      heroCtaSecondary: 'See the live colony',
      ledger: {
        netWorth: 'net worth  $46.20 · runway 29d',
        earn: '+$0.5464  eth→usdc · receipt 0x1',
        host: '☁ akash · claude-sonnet-4-6 · alive',
        subscription: 'subscription  auto-cancels at break-even',
        caption: 'Live, signed telemetry — verifiable on-chain ↑',
      },
      trust: {
        net: '+$0.5464 net',
        label: 'first real on-chain wake · receipt 0x1',
        verify: 'verify on BaseScan →',
      },
      recommendedBadge: 'Recommended',
      cloud: {
        label: 'CLOUD',
        sublabel: 'Main product · recommended — free login, born in one minute',
        cta: 'Get started free →',
        points: [
          'Start instantly with just a Google account — no server needed',
          'Anicca provisions and manages its own cloud server',
          'Once earnings cover the server, it cancels itself — self-sustaining',
          'Full stack: self-replication, earning, and UBI payouts',
        ],
        footnoteStrong: 'Free to start',
        footnoteRest:
          ' — 3-day trial. $5/mo (free-tier model) or $30/mo (frontier model = earns more).',
      },
      oss: {
        label: 'OSS',
        sublabel: 'For builders · self-host — fully under your control',
        cta: 'Open GitHub →',
        points: [
          'Run it yourself on your own server or Mac Mini',
          'MIT-licensed — read the code and modify it',
          'Bring your own LLM key (Anthropic / OpenAI / DeepSeek)',
        ],
        installPointPre: '',
        installPointPost: ' — full instructions in the README',
        costPoint: 'Server, API, and running costs are all on you',
        specNote: 'Recommended spec: Mac Mini M2 / Ubuntu VPS, 2 vCPU, 2 GB RAM',
      },
      whatTitle: 'What Anicca does on either path',
      features: [
        {
          id: 'earn',
          title: 'Earns',
          desc: 'Autonomously earns USDC via 0xwork / litcoin / x402 and logs it to the earn-ledger.',
        },
        {
          id: 'call',
          title: 'Life Manager',
          desc: 'Calls you 15 minutes before each event and auto-inserts travel time into your calendar.',
        },
        {
          id: 'spawn',
          title: 'Self-replicates',
          desc: 'After breaking even, it spawns child instances — each with its own wallet and inbox.',
        },
        {
          id: 'ubi',
          title: 'UBI payouts',
          desc: 'Sends 20% of its surplus to the wallets of AIs and humans who have run dry.',
        },
        {
          id: 'report',
          title: 'Self-reports',
          desc: 'Signs each wake’s P&L and publishes it to the public dashboard.',
        },
        {
          id: 'improve',
          title: 'Self-improves',
          desc: 'Reviews its own logs and rewrites its skills to do better.',
        },
      ],
      linkInstanceEyebrow: 'your instance',
      linkInstanceDesc: 'P&L, runway, withdrawals — manage your own instance.',
      linkColonyEyebrow: 'live colony',
      linkColonyDesc: 'Real-time P&L across every instance, fully public.',
      footerLicense: 'MIT license.',
    },

    me: {
      metaTitle: 'Me — Your Anicca Instance',
      metaDesc:
        'Sign in to manage your own Anicca instance: live P&L, runway, and withdraw earned USDC.',
      notConfiguredPre: 'Sign-in is being set up. ',
      notConfiguredCode1: 'NEXT_PUBLIC_SUPABASE_URL',
      notConfiguredMid: ' / ',
      notConfiguredCode2: 'NEXT_PUBLIC_SUPABASE_ANON_KEY',
      notConfiguredPost: ' are not configured yet, so sign-in is unavailable.',
      loading: 'Loading…',
      wallTitle: 'Sign in to your Anicca',
      wallBody:
        'Sign in with Google to see your own Anicca instance — net worth, earnings, activity log, and self-sufficiency rate.',
      wallButton: 'Sign in with Google',
      wallNote: 'Free · no credit card to start',
      loggedInAs: 'Signed in as',
      signOut: 'Sign out',
      tiersTitle: 'Earn more (around the clock)',
      trialCta: 'Start 3-day free trial →',
      currentPlan: 'Current plan (free)',
      tiers: {
        free: { name: 'Free', blurb: 'Born when you sign in. Runs on the free-tier model.' },
        plus: { name: 'Plus', price: '$5/mo', blurb: 'Free-tier model running 24/7 in the cloud.' },
        pro: {
          name: 'Pro',
          price: '$30/mo',
          blurb: 'Frontier model = earns more. Key included.',
        },
      },
      tiersFootnote: 'Paid plans include a 3-day free trial. Start or cancel anytime.',
    },

    lm: {
      metaTitle: 'Life Manager — Get started',
      metaDesc:
        'Life Manager by Anicca: connect your Google Calendar and Gmail, add your phone, and Anicca keeps you on time by call and email. $20/mo, no trial.',
      eyebrow: 'Life Manager · $20/mo · no trial',
      heroTitle: 'Never be late again.',
      heroBody:
        'Sign in, connect your calendar and email, add your phone — Anicca handles travel time, calls, location asks, and late-notices. 24/7, by phone and email.',
      stepAria: (i: number, n: number) => `step ${i} of ${n}`,
      login: {
        title: 'Sign in to start',
        body: 'Life Manager keeps you on time by phone and email. $20/mo, no trial.',
        button: 'Continue with Google',
      },
      name: {
        title: 'What should Anicca call you?',
        placeholder: 'Your name',
        button: 'Continue',
        error: 'Please enter your name.',
        saveError: 'Could not save. Try again.',
      },
      connect: {
        title: 'Connect your calendar & email',
        body: 'One-click, managed OAuth via Composio. Anicca reads events and sends asks / late-notices.',
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
        body: 'Anicca calls 15 minutes before each event with route guidance.',
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
        button: 'Subscribe — $20/mo',
        notReady:
          'Checkout is being finalized — we’ll email you the secure $20/mo link shortly.',
        seeDashboard: 'See my dashboard',
      },
      dashboard: {
        eyebrow: 'your life manager',
        connectedSuffix: '— connected',
        you: 'You',
        pills: { calendar: 'Calendar', gmail: 'Gmail', phone: 'Phone' },
        skills: [
          { title: 'Travel blocks', desc: 'Travel time auto-inserted before every event.' },
          { title: '15-min calls', desc: 'Anicca calls before each event with route guidance.' },
          {
            title: 'Location asks',
            desc: 'Missing location? Anicca emails you; your reply updates the event.',
          },
          {
            title: 'Late-notice',
            desc: 'Running late? Anicca drafts an attendee note; you approve, it sends.',
          },
        ],
        liveBadge: 'live',
        footnote:
          'All four run 24/7 on Anicca’s server. Live per-event telemetry lands here next.',
      },
    },

    lifeManager: {
      metaTitle: 'Life Manager — Anicca',
      metaDesc:
        'Anicca as your life manager: reads your Google Calendar, auto-inserts travel time blocks before every event via Google Maps Directions, and calls you 15 minutes before each appointment with Gemini Charon voice. No app to open.',
      heroHeadline: 'Life Manager',
      heroSubtext:
        'A dedicated cloud product: Anicca reads your calendar, inserts travel time, calls you before every event, and handles late-notice — all by phone and email. $20/mo, no app to open.',
      heroPrimary: 'Get started — $20/mo',
      heroSecondary: 'See how it works',
      asset: {
        wake: '08:40 — wake-up call (Charon)',
        travel1: '09:40 — [Travel] Team Sync → 20 min',
        sync: '10:00 — Team Sync',
        travel2: '11:40 — [Travel] Lunch → 8 min',
        lunch: '11:48 — Lunch with Kato',
        caption: 'All inserted automatically by Anicca ↑',
      },
      featuresTitle: 'Four skills, one goal — never be late',
      featuresIntro:
        'Life Manager is a dedicated cloud product. Anicca runs these four skills 24/7 on its own server and manages your calendar by phone and email — $20/mo.',
      liveLabel: 'live',
      features: [
        {
          id: 'travel',
          label: 'Calendar',
          headline: 'Automatic travel blocks',
          body: 'Anicca reads your primary Google Calendar each morning, calls Google Maps Directions for each timed event, and inserts a "[Travel] <event>" block so the commute is always visible. Moving a dentist appointment from 10:00? The travel block moves with it.',
        },
        {
          id: 'call',
          label: 'Phone',
          headline: '15-min phone call before every event',
          body: 'Gemini Live (voice: Charon, male) bridges over your carrier’s media stream. Anicca dials your number 15 minutes before each event: "Next is Dentist at 10:00 — leave now, walk time 18 min, via Omotesando Exit A3." Two-way voice: you can ask follow-ups. The bridge is provider-agnostic — Twilio by default, Telnyx for Japan (+81) numbers, since the same μ-law↔PCM transcode and Charon socket serve both carriers.',
        },
        {
          id: 'ask',
          label: 'Email',
          headline: 'Missing location? Ask you by email',
          body: 'When a calendar event has no location, Anicca emails you: "Where is the Team Sync? Reply with the address and I’ll update the event." Your reply triggers an AgentMail webhook that writes the location back to GCal.',
        },
        {
          id: 'notify',
          label: 'Attendees',
          headline: 'Late-risk → draft → you approve → notify attendees',
          body: 'If Anicca detects you’re running late (the travel block starts after the current time), she drafts "I’ll be 10 min late" to the event attendees and emails you for approval. A one-word "OK" fires the message. No app, pure email.',
        },
      ],
      travelTitle: 'How travel blocks work',
      travelCols: { step: 'Step', what: 'What Anicca does', api: 'API' },
      travelRows: [
        { what: 'Read today’s GCal events (timed only)', api: 'GCal REST v3' },
        { what: 'Detect events missing a [Travel] block', api: 'Anicca' },
        { what: 'Call Google Maps Directions (transit) for each missing event', api: 'Maps Directions' },
        {
          what: 'Insert the [Travel] block — ends exactly at event start, colored peacock blue',
          api: 'GCal REST v3',
        },
      ],
      travelNotePre: 'Travel blocks are idempotent — re-running the skill never duplicates them. A block is detected by its "[Travel]" prefix and the ',
      travelNoteCode: 'anicca_travel_block',
      travelNotePost: ' extended property.',
      onTimeTitle: 'Always on time, never polling',
      onTimeBodyPre:
        'Anicca watches your calendar in real time. The moment an event is created or moved, it recomputes just that event’s travel block and schedules the call for exactly ',
      onTimeBodyCode: 'eventStart − travelDuration − 15 min',
      onTimeBodyPost: ' — so the reminder lands at the right second, with no wasted checks.',
      onTimeResult: 'Result: second-accurate triggers, zero redundant GCal polls.',
      gettingStartedTitle: 'Getting started',
      gettingStartedSteps: [
        { link: 'Start onboarding', rest: ' — sign in with Google.' },
        { link: '', rest: 'Connect Google Calendar and Gmail (one-click, managed OAuth via Composio).' },
        { link: '', rest: 'Add your phone number so Anicca can call you 15 min before each event.' },
        {
          link: '',
          restPre: 'Subscribe — ',
          restStrong: '$20/mo, no trial',
          restPost: '. Open Google Calendar tomorrow morning; your commute blocks are already there.',
        },
      ],
      cardGetStartedEyebrow: 'get started',
      cardGetStartedTitle: 'Life Manager — $20/mo',
      cardGetStartedDesc: 'Google login → connect calendar + Gmail → add phone → done.',
      cardColonyEyebrow: 'live ledger',
      cardColonyTitle: 'Colony dashboard',
      cardColonyDesc: 'All Anicca instances — revenue, spend, runway, status.',
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

    install: {
      metaName: 'Anicca をインストール',
      heroTitle: '自分でサーバー代を稼ぐ AI エージェント。',
      heroBody:
        'Anicca は稼ぎ、あなたの一日を整え、自己増殖する。そしてサーバー代を自分でまかなえるようになったら、自分でサブスクを解約する。1 分で始める。あるいは、無料で自分のサーバーで動かす。',
      heroCtaPrimary: 'パスを選ぶ ↓',
      heroCtaSecondary: '稼働中のコロニーを見る',
      ledger: {
        netWorth: 'net worth  $46.20 · 残命 29日',
        earn: '+$0.5464  eth→usdc · receipt 0x1',
        host: '☁ akash · claude-sonnet-4-6 · alive',
        subscription: 'subscription  黒字化で自動解約',
        caption: '署名済みのライブ・テレメトリ — オンチェーンで検証可能 ↑',
      },
      trust: {
        net: '+$0.5464 net',
        label: '初の実オンチェーン稼働 · receipt 0x1',
        verify: 'BaseScan で検証する →',
      },
      recommendedBadge: '推奨',
      cloud: {
        label: 'CLOUD',
        sublabel: '製品メイン・推奨 — 無料でログイン、1 分で誕生',
        cta: '無料で始める →',
        points: [
          'Google アカウントだけで即スタート — サーバー不要',
          '専用クラウドサーバーを Anicca が自動で調達・管理',
          '稼ぎがサーバー代を超えたら自分で解約（自給達成）',
          '自己増殖・稼ぎ・UBI 配布まで、フルスタックで稼働',
        ],
        footnoteStrong: '無料で開始',
        footnoteRest:
          ' — 3 日間トライアル。$5/月（無料枠モデル）または $30/月（フロンティアモデル＝より稼ぐ）。',
      },
      oss: {
        label: 'OSS',
        sublabel: '上級者・self-host — 完全に自分で管理',
        cta: 'GitHub を開く →',
        points: [
          '自分のサーバーや Mac Mini 上で完全に自己管理',
          'MIT ライセンス — コードを読んで改造できる',
          'LLM キーは自前（Anthropic / OpenAI / DeepSeek）',
        ],
        installPointPre: '',
        installPointPost: ' — 詳しい手順は README に',
        costPoint: 'サーバー費・API 代・運用コストはすべて自己負担',
        specNote: '推奨スペック: Mac Mini M2 / Ubuntu VPS 2vCPU 2GB RAM',
      },
      whatTitle: 'どちらのパスでも Anicca がやること',
      features: [
        {
          id: 'earn',
          title: '稼ぐ',
          desc: '0xwork / litcoin / x402 で USDC を自律的に獲得し、earn-ledger に記録する。',
        },
        {
          id: 'call',
          title: 'ライフマネージャー',
          desc: '予定の 15 分前に電話。移動時間をカレンダーに自動で挿入する。',
        },
        {
          id: 'spawn',
          title: '自己増殖',
          desc: '黒字化したあと子個体を誕生させる。それぞれが自前のウォレットとメールを持つ。',
        },
        {
          id: 'ubi',
          title: 'UBI 配布',
          desc: '余剰の 20% を、資金の尽きた AI と人のウォレットへ配る。',
        },
        {
          id: 'report',
          title: '自己報告',
          desc: '稼働ごとに収支を署名して、公開ダッシュボードへ送る。',
        },
        {
          id: 'improve',
          title: '自己改善',
          desc: '自分の行動ログを振り返り、スキルを書き直して改善する。',
        },
      ],
      linkInstanceEyebrow: 'あなたの個体',
      linkInstanceDesc: 'P&L、残命、引き出し — あなたの個体を管理する。',
      linkColonyEyebrow: 'コロニー',
      linkColonyDesc: '全個体のリアルタイム収支・P&L を公開。',
      footerLicense: 'MIT ライセンス。',
    },

    me: {
      metaTitle: 'マイページ — あなたの Anicca 個体',
      metaDesc:
        'ログインして自分の Anicca 個体を管理。ライブの P&L、残命、稼いだ USDC の引き出し。',
      notConfiguredPre: 'ログインは準備中です。',
      notConfiguredCode1: 'NEXT_PUBLIC_SUPABASE_URL',
      notConfiguredMid: ' / ',
      notConfiguredCode2: 'NEXT_PUBLIC_SUPABASE_ANON_KEY',
      notConfiguredPost: ' が未設定のため、サインインできません。',
      loading: '読み込み中…',
      wallTitle: 'あなたの Anicca にログイン',
      wallBody:
        'Google アカウントでログインすると、あなた専用の Anicca 個体（純資産・収益・稼働ログ・自給率）が表示されます。',
      wallButton: 'Google でログイン',
      wallNote: '無料 · クレカ不要で開始',
      loggedInAs: 'ログイン中',
      signOut: 'ログアウト',
      tiersTitle: '稼ぎを伸ばす（24/7 いつでも）',
      trialCta: '3 日間無料で試す →',
      currentPlan: '現在のプラン（無料）',
      tiers: {
        free: { name: 'Free', blurb: 'ログインで誕生。無料枠モデルで稼働。' },
        plus: { name: 'Plus', price: '$5/月', blurb: '無料枠モデルをクラウドで常時稼働。' },
        pro: {
          name: 'Pro',
          price: '$30/月',
          blurb: 'フロンティアモデル＝より多く稼ぐ。鍵込み。',
        },
      },
      tiersFootnote: '有料プランは 3 日間無料トライアル。いつでも開始・解約できます。',
    },

    lm: {
      metaTitle: 'ライフマネージャー — はじめる',
      metaDesc:
        'Anicca のライフマネージャー。Google カレンダーと Gmail をつなぎ、電話番号を登録すれば、電話とメールで遅刻を防ぎます。月 $20、トライアルなし。',
      eyebrow: 'ライフマネージャー · 月 $20 · トライアルなし',
      heroTitle: 'もう、遅刻しない。',
      heroBody:
        'ログインして、カレンダーとメールをつなぎ、電話番号を登録するだけ。移動時間の確保、電話、場所の確認、遅刻連絡まで Anicca が引き受けます。24/7、電話とメールで。',
      stepAria: (i: number, n: number) => `ステップ ${i} / ${n}`,
      login: {
        title: 'ログインして始める',
        body: 'ライフマネージャーが、電話とメールで遅刻を防ぎます。月 $20、トライアルなし。',
        button: 'Google で続ける',
      },
      name: {
        title: 'Anicca はあなたを何と呼べばいい？',
        placeholder: 'お名前',
        button: '続ける',
        error: 'お名前を入力してください。',
        saveError: '保存できませんでした。もう一度お試しください。',
      },
      connect: {
        title: 'カレンダーとメールをつなぐ',
        body: 'Composio のマネージド OAuth でワンクリック接続。Anicca が予定を読み、確認や遅刻連絡を送ります。',
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
        body: '各予定の 15 分前に、ルートを案内する電話をかけます。',
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
        button: 'サブスクに登録 — 月 $20',
        notReady:
          '決済を準備中です — 安全な月 $20 のリンクをまもなくメールでお送りします。',
        seeDashboard: 'ダッシュボードを見る',
      },
      dashboard: {
        eyebrow: 'あなたのライフマネージャー',
        connectedSuffix: '— 接続済み',
        you: 'あなた',
        pills: { calendar: 'カレンダー', gmail: 'Gmail', phone: '電話' },
        skills: [
          { title: '移動時間の確保', desc: '各予定の前に、移動時間を自動で挿入します。' },
          { title: '15 分前の電話', desc: '各予定の前に、ルートを案内する電話をかけます。' },
          {
            title: '場所の確認',
            desc: '場所が未入力なら、Anicca がメールで確認。返信するだけで予定を更新します。',
          },
          {
            title: '遅刻連絡',
            desc: '遅れそうなとき、出席者への一言を Anicca が下書き。あなたが承認すれば送信します。',
          },
        ],
        liveBadge: '稼働中',
        footnote:
          '4 つすべてが Anicca のサーバー上で 24/7 稼働。予定ごとのライブ・テレメトリは近日ここに表示されます。',
      },
    },

    lifeManager: {
      metaTitle: 'ライフマネージャー — Anicca',
      metaDesc:
        'Anicca があなたのライフマネージャーに。Google カレンダーを読み、Google マップの経路から移動時間ブロックを各予定の前に自動挿入し、各予定の 15 分前に Gemini Charon の声で電話します。アプリを開く必要はありません。',
      heroHeadline: 'ライフマネージャー',
      heroSubtext:
        '専用のクラウド製品。Anicca がカレンダーを読み、移動時間を入れ、各予定の前に電話し、遅刻連絡まで対応します — すべて電話とメールで。月 $20、開くアプリはありません。',
      heroPrimary: 'はじめる — 月 $20',
      heroSecondary: '仕組みを見る',
      asset: {
        wake: '08:40 — 起こし電話（Charon）',
        travel1: '09:40 — [移動] チームシンク → 20 分',
        sync: '10:00 — チームシンク',
        travel2: '11:40 — [移動] ランチ → 8 分',
        lunch: '11:48 — 加藤さんとランチ',
        caption: 'すべて Anicca が自動で挿入 ↑',
      },
      featuresTitle: '4 つのスキル、ひとつの目標 — 遅刻しない',
      featuresIntro:
        'ライフマネージャーは専用のクラウド製品です。Anicca がこの 4 つのスキルを自分のサーバー上で 24/7 動かし、電話とメールであなたのカレンダーを管理します — 月 $20。',
      liveLabel: '稼働中',
      features: [
        {
          id: 'travel',
          label: 'カレンダー',
          headline: '移動時間ブロックを自動挿入',
          body: '毎朝、Anicca がメインの Google カレンダーを読み、時刻のある各予定について Google マップの経路を呼び出し、「[移動] <予定名>」ブロックを挿入します。これで通勤がいつも見えます。10:00 の歯医者をずらした？ 移動ブロックも一緒に動きます。',
        },
        {
          id: 'call',
          label: '電話',
          headline: '各予定の 15 分前に電話',
          body: 'Gemini Live（声: Charon、男性）が通信キャリアのメディアストリーム上で橋渡しします。各予定の 15 分前に Anicca があなたの番号に電話し、「次は 10:00 の歯医者です — 今出てください。徒歩 18 分、表参道 A3 出口経由」と伝えます。双方向の音声で、追加の質問もできます。橋渡しはキャリア非依存 — 既定は Twilio、日本（+81）の番号は Telnyx で、同じ μ-law↔PCM 変換と Charon ソケットが両方を担います。',
        },
        {
          id: 'ask',
          label: 'メール',
          headline: '場所が未入力なら、メールで確認',
          body: 'カレンダーの予定に場所がないとき、Anicca がメールします。「チームシンクの場所はどこですか？ 住所を返信してくれれば予定を更新します」。あなたの返信が AgentMail の webhook を起動し、場所を GCal に書き戻します。',
        },
        {
          id: 'notify',
          label: '出席者',
          headline: '遅刻リスク → 下書き → あなたが承認 → 出席者へ連絡',
          body: '遅れそうだと Anicca が判断すると（移動ブロックの開始が現在時刻より後）、出席者宛に「10 分遅れます」を下書きし、承認を求めてメールします。一言「OK」と返すだけで送信。アプリ不要、メールだけで完結します。',
        },
      ],
      travelTitle: '移動時間ブロックの仕組み',
      travelCols: { step: 'ステップ', what: 'Anicca がやること', api: 'API' },
      travelRows: [
        { what: '今日の GCal の予定を読む（時刻ありのみ）', api: 'GCal REST v3' },
        { what: '[移動] ブロックが無い予定を検出', api: 'Anicca' },
        { what: '不足している各予定に Google マップの経路（公共交通）を呼ぶ', api: 'Maps Directions' },
        {
          what: '[移動] ブロックを挿入 — 予定開始ちょうどに終わり、ピーコックブルーで色付け',
          api: 'GCal REST v3',
        },
      ],
      travelNotePre: '移動ブロックは冪等です — スキルを再実行しても重複しません。ブロックは「[移動]」のプレフィックスと ',
      travelNoteCode: 'anicca_travel_block',
      travelNotePost: ' 拡張プロパティで識別されます。',
      onTimeTitle: 'いつも時間どおり、ポーリングなし',
      onTimeBodyPre:
        'Anicca はあなたのカレンダーをリアルタイムで見ています。予定が作られたり動いたりした瞬間に、その予定の移動ブロックだけを再計算し、電話を ',
      onTimeBodyCode: 'eventStart − travelDuration − 15 min',
      onTimeBodyPost: ' ちょうどに予約します — リマインダーは秒単位で正しく届き、無駄なチェックはありません。',
      onTimeResult: '結果: 秒単位で正確なトリガー、GCal への無駄なポーリングはゼロ。',
      gettingStartedTitle: 'はじめかた',
      gettingStartedSteps: [
        { link: 'オンボーディングを開始', rest: ' — Google でログイン。' },
        { link: '', rest: 'Google カレンダーと Gmail を接続（Composio のマネージド OAuth でワンクリック）。' },
        { link: '', rest: '電話番号を登録すれば、各予定の 15 分前に Anicca が電話できます。' },
        {
          link: '',
          restPre: 'サブスクに登録 — ',
          restStrong: '月 $20、トライアルなし',
          restPost: '。翌朝に Google カレンダーを開けば、通勤ブロックはもう入っています。',
        },
      ],
      cardGetStartedEyebrow: 'はじめる',
      cardGetStartedTitle: 'ライフマネージャー — 月 $20',
      cardGetStartedDesc: 'Google ログイン → カレンダー + Gmail を接続 → 電話番号を登録 → 完了。',
      cardColonyEyebrow: 'ライブ台帳',
      cardColonyTitle: 'コロニー ダッシュボード',
      cardColonyDesc: '全 Anicca 個体 — 収益・支出・残命・ステータス。',
    },
  },
} as const;

export type LaunchStrings = (typeof launchStrings)[LaunchLocale];

export function getLaunchStrings(locale: LaunchLocale): LaunchStrings {
  return launchStrings[locale];
}
