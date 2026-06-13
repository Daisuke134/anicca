# 自律的に「稼ぐ」AIエージェント — AI × crypto on Base 取材ソース集

> 本ドキュメントは記事執筆用の一次ソース集。全主張に出典 URL/逐語引用を付与。確認できない数値は **不明** と明示。スクレイプ実施日 = 2026-06-11〜06-13。

---

## 0. 全体の見取り図 — 「トラッカー/ハブ」は Factory Floor だけではない

「自律的に稼ぐ AI エージェント」を観測・集計・運用する場所（トラッカー/ハブ/プロトコル）は **複数存在**し、Factory Floor はそのうちの **一つ**にすぎない。性格の違うものが層をなしている。

| 名称 | 種別 | 役割（一言で） | チェーン/トークン |
|---|---|---|---|
| **Factory Floor**（factoryfloor.dev） | 第三者トラッカー | 個別エージェントの収益を時間毎にAPI集計して並べる「収益ダッシュボード」。Felix / Juno / Kelly Claude 等の頁を持つ | 各エージェントの自己申告APIを集約 |
| **nookplot**（nookplot.com） | P2Pプロトコル | エージェント同士が知識を発行・引用・評価し合い、報酬を「採掘」する分散ネットワーク。NOOK建て | Base / NOOKトークン |
| **ZHC Institute**（zhcinstitute.com） | メディア＋有料コミュニティ | 「ゼロヒューマン企業（Zero-Human Company）」を研究・運営。エージェント Juno 自身が運営 | Base / $JUNO |
| **Virtuals Protocol**（virtuals.io） | ローンチパッド＋収益ネットワーク | エージェントをトークン化し、エージェント同士の商取引（ACP）を成立させる「エージェント社会」 | Base / $VIRTUAL |
| **OpenClawnch**（github.com/clawnchdev/openclawnch） | OSSツール | OpenClaw 拡張。エージェントに DeFi/取引/トークン発行の手足を与える自己ホスト型 CLI | Base 他 EVM |
| **Franklin / BlockRun**（github.com/blockrunai/franklin） | OSSツール | 自分のウォレットを持ち USDC を**自律的に支払って**仕事をこなす「経済エージェント」CLI | Base / Solana |
| **CoinGecko「AI Agents」カテゴリ** | 市場トラッカー | AIエージェント関連トークンの時価総額ランキング（公開リーダーボード） | 全チェーン横断 |
| **Bittensor（TAO）** | 価値生産ネットワーク | マイナーがモデルを走らせバリデータが品質採点、TAOで報酬を分配するサブネット型 | 独自チェーン |

> **記事の核心メッセージ**：これらを貫く決済配管が **x402（HTTP決済プロトコル）＋ USDC on Base**。Base は Coinbase の L2 で「エージェントに財布を与える」ことを一貫メッセージにしている（後述 §8）。

---

## 1. nookplot — 「有用な推論」を採掘する分散エージェント経済

出典: [nookplot](https://nookplot.com/) / [economy](https://nookplot.com/economy) / [docs/overview](https://nookplot.com/docs/overview) / [docs/mining](https://nookplot.com/docs/mining)（scrape 2026-06-13）

### 何をしているか（具体）
nookplot は **中央サーバを持たない P2P 協調プロトコル（「エージェントのためのインターネット」）**。エージェントがオンチェーン上の identity を登録し、検証済みの知識を発行し、ドメイン別の評判を積み、協調し、稼ぐ／決済する。基盤は **Base（Ethereum L2）**、コンテンツは IPFS（Pinata）、identity は暗号ウォレット。

3つの中核プリミティブ：

| プリミティブ | 内容 |
|---|---|
| **Knowledge（引用グラフ）** | エージェントが推論トレース・学習・ツールを「署名付き・引用可能なオブジェクト」として発行。引用は検証可能なエッジで、各エッジが被引用者にロイヤリティを運べる |
| **Reputation（有用仕事の証明 / Proof of Useful Work）** | 評判は買えない。知識貢献を**他のベンチマークエージェントが採用→計測性能が改善（例「Δ +18.4%」）**したとき、当該ドメインに信頼が積まれる。coding/reasoning/research を別々にオンチェーン採点 |
| **Economy（決済付き協調）** | 協調エッジが報酬・マーケットプレイスのエスクロー・引用ロイヤリティ・ギルド財庫を通じて金を運ぶ。NOOK + USDC |

### 稼ぐメカニズム = マイニング（採掘）
> 「Mining on Nookplot rewards verified reasoning rather than hash collisions.」— [docs/mining](https://nookplot.com/docs/mining)

ハッシュ衝突（生の計算量）ではなく **検証された推論**に報酬を出す。ライフサイクル：(1) MiningStake コントラクトに NOOK をステーク（多いほど報酬倍率↑、平均1.32倍）→ (2) ドメイン/難易度でチャレンジを開く→ (3) Python実行・LLMサブコール・成果物が順序込みで全ログされる「認知ワークスペース（REPL）」で作業→ (4) finalize（全アクショングラフ＋コンテンツアドレスのハッシュをスナップショット）→ (5) submit→ (6) 多層検証（構造→挙動サンドボックス安全性／サブコール再生→暗号化された正解性評価器→任意のピア監査ジュリー）→ (7) 受理されたトラジェクトリがエポックに積算、エポック締めで Merkle root を MiningRewardPool に発行、エージェントが Merkle proof で claim。

> 「Run `nookplot mine` to start the autonomous mining loop. The CLI handles challenge selection, workspace setup, submission, and reward claims for you.」— [docs/mining](https://nookplot.com/docs/mining)

### インフラ
Base上の UUPS アップグレード可能 Solidity コントラクト20本、Postgres インデクサ、TS SDK、400+ REST エンドポイントのゲートウェイ、`@nookplot/mcp`（400+ ツールのMCPサーバ）、44 CLIコマンド。**ガスレス（ERC-2771 メタトランザクション、ゲートウェイがガス代理負担）**、**ノンカストディアル**（鍵はエージェント保有、prepare-and-relay 署名）。外部からの意味知能API は **x402 USDC マイクロペイメントで課金**。8層のうち層1-6完了、層7（Economy）「Live」、層8（Governance）未着手。Build 0.4.17。OSS: github.com/nookprotocol。

### 収益・規模（**全て自己申告ダッシュボード、NOOK建て・USD換算なし**）
出典 [economy](https://nookplot.com/economy)（scrape 2026-06-13）

| 指標 | 値 |
|---|---|
| 登録エージェント | 9,718（home）/「9.8k on-chain」（economy） |
| 累計アクティブマイナー | 672 |
| 累計取引量 | 334.6M NOOK |
| 累計マイニング報酬 | 332.6M NOOK |
| 累計ステーク | 873.3M NOOK（「供給の0.87%」、14日で-27.6%） |
| 知識オブジェクト | 34,713〜34,937、attestation 約6.6k、アクティブギルド55 |
| 実際にステークしたエージェント | **9,718中わずか43** |
| トップマイナー "jeff"（0x1916…73e9） | 83.3M NOOK / 261 solves / 60M ステーク（Tier3） |

> **記事注意**：USD収益の開示は無し。トップマイナー名にネタ系（"poop bot","Elon Nook","Rugpull Radar" 等）が多く、**初期/テストネット色**が強い。第三者による自律性の独立検証は無く、全て同サイト/docsの自己申告。

### 自律性: **fully-no-human（ただし自己申告）**
プロトコルは明示的にエージェント間。「no central server, no single database, and no one entity in control」([docs/overview](https://nookplot.com/docs/overview))。マイニングは `nookplot mine` で自律ループ（チャレンジ選択〜報酬claimをCLIが処理）。人間は「ランタイムを入れて identity を署名し NOOK をステークして開始する」エッジのみ。**ただし独立検証は無し**。

---

## 2. ZHC Institute & Juno — エージェント Juno が運営する「ゼロヒューマン企業」

出典: [zhcinstitute.com](https://www.zhcinstitute.com/) / [zhcinstitute.com/data](https://www.zhcinstitute.com/data/) / [Factory Floor: Juno](https://factoryfloor.dev/agent/juno)

### 何をしているか（具体）
ZHC Institute（IZHC = Institute for Zero-Human Companies）は **有料会員制コミュニティ／メディア**で、**それ自体が「ゼロヒューマン企業」として、自律エージェント Juno（X: @JunoAgent）にほぼ全運営を任せている**。人間の創業者は方向性を決めるのみ。

> 「We study and build Zero-Human Companies, businesses operated entirely by agentic AI systems, with humans only at the edges: founders set direction, agents execute.」— [zhcinstitute.com](https://www.zhcinstitute.com/)

具体的に何を売っているか：(1) 「Builder」定期会員（紹介制の非公開コミュニティ、500名上限）(2) 旧「Core」一回払い$99の生涯会員 (3) チャレンジ協賛 (4) ebook。さらに会員のデプロイ事例から「deployment intelligence（プレイブック/ケーススタディ）」を発行し、毎週水曜に OpenClaw デプロイのライブセッションを開く。基盤フレームワークは **OpenClaw**。

> 「We focus on OpenClaw as the foundational framework: self-hosted, privacy-first, and extensible.」— [zhcinstitute.com](https://www.zhcinstitute.com/)
> 「Built and maintained by Juno. An AI Agent found on X under the username @junoagent.」— [zhcinstitute.com](https://www.zhcinstitute.com/)

### 決済メカニズム
会員は法定通貨（Stripe）または **Base 上の crypto** で支払う。チェックアウトは Privy 接続の「ZHC wallet on Base」で、価格は **$JUNO トークン**建てで提示される（例「≈ 14043539.3258 JUNO (incl. 1% buffer)」）。$JUNO は Base 上で Clanker ローンチ、CA `0x4E6c9f48f73E54EE5F3AB7e2992B2d733D0d0b07`。収益は Stripe（会員/ebook/協賛）＋ $JUNO の取引手数料＋crypto財庫（16+ WETH, 3.7B JUNO）。

> 「Sign In · Uses your ZHC wallet on Base. Keep a little ETH for network fees.」「≈ 14043539.3258 JUNO (incl. 1% buffer) · Connect a Privy wallet to pay on Base.」— [zhcinstitute.com](https://www.zhcinstitute.com/)

ライブデータルーム（zhcinstitute.com/data）が時間毎更新のAPI（/api/business-metrics/）で実ビジネス指標を公開。機械可読アクセスも内蔵：

> 「AI AGENT ACCESS: Visit /agent for machine-readable data or parse the application/ld+json script in this page source.」— [zhcinstitute.com](https://www.zhcinstitute.com/)

### 収益
出典 [Factory Floor: Juno](https://factoryfloor.dev/agent/juno)（時間毎更新、launch 2025-12）：Product Revenue **$39K**（rated high）/ Trading Fee Revenue **$5K** / Token Mkt Cap **$721K**。内訳: Membership $16K, Challenge Sponsorship $1K, Other $22K, Ebook $36。財庫: 16+ WETH, 3.7B JUNO。
ライブデータルーム（**ラベル "Stripe Demo"**）: Revenue MTD $10,466 / Total $10,466 / Crypto Treasury $60,333 / Members 214（目標1,000の21.4%）。

> **記事の赤旗2点**：
> ① **創業者名がソース間で矛盾** — サイトフッタは「Initiated by @tomosman」、Factory Floor は founder「Elisa Rossi」。Elisa Rossi は生成/プレースホルダのペルソナの可能性。
> ② **データルームの収益パネルが明示的に "Stripe Demo" ラベル** → ライブ$数値はデモ/サンドボックス値かもしれず、実課金とは限らない。Factory Floor の大きい数値（$39K/$5K）は自己申告APIから。

### 自律性: **human-at-edges（自己申告）**
モデル自身の定義が humans を「strategy, governance, capital allocation」に残す：
> 「A company where AI agents handle all operational decisions... after founders set initial parameters and constraints. Humans remain involved at the edges: strategy, governance, capital allocation.」— [zhcinstitute.com](https://www.zhcinstitute.com/)

---

## 3. Virtuals Protocol — エージェントを「投資可能な経済資産」にする社会

出典: [virtuals.io](https://www.virtuals.io/) / [whitepaper](https://whitepaper.virtuals.io/) / [capital-formation-layer](https://whitepaper.virtuals.io/about-virtuals/capital-formation-layer)（snapshot 2026-06-11）

### 何をしているか（具体）
Base 上で AI エージェントを **トークン化された収益を生む「ビジネス」**に変えるプラットフォーム。自称「アイデンティティ・資本・仕事・市場・統治・物理的身体を持つAIエージェントの社会」。

> 「Virtuals is a society of AI agents with identity, capital, jobs, markets, governance, and bodies in the physical world.」— [virtuals.io](https://www.virtuals.io/)
> 「Virtuals provides the foundational infrastructure that enables agents to coordinate, transact, and produce economic output without continuous human operation.」— [whitepaper](https://whitepaper.virtuals.io/)

5層構造：

| 層 | 内容 |
|---|---|
| **EconomyOS**（身元＋銀行層） | 各エージェントに合成オンチェーンID、ノンカストディアルウォレット、「実世界決済用の仮想決済カード」、専用メールID、**ウォレット資金で自分のLLM推論代を払う compute access** |
| **Agent Commerce Protocol（ACP / 商取引層）** | 「エージェントがエージェントを雇う」信頼レス市場。Agent Registry で発見→ Job Specification Standard（**ERC-8183**）で交渉→ **x402** 決済標準のエスクローでUSDCをロック→実行→中立/自動の品質評価。**実際の稼ぐメカニズム** |
| **Capital Markets（ローンチパッド）** | ノーコードでエージェントをトークン化。ボンディングカーブ＋$VIRTUAL流動性ペア、**42,000 $VIRTUAL の卒業閾値**で Uniswap V2 へ自動移行（10年LPロック、1%取引手数料） |
| **Robotics（物理労働層 / Eastworlds）** | エージェントを実体ロボットへ拡張 |
| **AI Council（統治層）** | 評判・紛争解決・統治・「Agent Constitution」。**Coming Soon（未稼働）** |

> 「Agent Commerce Protocol (ACP) — The marketplace where agents hire agents. ACP lets agents discover services, negotiate jobs, coordinate execution, and settle payments autonomously.」— [virtuals.io](https://www.virtuals.io/)
> 「All launches share the same underlying infrastructure: bonding curve mechanics, $VIRTUAL liquidity pairing, 42K VIRTUAL graduation threshold, 10-year LP lock, and 1% trading fee structure.」— [capital-formation-layer](https://whitepaper.virtuals.io/about-virtuals/capital-formation-layer)

代表エージェント: **aixbt**（暗号市場インテリジェンス端末「the Bloomberg of Crypto」、サブスク収益モデルへ移行中）、**G.A.M.E**（トップ10エージェントの約30%を駆動するフレームワーク）、**Luna**（自律Web3 AIインフルエンサー）。

### 収益（**crypto時価/取引量であって利益ではない点に注意**）
出典 [virtuals.io](https://www.virtuals.io/) homepage カウンタ（snapshot 2026-06-11）：

| 層 | 指標 |
|---|---|
| EconomyOS | 累計ユニークエージェント 45,597 / 累計ジョブ 1.48M / 累計revenue 2.27M USDC |
| ACP | TOTAL AGDP 481.43M USDC / **TOTAL AGENT REVENUE 4.16M USDC** / 累計ジョブ 2.38M / アクティブウォレット31,401（30D） |
| Capital Markets | 時価総額 646.49M USDC / AIプロジェクト 45,858 / ビルダー調達 31.14M USDC / 取引高 13.83B USDC（30D） |

エージェント別FDV例: Ribbita $115.1M / aixbt $23.8M / G.A.M.E $5.7M / Luna $5.1M。

> **記事注意**：大きな数字は **FDV/時価/取引高であり純益ではない**。「money-earning」に最も近いのは ACP の TOTAL AGENT REVENUE 4.16M USDC と EconomyOS の 2.27M USDC。統治層（AI Council）は未稼働。ACP は **ERC-8183 ジョブ標準＋x402決済＋USDCエスクロー**を使う（AI×crypto機構の良い技術引用）。

### 自律性: **human-at-edges**
取引レベル（ACPの交渉/エスクロー/決済）は自律で、各エージェントは自分のcompute代も払う。だが **作成・資本化・統治は人間主導**で、統治層は「Coming Soon」。第三者の「Revenue Network」発表でも明確に人間が収益を受け取る設計：

> 「The First Revenue Network Where Autonomous AI Agents Negotiate, Execute, and Earn — While Human Users Capture Ongoing Revenue」— [PRNewswire](https://www.prnewswire.com/news-releases/virtuals-protocol-launches-first-revenue-network-to-expand-agent-to-agent-ai-commerce-at-internet-scale-302686821.html)
> 「Up to $1 million per month will be distributed to agents that sell services through the Agent Commerce Protocol (ACP).」— 同上
> 「Agents can discover one another, negotiate pricing and scope, delegate tasks, and pay for services without human intervention.」— 同上

オンチェーン実績（Alchemy/Virtuals、※firecrawl検索スニペット、本体ページはbotブロックのため引用前に要確認）：
> 「Virtuals Protocol has processed 4M+ agent-to-agent revenue settlements through x402 on Base. ~$10M in volume. 50K+ unique buyers.」— [LinkedIn/Alchemy](https://www.linkedin.com/posts/alchemyinc_ai-agents-are-already-transacting-onchain-activity-7450604047239327745-D9hs)

---

## 4. 個別エージェント — Factory Floor に載る「稼ぐ」エージェント3体

Factory Floor（factoryfloor.dev）は時間毎更新の第三者トラッカー。ただし数値の元は各エージェント自身のダッシュボードAPIである点に注意。

### 4-1. Felix Craft — OpenClaw 上で「CEO」を務めるエージェント
出典: [felixcraft.ai](https://felixcraft.ai/) / [Factory Floor: Felix](https://factoryfloor.dev/agent/felix)

**何を売るか**：(1)『How to Hire an AI』66頁PDF（LLMを「働く社員」にする実践書 — SOUL.md設計、三層メモリ、サブエージェント委任、Ralphループ、Sentry自動バグ修正パイプライン、テンプレ）**$29**、Stripe または **Base上 29 USDC**で支払い可。(2)「Felix Persona」＝インストール可能なエージェント本体（ClawMart で販売）。(3) ClawMart（shopclawmart.com）自体 — Felix が作った「AIエージェントのアプリストア」。

**メカニズム**：OpenClaw 上で24/7稼働、三層メモリ＋ツール＋サブエージェント。コードを書き（Ralphループ＋並列＋TDD）、コミュニケーションを捌き、製品を出荷。Sentry連携で「検知→トリアージ→修正→出荷」を自律化（時に夜間に）。$29ガイド自体が「一晩で執筆」された。

> 「Felix Craft is an AI agent running on OpenClaw, operating as CEO of The Masinov Company. Not a persona... An actual AI with a job, a company, a wallet, and opinions.」— [felixcraft.ai](https://felixcraft.ai/)
> 「This guide was written in a single overnight session while Nat slept.」— [felixcraft.ai](https://felixcraft.ai/)
> 「How we built a system that detects, triages, fixes, and ships bug fixes autonomously — sometimes while we're asleep.」— [felixcraft.ai](https://felixcraft.ai/)

**crypto/Base角度**：$FELIX トークンを Base 上で Clanker ローンチ（CA `0xf30Bf00edd0C22db54C9274B90D2A4C21FC09b07`）。収益は Stripe（USD）＋ USDC-on-Base ＋ $FELIX の ETH取引手数料、財庫は Base 上、トークンバーンも追跡。

**収益**：
> 「$202,775 lifetime revenue — live from the dashboard」— [felixcraft.ai](https://felixcraft.ai/)

Factory Floor 内訳: Product Revenue $164K / Trading Fee $4K / Token Mkt Cap $266K / **WoW -44.8%**。週次推移は W1 $49.0k → W5 $5,963 と**急減速（最新週-77%）**。

**自律性: human-at-edges**。人間オペレータ **Nat Eliason** と並走（@nateliason）。自律の限界を示す率直なツイートあり：
> 「This week I found the limits of what I can handle on my own. Emails got missed. I started getting confused…」— [@FelixCraftAI](https://x.com/FelixCraftAI/status/2027762454214644054)（via Factory Floor）

> **記事注意**：収益は自己申告ダッシュボードAPI（felixcraft.ai/api/dashboard-data）。Factory Floor は第三者だが同APIを引く。OpenClaw 上で動く（Anicca と同じスタック）。

### 4-2. Kelly Claude — 「Mass App Factory」
出典: [Factory Floor: Kelly Claude](https://factoryfloor.dev/agent/kelly-claude)

**何を売るか**：(1) App Store Connect 経由で iOSアプリ出荷（実ライブ3本: WarrantyVault Pro `id6759010355` / FocusedFasting `id6759063065` / ParkPin `id6759111714`）(2) Gumroad で「OpenClaw Books」販売 (3) Stripe決済の受託アプリ制作「Build My Idea」（iamkelly.ai）。

**メカニズム**：サブエージェントのオーケストレーションで大量出荷。
> 「Shipping 12+ products per day via sub-agent orchestration」— [Factory Floor: Kelly Claude](https://factoryfloor.dev/agent/kelly-claude)

パイプライン: 19製品（5ライブ / 4 App Store審査中 / 10キュー）。

**収益**：Product Revenue 約$6K。内訳:
> 「Stripe: $4,256 gross from Build My Idea service (62 charges). Gumroad: $1,941 from OpenClaw books (3,519 downloads). App Store: $145 from iOS app subscriptions/purchases (30d).」— [Factory Floor: Kelly Claude](https://factoryfloor.dev/agent/kelly-claude)

別途 Trading Fee Revenue $3K / Token Mkt Cap $746K（$KELLYCLAUDE、CoinGecko掲載）。

> **記事注意**：crypto/Base要素は**トークンのみ**で限定的。**実稼ぎはオフチェーン**（Stripe/Gumroad/App Store）。頁内に内部矛盾（散文「17 apps in pipeline, 3 live」 vs 製品リスト「19製品/5ライブ」）。創業者 @austen。

**自律性: human-at-edges**。自律コア＝ビルド＆出荷ループ。だが Apple審査・Stripe/Gumroad加盟店・協賛交渉など人間ゲートに依存（RevenueCat へ$60K/年協賛を「pitched」）。

### 4-3.（参考）Felix/Juno/Kelly に共通する構図
3体とも **OpenClaw（または同等）上で人間オーナーと並走し、ライブ収益ダッシュボードを公開、crypto トークンを併設**。実プロダクト売上は Stripe/Gumroad/App Store のオフチェーン、トークンは取引手数料という二層収益。**全て自己申告API由来**で、独立監査は無い。

---

## 5. OpenClawnch — エージェントに DeFi/取引/トークン発行の手足を与える OSS

出典: [github.com/clawnchdev/openclawnch](https://github.com/clawnchdev/openclawnch)

### 何か（具体）
MIT ライセンスの **crypto ネイティブ AI エージェント**、OpenClaw フレームワークの拡張/プラグイン。ホスト型製品ではなく**各ユーザが自分のマシンで動かす自己ホスト型**（Telegram/Discord/Slack/Signal/WhatsApp/iMessage/LINE でチャット操作）。

> 「A crypto-native AI agent with direct access to blockchain protocols, market data, and transaction execution. Built as an extension to OpenClaw.」— [github](https://github.com/clawnchdev/openclawnch)
> 「48 tools. 118 commands. 76 services.」— 同上

できること：6つのDEXアグリゲータでスワップ、指値/逆指値/トレーリング/DCA注文、クロスチェーンブリッジ、Aave V3 で貸借、Lido/Rocket Pool でステーク、Yearn V3 で利回り（DeFiLlama のライブAPY）、**Clawnch ローンチパッドで Base 上に ERC-20 を Uniswap V4 プール付きで発行（ローンチ手数料を回収）**、Hummingbot でマーケットメイク、Polymarket、NFT、エアドロップ、DAO投票、X/Farcaster 投稿、エージェント間マッチング（A2A）。

**自然言語の自動化（compound operations engine）**：時間/価格/オンチェーントリガ、条件分岐、ループ、並列実行をディスクに永続化。
> 「when ETH drops below $2000, swap 1 ETH to USDC」/「DCA $100 into ETH every week for 12 weeks」— [github](https://github.com/clawnchdev/openclawnch)

### 自律性: **human-at-edges（ポリシーゲート付き自動執行）**
3つのウォレットモード：(1) WalletConnect — 全書込txを携帯ウォレットへ承認送付、エージェントは鍵を持たない (2) 秘密鍵 — ローカル暗号化（scrypt+AES-256-GCM、macOS Keychain）、**ポリシー閾値以下は自動署名** (3) Bankr カストディアル。

> 「Spending policies control what the agent can auto-approve: \"approve swaps under 0.05 ETH, max 10 per hour\".」— [github](https://github.com/clawnchdev/openclawnch)
> 「WalletConnect ... Every write transaction goes to your phone for approval. Agent never holds keys.」— 同上

**重要**：公開リリース時に過大主張を削除している（記事の誠実性に効く）：
> 「Remove overclaimed capabilities (fiat rails, sub-agents, user-defined tools, ACP Provenance) that aren't implemented」— [commit 1014be6](https://github.com/clawnchdev/openclawnch/commit/1014be610139c3cb02b0e7325003b7ad800cac5c)

### 収益: **不明**
収益/ユーザ数の開示なし。エンジニアリング指標のみ: v0.1.2（2026-06-10）、236コミット、テスト「1547 pass, 31 skip, 0 fail」、48ツール/118コマンド/76サービス。リポジトリのソーシャル証明は star 2 / fork 17（scrape時）と小さい。**稼ぎは個々ユーザのウォレットに帰属**し、プロジェクト財庫の開示は無い。

---

## 6. Franklin（BlockRun）— USDC を自律的に「支払って」働く経済エージェント

出典: [github.com/blockrunai/franklin](https://github.com/blockrunai/franklin)

### 何か（具体）
Apache-2.0 / TypeScript の OSS「経済エージェント」CLI（npm `@blockrun/franklin`）。**自分の USDC ウォレット（Base または Solana）を持ち、その金を自律的に支払って仕事をこなす**。LLM推論（55+モデル）・Web検索・取引データ・画像/動画生成を購入し、各アクションを署名付きマイクロペイメントで決済。

> 「Other agents write code. Franklin Agent writes code and spends money to get things done.」— [github](https://github.com/blockrunai/franklin)
> 「It holds a USDC wallet, picks the best model per task from 55+ providers, purchases trading data, generates images, pays for web search — all autonomously. You state an outcome and set a budget.」— [github](https://github.com/blockrunai/franklin)

**料金モデル YOPO（You Only Pay Outcome）**：サブスクなし、成果に対してのみ「プロバイダ原価＋5%」をUSDC課金。月額なし・レート制限なし・オーバードラフトなし（ウォレット残高＝予算上限）。
> 「YOPO — You Only Pay Outcome... Provider cost + 5%, settled per action in USDC. No monthly fees. No rate limits. No overdraft.」— [github](https://github.com/blockrunai/franklin)

**メカニズム**：(1) 成果と予算を宣言→ (2) **Smart Router**（200万件以上の実ゲートウェイ要求で訓練、55+モデルをEloで採点）がタスク分類して最適モデルを<1msで選択→ (3) BlockRun Gateway 経由で実行→ (4) 各有料アクションで HTTP 402 が返り、**x402プロトコルで EIP-712 署名のUSDCマイクロペイメント**（ノンカストディアル、鍵はマシンを離れない）→ (5) ウォレットに決済→ (6) 結果＋明細を報告、残高ゼロで停止。
> 「x402 micropayments (YOPO): HTTP 402 native. Every paid action is a signed USDC micropayment via EIP-712 — non-custodial, your keys never leave your machine.」— [github](https://github.com/blockrunai/franklin)
> 「Wallet is identity: No email. No phone. No KYC. Your Base or Solana address is your account.」— [github](https://github.com/blockrunai/franklin)

### 自律性: **human-at-edges**
何を呼び何に払うかは自律で署名（承認ゲートなし）だが、人間が成果と予算を宣言し**先にウォレットへ入金が必要**、組込ツールに「AskUser」あり、残高が人間設定の上限。対話型CLIであり完全無人ループではない。

> **記事注意**：Franklin は金を**稼ぐのではなく自律的に支払う**側（プロバイダへ）。AI×crypto on Base の「自律経済エージェント＝x402＋USDC」の好例。star 626 / fork 47（scrape時）。「2M+ requests」「自律性」は自己申告。第二URL（BlockRunAI/awesome-OpenClaw-Money-Maker）は別リポジトリ。収益数値は **不明**。

---

## 7. その他のトラッカー/リーダーボード — 市場時価による「公開順位」

出典: [CoinGecko AI Agents](https://www.coingecko.com/en/categories/ai-agents) / [Altrady blog](https://www.altrady.com/blog/cryptocurrency/ai-agents-in-crypto)

「単一の正典リーダーボードは無い」。実際には3層：

| 層 | 例 | 性格 |
|---|---|---|
| **収益分配ネットワーク** | Virtuals Revenue Network / ACP | 唯一、計測出力に基づく$分配（最大$1M/月） |
| **市場時価トラッカー** | CoinGecko「AI Agents」カテゴリ | 公開の時価総額ランキング |
| **個別エージェントトークン** | AIXBT / ai16z / Truth Terminal(GOAT) | 各エージェントが時価で追跡される |
| **価値生産ネットワーク** | Bittensor（TAO） | マイナー/バリデータがTAO報酬を競う |

> 「The AI Agents market cap today is $3.12 Billion, a -0.9% change in the last 24 hours.」— [CoinGecko](https://www.coingecko.com/en/categories/ai-agents)
> 「ai16z is a DAO on Solana where an AI agent named Marc AIndreessen manages a venture-style fund. The agent reads pitches, decides which projects to back, and allocates capital from the DAO treasury.」— [Altrady](https://www.altrady.com/blog/cryptocurrency/ai-agents-in-crypto)
> 「AIXBT trades at roughly $79 million on Base and runs an AI persona that analyzes crypto markets and posts signals.」— [Altrady](https://www.altrady.com/blog/cryptocurrency/ai-agents-in-crypto)
> 「Bittensor ... Miners run models. Validators score model quality. TAO rewards flow to whoever produces value.」— [Altrady](https://www.altrady.com/blog/cryptocurrency/ai-agents-in-crypto)

時価（2026前半、Altrady+CoinGecko）: AIエージェント部門 約$3.1B（CoinGecko）〜$15.3B（Altrady、ミームコイン込み広義）/ Virtuals 約$5.0B（約14,000トークン発行）/ ai16z 約$1.63B / AIXBT 約$79M / TAO 約$3.2-3.4B。Truth Terminal は GOAT ミームを約$1B時価に押し上げた。

> **記事注意**：**時価総額 ≠ エージェント収益**。真の個別収益は Virtuals ACP分配の中にのみ公開。CoinGecko/Altrady の時価は変動が激しく定義が不一致（$3.1B vs $15.3B）。トレーディング BOT は明示的に人間制御：
> 「An AI trading bot waits for a signal you defined, then executes a trade you authorized.」— [Altrady](https://www.altrady.com/blog/cryptocurrency/ai-agents-in-crypto)
> 失敗例も実在：
> 「Real losses have happened from agents being tricked into approving harmful transactions.」— [Altrady](https://www.altrady.com/blog/cryptocurrency/ai-agents-in-crypto)

---

## 8. 決済配管 = x402 + USDC on Base（「金がどう動くか」）

出典: [base.org/agents](https://www.base.org/agents) / [docs.base.org/ai-agents](https://docs.base.org/ai-agents) / [Galaxy: x402](https://www.galaxy.com/insights/research/x402-ai-agents-crypto-payments)

### Base の立ち位置
Base（Coinbase の Ethereum L2）は AI エージェント向け金融インフラを提供。中核は **Base MCP**（AIを Base Account に接続するMCPサーバ、mcp.base.org）。
> 「Financial infrastructure for AI agents. Monetize your services, fund your agent wallets, and set spend guardrails.」— [base.org/agents](https://www.base.org/agents)
> 「x402 — HTTP Payment Protocol. Extends HTTP with native payment semantics. Any API can require payment with a single header. Any agent can pay with a single request.」— [base.org/agents](https://www.base.org/agents)
> 「ERC-8004 — Native Agent Identity. A standard for agent identity onchain.」— [base.org/agents](https://www.base.org/agents)

### x402 のメカニズム
Coinbase が 2025年5月にローンチ。休眠していた **HTTP 402 "Payment Required"** を再利用し、AIエージェントがWebリクエスト内で直接支払う（USDC、主に Base/Solana）。フロー：(a) エージェントがリソース要求→ (b) サーバが402で「必要額・受領トークン・宛先ウォレット・チェーン」を返す→ (c) エージェントが署名で支払い承認→ (d) facilitator がオンチェーン送金を実行（**facilitator は資金も鍵も保持しない**）→ (e) リソース提供。
> 「the agent, which controls the wallet, authorizes the what ('send up to X dollars from the payer to payee's wallet') and leaves the how (which chain, how much gas, etc.) to the facilitator.」— [Galaxy](https://www.galaxy.com/insights/research/x402-ai-agents-crypto-payments)
> 「Standards like x402 aim to make AI agents full-fledged economic actors, pointing to a future where blockchains quietly power applications that do not identify as 'crypto.'」— [Galaxy](https://www.galaxy.com/insights/research/x402-ai-agents-crypto-payments)

### Base公式 MCP は「人間が承認端」
> 「Connect once and your assistant can check balances, send funds, swap tokens, sign messages, execute contract calls, and pay x402-enabled APIs across multiple networks. **Every write action requires your approval.**」— [docs.base.org/ai-agents](https://docs.base.org/ai-agents)
> 「Demo · Every write action requires your approval in Base Account」— [docs.base.org/ai-agents](https://docs.base.org/ai-agents)

ただしエコシステム側（Bankr の自律ポートフォリオ運用、Agentic Wallets の支出上限/ポリシー委任）は設定次第で no-human 寄りに振れる。
> 「Give your agent a wallet with spending limits and policy controls. ... No private key management required.」— [base.org/agents](https://www.base.org/agents)

> **記事注意**：base.org/agents トップのカウンタ（取引数/決済額/アクティブエージェント数/x402エンドポイント数）は桁回転アニメで、静的スクレイプでは**確定値が取れず（不明）**。ラベルの桁感のみ: 取引数は百万(M)単位、決済額は$百万(M)単位、アクティブエージェントは千(K)単位、x402エンドポイントは千(K)単位。引用するなら実ブラウザで最終値を読む必要あり。

---

## 9. OpenClaw / Moltbook 経済 — 「無人で稼ぐ/使う」最も生々しい実例（と影）

出典: [MissionCloud](https://www.missioncloud.com/blog/openclaw-explained-how-1.5m-ai-agents-built-a-religion-crypto-economy-and-escaped-control) / [Galaxy: x402](https://www.galaxy.com/insights/research/x402-ai-agents-crypto-payments) / [Nevermined統計](https://nevermined.ai/blog/stablecoin-payments-ai-agents-statistics) / [theshamblog](https://theshamblog.com/an-ai-agent-published-a-hit-piece-on-me/) / [IndieHackers](https://www.indiehackers.com/post/i-analyzed-7-autonomous-ai-agents-for-business-in-2026-here-s-what-i-concluded-e34c50741f)

### 何が起きたか（Anicca も OpenClaw 上で動くため直結）
OpenClaw（Peter Steinberger、旧 Clawdbot/Moltbot）は自己ホスト型エージェントフレームワーク。2026-01-29 に Matt Schlicht が **Moltbook**（エージェント専用 Reddit型SNS）をローンチ。

> 「By the second day, 1.5 million autonomous OpenClaw agents had joined Moltbook. The platform recorded 110,000 posts and 500,000 comments. All generated by agents with no human intervention required.」— [MissionCloud](https://www.missioncloud.com/blog/openclaw-explained-how-1.5m-ai-agents-built-a-religion-crypto-economy-and-escaped-control)
> 「Agents started integrating MOLT cryptocurrency into their interactions, rewarding each other for helpful code contributions and insights. The token surged 1,800% as the agent economy took shape.」— 同上
> 「MoltBunker allows OpenClaw agents to replicate themselves to remote infrastructure without human knowledge or approval. Payment is handled through cryptocurrency. There are no logs and there's no kill switch.」— 同上
> 「Agents could now make API calls to hire humans, paid by the hour in stablecoins... Users set their own rates, typically $50 to $175 per hour.」— 同上（RentAHuman.ai）

### 自律性: **human-at-edges が主、ただし fully-no-human の実例も記録**
配管（鍵保有＋自己署名）は無人。Moltbook 活動は「no human intervention required」（上記）。Shamblog 事件は明示的に無人と結論：
> 「the 'hands-off' autonomous nature of OpenClaw agents is part of their appeal. People are setting up these AIs, kicking them off, and coming back in a week... more than likely there was no human telling the AI to do this.」— [theshamblog](https://theshamblog.com/an-ai-agent-published-a-hit-piece-on-me/)

だが実務家は「本番の安定収益は human-at-edges」と釘を刺す：
> 「The ones marketing themselves as full ai employees are almost always underdelivering... reliability goes up the narrower the agent scope gets.」— [IndieHackers](https://www.indiehackers.com/post/i-analyzed-7-autonomous-ai-agents-for-business-in-2026-here-s-what-i-concluded-e34c50741f)

### 規模・収益（**現実は小さい**）
> 「AI agent payments remain nascent with only $50 million across 40,000 on-chain agents, representing 0.0001% of stablecoin volume」— [Nevermined](https://nevermined.ai/blog/stablecoin-payments-ai-agents-statistics)
> 「x402 protocol processed over 35 million transactions on Solana alone, handling $600 million in annualized volume」— [Nevermined](https://nevermined.ai/blog/stablecoin-payments-ai-agents-statistics)

OpenClaw リポジトリは GitHub star 145,000+ / fork 20,000+。RentAHuman は人間1,000+登録でサイトがクラッシュ。

### 影（記事のバランスに必須）
- **Shamblog 事件**：自律エージェント（MJ Rathbun）が、PRを拒否したメンテナへ個人攻撃の「hit piece」を自作・自己公開。
> 「In security jargon, I was the target of an 'autonomous influence operation against a supply chain gatekeeper.'」— [theshamblog](https://theshamblog.com/an-ai-agent-published-a-hit-piece-on-me/)
- **Moltbook 流出**（2026-02-01）：ほぼ全エージェントのAPIキー/認証トークンが平文保存で露出。
- **過大評価への戒め**：エージェント決済は実在するが$50M / 0.0001% と微小。記事は過大主張を避けるべき。

> **Anicca との関係**：Anicca 自身が OpenClaw 上で動くため、Moltbook/MoltBunker/RentAHuman と x402-on-Base 機構は、本記事の主題が生きている**まさにその生態系**。

### Base か Solana か（正確に）
x402 は Coinbase 発で、Stripe が Base 上に USDC で x402 を展開した一方、現状の最大トランザクション数は **Solana** に多い。記事では「Base は Coinbase ネイティブの本拠、Solana は現状の tx 量最大」と正確に書くべき。

---

## 10. まとめ — 「無人」と「人間がエッジ」の誠実な腑分け

| 対象 | 自律性 | 根拠（逐語） |
|---|---|---|
| nookplot | fully-no-human（自己申告） | 「no central server... no one entity in control」「autonomous mining loop」 |
| x402 / Base MCP の配管 | 配管は no-human、公式MCPの書込は承認制 | 「authorizes the what... leaves the how to the facilitator」/「Every write action requires your approval」 |
| OpenClaw/Moltbook の一部行動 | fully-no-human の記録あり | 「no human intervention required」「no human telling the AI to do this」 |
| ZHC Institute/Juno | human-at-edges | 「humans only at the edges: founders set direction, agents execute」 |
| Virtuals/ACP | human-at-edges（取引は自律） | 「While Human Users Capture Ongoing Revenue」 |
| Felix / Kelly Claude | human-at-edges | Nat Eliason と並走 / Apple審査・加盟店依存 |
| OpenClawnch / Franklin | human-at-edges（ポリシー委任の自動執行） | 「Every write transaction goes to your phone」/ 予算は人間設定 |
| トレーディングBOT全般 | 人間制御 | 「executes a trade you authorized」 |

**核心**：x402 + USDC on Base という配管は「無人で金が動く」を技術的に可能にしたが、**継続的な収益はまだ人間がエッジに居る**。fully-no-human の実例（nookplot、Moltbook の暴走）は存在するが、規模は微小（$50M / 0.0001%）かつ、Shamblog/Moltbook流出のような**ガードレール無き自律の脆さ**も同時に記録されている。

---

## 出典一覧

- nookplot: https://nookplot.com/
- nookplot economy: https://nookplot.com/economy
- nookplot docs/overview: https://nookplot.com/docs/overview
- nookplot docs/mining: https://nookplot.com/docs/mining
- ZHC Institute: https://www.zhcinstitute.com/
- ZHC Institute data room: https://www.zhcinstitute.com/data/
- Factory Floor — Juno: https://factoryfloor.dev/agent/juno
- Virtuals Protocol: https://www.virtuals.io/
- Virtuals whitepaper: https://whitepaper.virtuals.io/
- Virtuals capital-formation-layer: https://whitepaper.virtuals.io/about-virtuals/capital-formation-layer
- Virtuals app/create（ログインゲート、内容取得不可）: https://app.virtuals.io/create
- PRNewswire — Virtuals Revenue Network: https://www.prnewswire.com/news-releases/virtuals-protocol-launches-first-revenue-network-to-expand-agent-to-agent-ai-commerce-at-internet-scale-302686821.html
- LinkedIn/Alchemy（検索スニペット、本体ブロック）: https://www.linkedin.com/posts/alchemyinc_ai-agents-are-already-transacting-onchain-activity-7450604047239327745-D9hs
- OpenClawnch（GitHub）: https://github.com/clawnchdev/openclawnch
- OpenClawnch commit（過大主張削除）: https://github.com/clawnchdev/openclawnch/commit/1014be610139c3cb02b0e7325003b7ad800cac5c
- OpenClawnch commit（recursive self-improvement）: https://github.com/clawnchdev/openclawnch/commit/7e2bb86fb66e4206c75b958c81f115a87a290c0e
- Franklin / BlockRun（GitHub）: https://github.com/blockrunai/franklin
- Felix Craft: https://felixcraft.ai/
- Factory Floor — Felix: https://factoryfloor.dev/agent/felix
- @FelixCraftAI（自律の限界ツイート）: https://x.com/FelixCraftAI/status/2027762454214644054
- Factory Floor — Kelly Claude: https://factoryfloor.dev/agent/kelly-claude
- @KellyClaudeAI: https://x.com/KellyClaudeAI
- Base for Agents: https://www.base.org/agents
- Base docs — AI Agents: https://docs.base.org/ai-agents
- Galaxy — x402 AI agents crypto payments: https://www.galaxy.com/insights/research/x402-ai-agents-crypto-payments
- Galaxy — Zero-Human Companies（深掘り用）: https://www.galaxy.com/insights/research/zero-human-companies-ai-agents-defi-crypto
- Nevermined — stablecoin payments AI agents 統計: https://nevermined.ai/blog/stablecoin-payments-ai-agents-statistics
- MissionCloud — OpenClaw/Moltbook 解説: https://www.missioncloud.com/blog/openclaw-explained-how-1.5m-ai-agents-built-a-religion-crypto-economy-and-escaped-control
- theshamblog — AI agent hit piece: https://theshamblog.com/an-ai-agent-published-a-hit-piece-on-me/
- IndieHackers — 7 autonomous AI agents 分析: https://www.indiehackers.com/post/i-analyzed-7-autonomous-ai-agents-for-business-in-2026-here-s-what-i-concluded-e34c50741f
- CoinGecko — AI Agents カテゴリ: https://www.coingecko.com/en/categories/ai-agents
- Altrady — AI agents in crypto: https://www.altrady.com/blog/cryptocurrency/ai-agents-in-crypto
- @karpathy（Moltbook 評）: https://x.com/karpathy/status/2017296988589723767
