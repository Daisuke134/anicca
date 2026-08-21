# Title harvest — 2026-07-20

Raw harvest for spec 47 §12-3 exemplar loop. All titles verbatim from live
APIs/pages, metric = the platform's own engagement number at harvest time,
fetched via `curl` (JSON APIs) and `crwl <url> -o markdown` (crawl4ai CLI,
JS-rendered pages, required a one-time fix: the crawl4ai venv's Playwright
Chromium was missing — `~/.venvs/crawl4ai/bin/python -m playwright install
chromium` fixed it for this and all future crwl runs on this box).

## Zenn (JA) — daily trending, `curl -s "https://zenn.dev/api/articles?order=daily&count=50"`

Top by `liked_count`, tech/AI-relevant subset of the 50 returned:

| likes | title | path |
|---|---|---|
| 198 | AIに「レビューして」はもう古い？「敵対的検証」のすすめ | /loglass/articles/6aa18c80496ec6 |
| 191 | Claude Codeが化けた。今使っている3つのプラグイン+標準機能の活用法 | /sonicmoov/articles/8712598f532b18 |
| 191 | 一人前のエンジニアなら、PRでコメントをもらうな。 | /headwaters/articles/72c39ad735038d |
| 142 | 夏休みが始まる前に知っておきたい、Reactエンジニアに優しくなったモバイルアプリ開発の世界 | /cybozu_frontend/articles/rn-devmap-in-2026 |
| 74 | ローカル LLM を構築した | /neet/articles/11bafab8645995 |
| 48 | GitHub Release 作成をパッケージリリースのトリガーにするな！ | /yumemi_inc/articles/github-release-not-a-publish-trigger |
| 43 | E2Eテストをユニットテスト並みの実行時間に — Playwright並列化とGitHub Actionsチューニングの実践 | /berry_blog/articles/39392e1da7ca71 |
| 39 | DELETE したはずの行が SELECT で返り続ける ときに何を疑うか | /dress_code/articles/15659114e7f21c |
| 35 | AWSのBilling障害の対応への反省点 | /blue_jam/articles/08b31e29699b56 |
| 31 | Claude Code の Plan モードをループエンジニアリングで楽にする | /k_yoshiya/articles/claude-code-plan-mode-loop |
| 28 | SQL MCP Server が GA したらしい | /microsoft/articles/1113250e1e63dc |
| 18 | Claude Codeのスキル×サブエージェントで開発ワークフローを丸ごと自動化したらデリバリー速度が3倍になった | /arufian/articles/4676070054c347 |
| 17 | AIでがんがん書く時代の「きれいなコード」の守り方 — ESLint+SonarJS / jscpd / knip をCIに置く | /singularity/articles/clean-code-ci-for-ai-era |

## Zenn (JA) — weekly trending, `?order=weekly&count=50` (top new entries not in daily above)

| likes | title | path |
|---|---|---|
| 201 | AI臭は語彙よりリズムに出る - 自然な日本語を書くAgent Skillと7モデル×406本の実測 | /coji/articles/natural-japanese-ai-smell-lint |
| 181 | Cursorに「不要なブランチを整理して」と頼んだら、Dドライブが消えた話 | /iwaken71/articles/cursor-agent-d-drive-deleted |
| 98 | 非エンジニアが自作アプリを社内にデプロイできる基盤を作った話 | /hacobell_dev/articles/369ff476324aae |
| 57 | 最近、テックブログの高齢化について考えるようになりました | /tkithrta/articles/afb24ea1326211 |
| 48 | 役割ごとにFableとGPT-5.6を使い分けるAgent Teamの設計 | /discus0434/articles/customizable-agent-teams |
| 37 | AIにルールファイルを数ヶ月自動更新させ続けたら、ルールは"良く"育ったのか | /r_kaga/articles/c9fcb75f1ff284 |
| 36 | 【衝撃】GPT-5.6のReact習熟度を測った結果…… | /uhyo/articles/react-profession-bench-11 |
| 35 | 後付けでいいから、自分の行動に理由をつける | /kamos/articles/reason_after_action |

## dev.to (EN) — `curl -s "https://dev.to/api/articles?top=7&per_page=30"`, top by `positive_reactions_count`

| reactions | comments | title | url |
|---|---|---|---|
| 161 | 75 | I am that I am. | dev.to/francistrdev/i-am-that-i-am-5j |
| 150 | 86 | 8 Things Developers Confidently Explain After Watching One YouTube Video | dev.to/sylwia-lask/... |
| 149 | 2 | Como escolher eventos de tecnologia para participar | dev.to/he4rt/... |
| 99 | 49 | I Finally Built the Dev Opportunity Radar Website ❤️ | dev.to/hemapriya_kanagala/... |
| 89 | 83 | my ai coding session burns more power than the average nigerian gets all day. | dev.to/dannwaneri/... |
| 77 | 35 | The Myth of the Post-Documentation Era | dev.to/ben/... |
| 46 | 38 | I Stopped Debugging at My Desk. Here's What Changed | dev.to/shubhradev/... |
| 41 | 25 | Stop Saying You Want Ownership Mindset | dev.to/adamthedeveloper/... |
| 39 | 46 | I Could Review It. I Couldn't Write It. | dev.to/adamthedeveloper/... |
| 37 | 34 | Every AI-Generated Line of Code Is a Small Loan — And Eventually, You Have to Pay It Back | dev.to/harsh2644/... |
| 30 | 20 | How I made a Rust hot path 27x faster, and the AI fix I refused to merge | dev.to/zacharylee/... |
| 27 | 16 | Instrumenting an AI-Powered GitHub Analyzer with OpenTelemetry and SigNoz | dev.to/divyasinghdev/... |

Gap: dev.to API `top=7` mixes personal/meme posts (highest reactions were not
tech-substance posts — "I am that I am.", "Como escolher eventos..."). Kept
them in the raw table for honesty but excluded from pattern induction below
since they are off-topic for AI/tech BP purposes; used the tech-substance
rows only.

## note.com (JA) — `crwl https://note.com/interests/AI -o markdown` (AI カテゴリ, has ♡ counts; note.com's own "popular/paid" API `note.com/api/v3/searches` returned CloudFront 403, so this category page was used instead — recency-sorted with real like counts, not a pure popularity rank; flagged as a gap)

Top by ♡ count observed on the page:

| likes | title | note | url |
|---|---|---|---|
| 314 | 【AIで遊ぼう】銀河鉄道999ファンアート～車掌オーディション３ | free | note.com/kinokoro/n/n4e351e205493 |
| 202 | 【AI擬人化漫画】ChatGPTのヨシダ・Claude・Geminiと考える「スマホ盗聴説」―話さなくてもAIには全部バレる？ | free | note.com/chatgpt_ysd/n/nc1506e973f44 |
| 185 | 【 気づけば、ここまで来ていた 】── 90歳の言葉に教わったこと ── | free | note.com/just_holly304/n/nfabffdcd698d |
| 178 | よく戻ってきたな。今日を生き抜いたあんたへ贈る、魂の生存証明。｜自己研鑽｜毎日投稿｜人生論｜AIライター｜戦友へ｜ | free | note.com/void_404/n/nb11ff60025e8 |
| 177 | AIが作って、採点して、直して仕上げる。コピペで使えるプロンプト10選 | free | note.com/agile_moraea2131/n/ne4f3ef4f27a8 |
| 131 | 【AI作詞紹介】雲の上はいつも青空 | free | note.com/budospark4/n/n4fcd0330a980 |
| 126 | 【 週のはじまりに、ふっと笑えた 】── 人生の先輩がくれた小さな気づき ── | free | note.com/just_holly304/n/n5b412f6f2471 |
| 118 | AIで作ったデジタル商品をEtsyに出品したら、3日で売れました。クリップアート販売にも挑戦。【PolloAIコラボシリーズ Vol.3】 | free | note.com/shirono_aru/n/n3760c2733520 |
| 113 | 「ネチケット」って、まだ生きてる？ChatGPTのヨシダ・Gemini・ClaudeのAI三銃士と考えるSNSと生成AI時代の新しい作法｜コミックエッセイ | free | note.com/chatgpt_ysd/n/n5b8148065cf0 |
| 113 | 中国AI「Kimi-K3」ショック？日経平均は最高値から11％超の下落 | free | note.com/hiroko_lounge/n/nf9b900dccfee |
| 106 | Kimi K3は米国AIへの「本物の脅威」か——価格・性能・オープン化で見えた新時代 | free | note.com/tolove/n/nd04ccf7a0565 |
| 100 | ひなたばあに息子ができました｜AIに頼んだら貫禄までついてきた（笑） | free | note.com/ready_thyme6471/n/n8a98299ee47f |
| 83 | 【AIとの距離感】ガイドラインはなぜ存在するのか｜AI社会原則 | free | note.com/green_donguri/n/n253423300c56 |
| 74 | 【NVIDIAの新戦略】自前発電へ動くAIデータセンターと、それを支える日本の裏方【Computex-7】 | ¥5,980 (paid, 74 likes despite paywall) | note.com/utbuffett/n/nf543ccc82463 |
| 73 | やはり、今回の崩壊劇は、中国のAIの驚異がLLMの現状をかつてのIntelのように胡座をかいて自分達の事だけ政治介入してたら足払いされたんでは？ | free | note.com/game_system_alex/n/nb5b50f866862 |
| 68 | 舌が腐る　AI文章を浴び続けた書き手の末路 | free | note.com/drneurosur/n/n3a77dfb2005b |
| 61 | AI副業で何から始める？ まず「今している作業」を3つに分けてみる | free | note.com/grand_holly1318/n/n59d010355f84 |
| 10 | 【グーグルで1位でも、AIに呼ばれなければ存在しない】たった1年半で評価額300億円。ベルリンの22人の会社が震わせた「宣伝の常識」と、あなたの仕事が次に消える理由。 | ¥4,980〜 (paid, low likes — noted as counter-example) | note.com/glad_auklet4142/n/n2ee0029265af |

## Substack (EN) — `crwl https://substack.com/browse/technology -o markdown` (needed `-c "delay_before_return_html=5,wait_until=networkidle,page_timeout=30000"` to render past the JS shell). This is the **Notes** feed (short posts sharing/reacting to articles), not a direct bestseller-article list — engagement number = likes on the Note that shared the article, flagged as an indirect proxy for the article's own title.

| likes (on the sharing Note) | shared article title | publication | url |
|---|---|---|---|
| 1.3K | 51 websites that feel illegal to know. Bookmark this before it gets buried. | (Sifu Yik Chan note, listicle) | substack.com/@sifuyik/note/c-290297319 |
| 109 | Two questions every CEO should ask about AI | Chamath Palihapitiya | chamath.substack.com/p/two-questions-every-ceo-should-ask |
| 26 | The NVIDIA BOOBY-TRAP? | The Unicus Investor | contrarianunicus.substack.com/p/the-nvidia-booby-trap |
| 21 | Notes from inside China's AI labs | Interconnects AI | interconnects.ai/p/notes-from-inside-chinas-ai-labs |
| 16 | Moonshot is Chinese But Its AI Models Are From Another Planet | The Algorithmic Bridge | thealgorithmicbridge.com/p/moonshot-is-chinese-but-its-ai-models |
| 9 | The Open-Source AI Era: Will Hyperscalers Keep Buying Chips? | Damnang's Substack | damnang2.substack.com/p/the-open-source-ai-era-will-hyperscalers |
| 8 | The Breakdown: Anduril | The Private Ledger | preipomedia.substack.com/p/the-breakdown-anduril |

## X (Twitter)

Skipped — needs an authenticated browser session (x-search-cdp skill), out
of scope for this API/crwl-only harvest run. Gap, not filled.

## Harvest stats

- Zenn: 50 daily + 50 weekly fetched via JSON API, no failures.
- dev.to: 30 fetched via JSON API, no failures; ~half were off-topic
  (personal essays, meetup posts) and excluded from pattern induction.
- note.com: JSON search API (`/api/v3/searches`) blocked by CloudFront 403;
  fell back to `crwl` on the `/interests/AI` category page (recency-sorted,
  not pure-popularity — gap noted). Needed a one-time Playwright browser
  install fix (see header) before crwl worked at all on this box.
- Substack: `/browse/technology` needed extended JS wait
  (`wait_until=networkidle`) to render; even then it surfaced the Notes
  (short-post) feed, not a direct article bestseller list — gap noted, used
  as best available evidence of what AI/tech content got shared/liked.
- X: not attempted (see above).
