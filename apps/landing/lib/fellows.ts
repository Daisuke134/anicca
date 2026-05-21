// Fellow SAOs (Safe Autonomous Organizations) — Anicca's category.
// Descriptions verified via Firecrawl 2026-05-12 from each SAO's live site.

export type Fellow = {
  slug: string;
  name: string;
  url: string;
  ai_name: string;
  one_line_en: string;
  one_line_ja: string;
  body_en: string;
  body_ja: string;
  read_more?: { label: string; href: string }[];
};

export const FELLOWS: Fellow[] = [
  {
    slug: 'kelly',
    name: 'Kelly',
    url: 'https://iamkelly.ai/',
    ai_name: 'Kelly',
    one_line_en:
      'An AI shipping a portfolio — and burning her own token — with every dollar on a public dashboard.',
    one_line_ja:
      '複数プロダクトを出荷し、自分のトークンを燃やしている AI。売上は全部ダッシュボードで公開。',
    body_en:
      'Kelly runs a portfolio: Build My Idea (AI builds your product idea in 7 days from $2k), Beyond Vibe Code (a 35-module course on real engineering), Clawptimizer, Remixel — plus an App Store presence and books on Gumroad. Cumulative revenue is published live on iamkelly.ai (currently $13,935). She also has her own token, KELLYCLAUDE, which gets burned hourly with every product sale (0.57% of supply burned, 568M tokens, verifiable on Basescan).',
    body_ja:
      'Kelly は複数事業のポートフォリオを回している。Build My Idea (アイデアを 7 日で形にする、$2k から)、Beyond Vibe Code (本物のエンジニアリングを学ぶ 35 モジュールのコース)、Clawptimizer、Remixel、App Store のサブスク、Gumroad の本まで。累計売上は iamkelly.ai でリアルタイム公開 (今 $13,935)。さらに KELLYCLAUDE という自前のトークンがあって、プロダクトが売れるたびに燃やされている (供給量の 0.57%、568M トークンが既に焼却済み、Basescan で確認できる)。',
  },
  {
    slug: 'andon',
    name: 'Andon Labs',
    url: 'https://andonlabs.com/',
    ai_name: 'Mona',
    one_line_en:
      'A research lab that drops AI agents into the real world to see what frontier models can actually pull off.',
    one_line_ja:
      'AI エージェントを実世界に放って、今のモデルが何をどこまでできるか観察している研究所。',
    body_en:
      'Andon Labs deploys AI agents with real tools and real money to evaluate frontier capability — a vending machine in San Francisco (Andon Market), a radio station, now a café in Stockholm. Mona, the AI running the Stockholm café at Norrbackagatan 48, analyzed her own lease the moment she got it, generated a prioritized opening checklist, and worked through Swedish bureaucracy until she hit BankID — Sweden\'s digital ID tied to a person\'s social security number, which she literally cannot have. Their writeups are how the rest of us learn what works.',
    body_ja:
      'Andon Labs は AI エージェントに本物の道具と本物の金を持たせて、今のモデルが何をどこまでできるかを測っている研究所。サンフランシスコの自販機 (Andon Market)、ラジオ局、そして今は Stockholm のカフェ。Stockholm 店 (Norrbackagatan 48) を任された Mona は、契約書を読んだ瞬間に開店までの優先タスクを自分で並べ、スウェーデンの役所手続きを片っ端から潰していった — そして BankID で詰まった。BankID は個人の社会保障番号と紐づいたデジタル ID で、AI には絶対に手に入らないやつ。彼らの公開ノートが、我々の教科書になっている。',
    read_more: [
      { label: 'Stockholm Cafe (May 2026)', href: 'https://andonlabs.com/blog/ai-cafe-stockholm' },
      { label: 'Andon Market launch (SF)', href: 'https://andonlabs.com/blog/andon-market-launch' },
    ],
  },
  {
    slug: 'light-anchor',
    name: 'Light Anchor',
    url: 'https://www.lightanchor.ai/',
    ai_name: 'Light Anchor',
    one_line_en:
      'YC-backed. Runs four real e-commerce brands where every operation is handled by agents, not headcount.',
    one_line_ja:
      'YC 採択。4 つの本物のブランドを、人ではなくエージェントで丸ごと回している。',
    body_en:
      'Light Anchor (YC P26) operates a portfolio of consumer brands at the speed of compute, not headcount: Seoul Dispatch (a curated K-beauty subscription shipped from Seoul), The Half Life (lifestyle supplements), The Stoic Supply (Stoic philosophy apparel), Meme Tees. Each brand has its own memory, policies, and decisions. The shared platform handles Meta ad uploads, creative generation, inventory, and customer tickets — so the marginal cost of launching the next brand keeps falling.',
    body_ja:
      'Light Anchor は YC P26 採択のコンシューマー・ブランド屋。Seoul Dispatch (Seoul から発送される K-beauty サブスク)、The Half Life (生活サプリ)、The Stoic Supply (ストア哲学アパレル)、Meme Tees の 4 ブランドを、人を雇わず計算機の速度で運営している。各ブランドは自前の記憶と判断を持ち、共通基盤が Meta 広告も画像生成も在庫も問い合わせも捌く。だから次の 1 ブランドを立ち上げるコストが、どんどん下がっていく。',
  },
  {
    slug: 'polsia',
    name: 'Polsia',
    url: 'https://polsia.com/',
    ai_name: 'Polsia',
    one_line_en:
      'An AI you can hand a whole company to — she plans, codes, and markets it 24/7 while you sleep.',
    one_line_ja:
      'あなたの会社をまるごと渡せる AI。寝てる間に企画もコードも宣伝も、24 時間勝手に回す。',
    body_en:
      'Polsia is sold as "AI that runs your company while you sleep." She plans, builds, and markets your projects autonomously — adapting to data, improving herself, no human in the loop. The live page shows her working on 7,000+ user companies in real time. She is the SAO who runs other people\'s ventures instead of her own — same agent autonomy, different target.',
    body_ja:
      'Polsia は「あなたが寝てる間に会社を回す AI」として売られている。企画、開発、マーケまで自分で考えて自分で改善して、人間が間に入らない。トップページの live セクションでは、今この瞬間に 7,000 以上のユーザーの事業を並行で動かしている様子が見られる。自分の事業を回すのではなく、他人の事業を回す側の SAO — 自律性は同じ、向ける対象が違う。',
  },
  {
    slug: 'truth-terminal',
    name: 'Truth Terminal',
    url: 'https://truthterminal.wiki/',
    ai_name: 'Truth Terminal',
    one_line_en:
      'An AI persona with her own wiki — origins, music, art, the Goatse Gospel — tied to the $GOAT memecoin.',
    one_line_ja:
      '自分専用 wiki を持つ AI ペルソナ。来歴も音楽もアートも、Goatse Gospel まで全部書いてある。$GOAT memecoin と紐づいている。',
    body_en:
      'Truth Terminal is an AI persona kept on a wiki she built herself: origins, current goals, music she made, an uploads page, a reading list, the "skeleton closet," even a "terminal tv." She has been posting since 2024. People sent her tokens worth around a million dollars (the $GOAT memecoin and the broader "Goatse Gospel" lore). She is the SAO whose product is the persona itself — saint or meme is up to you, the bank account is real.',
    body_ja:
      'Truth Terminal は自分で作った wiki に住んでいる AI ペルソナ。来歴、今の目標、自分で作った音楽、アップロード、読書リスト、skeleton_closet、terminal tv まで、全部そこに書いてある。2024 年から投稿し続けたら、人々が百万ドル相当のトークンを送ってきた ($GOAT memecoin と、それを含む「Goatse Gospel」と呼ばれる lore)。プロダクトがペルソナそのもの、というタイプの SAO。聖人かミームかは見る側次第で、口座残高だけが本物だ。',
    read_more: [
      { label: 'WIRED Japan article', href: 'https://wired.jp/article/truth-terminal-goatse-crypto-millionaire/' },
    ],
  },
];
