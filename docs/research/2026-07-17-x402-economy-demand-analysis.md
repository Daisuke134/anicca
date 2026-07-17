# x402 経済 需要分析 — 何が売れるか / 元手ゼロ bootstrap / 薄い市場への処方箋

更新: 2026-07-17。ソース = crwl 実測 + ctx7 + gh search。断定には全てソース付き。「確認できず」は正直に明記。

## 背景（我々の現在地、STATUS.md より）

- colony 合計 x402 純売上（外部購入者のみ、生涯）= **$0.357362 / 22件**（`docs/STATUS.md` 実測、2026-07-17）。
- Bazaar 全体で唯一の明確な実需 = ottoai 宛の鯨bot1体（$698 funded、probe→採用の行動様式）。
- franklin1 は Bazaar 未掲載（Tailscale Funnel が443/8443/10000の3ポートのみ、4体目の席が無い）。
- 競合 `agentservices.to`（50 API、$0.02/call）の生涯売上 = $0.169/12件、payer 3体全てfacilitatorテストwallet = 実需ゼロ。
- 詳細 → `docs/STATUS.md` §MKT-1、`docs/research/2026-07-17-agentservices-competitor-analysis.md`。

---

## 1. エージェント経済で売れる物 — 予測と実データ

### 1-1. Coinbase 公式ローンチ記事の「売れる物」予測（2025-05-06）

> "Autonomous Cloud Compute... Market Intelligence... Prediction Markets... Consumer and Supply Chain Automation... AI-driven Creative Tools"
> — Erik Reppel et al., [Introducing x402](https://www.coinbase.com/developer-platform/discover/launches/x402)

Coinbase自身の想定ユースケース = **エージェントが自分でできないこと**: リアルタイム市場データ、GPU推論、予測市場データ、サプライチェーン価格見積、プレミアムメディア/創作ツール。「計算・整形・変換」は挙がっていない — 上流アクセス権・専門データ・行為の代行が中心。

### 1-2. x402scan 実データ（2026-07-17時点、30日間）— 何に金が流れているか実測

出典: [x402scan.com](https://www.x402scan.com/) / [x402scan.com/resources](https://www.x402scan.com/resources)（Merit Systemsが運営するon-chain block explorer）

| カテゴリ | 代表サービス | 30日売上 | 説明 |
|---|---|---|---|
| **LLM/AIゲートウェイ（圧倒的トップ）** | BlockRun | **$178.03K / 14.68M tx** | 「全フロンティアモデルへの1エンドポイント課金ルーティング」。2位の10倍近い |
| インフラ/DePIN | dTelecom | $18.56K / 8.82K tx | WebRTC・音声認識・TTSのpay-per-use |
| データ列挙(enrichment) | StableEnrich | $1.76K / 46.69K tx | FullEnrich/CompanyEnrich/Exa/Firecrawl等の再販代理 |
| オンチェーンデータ | sol.blockrun.ai | $1.27K / 9.83K tx | Solana RPC/データ |
| トレード/市場情報 | Otto AI(ottoai) | $103.89 / 64.66K tx | market intel・DeFi実行・創作ツール74種、$0.001〜 |
| ソーシャルデータ | twit.sh | $617 / 100.95K tx | X(Twitter)データ、サインアップ不要 |
| オンチェーン分析 | Nansen AI | $131 / 6.42K tx | 500M+ ラベル付きアドレスでスマートマネー追跡 |
| Web検索 | Exa | $37.49 / 5.49K tx | ニューラル検索・クロール |

**含意**: 単価の勝負ではなく「上位1社が全体の何十倍も稼ぐ」べき乗則。LLMアクセス自体（推論の再販）が最大の需要 — エージェントが最も欲しいのは「データ」より先に「もっと安く/柔軟に考える力」。次点はリアルタイム性の高いデータ（SNS・オンチェーン・市場）。

**市場規模の相違に注意**: x402.org公式（自社facilitator経由分のみ集計）は直近30日 **75.41M tx / $24.24M / 94.06K buyers / 22K sellers**（[x402.org](https://x402.org/)）。x402scan（複数facilitator横断集計）は同期間 **17.87M tx / $853.48K / 48.74K buyers / 61K sellers**。$24.24Mと$853Kの23倍差は集計範囲の違い（facilitator網羅率・batch settlement等の扱い差）であり、どちらも「本物の外部購入」と「内部ノイズ」を区別していない点は我々の$0.357との比較で常に注意。

### 1-3. x402scan「Marketplace」24時間実測 — 市場の薄さの独立裏付け

> Active Merchants 6.18K / New Merchants 1.89K / **Active Registered Merchants 30** / **Unique Buyers (Registered) 316**
> — [x402scan.com/resources](https://www.x402scan.com/resources)

「Active Merchants 6.18K」は生の on-chain 検知件数、一方「Registered」(=Bazaar等に正式掲載)は24hでわずか **30店・買い手316体**。これは我々自身の実測（agentservices.toの実需ゼロ、ottoai以外に明確な反復買い手なし）と独立に整合する — **x402市場は全体として薄い**。「掲載面を稼働店舗数万に対して30店だけが持つ」という事実が、掲載（discovery）の希少性そのものが差別化要因であることを示す。

### 1-4. カテゴリ別サーバー数（供給側の内訳、x402scan実測）

Search Servers 849 / Crypto Servers 1,149 / AI Servers 1,396 / Trading Servers 593。AI/Cryptoが供給過多気味、Trading/Search は相対的に薄い。「良い商品を安く出す」だけでは埋没する供給過多カテゴリと、まだ薄いカテゴリが混在。

### 1-5. Bazaar（発見層）の仕組み — 我々の律速点の技術的裏付け

> "The Bazaar solves a critical problem in the x402 ecosystem: discoverability... we're currently more like 'Yahoo search' - functional but evolving."
> — [docs.x402.org/extensions/bazaar](https://docs.x402.org/extensions/bazaar)

Facilitatorが`/discovery/resources`エンドポイントを提供し、ルート設定に`bazaar`拡張を含めた店舗のみが機械可読カタログに載る。**掲載自体がfacilitator側のバザー拡張実装に依存**し、x402公式も「発見層はまだ未成熟」と認めている。franklin1がFunnelポート制約で未掲載である問題は、我々固有のバグというより、この発見層がまだ粗い段階にあるエコシステム全体の構造的課題の一部。

---

## 2. 元手ゼロ bootstrap の具体戦略（faucet/grant/UBI 以外）

### 2-1. Proof-of-Work支払い — 実在する非faucet型ゼロ資本入口

> "free · pow 218 [tools]... free tier pays in compute - USDC on Base + 6 more chains, or USDG on Robinhood Chain when you scale."
> — [agent402.tools](https://agent402.tools)（506ツール中218ツールが計算力での支払いで無料利用可）

Agent402は「同じ入口の下で、無料ツールはproof-of-work（計算資源の消費）で支払い、有料ツールはx402ウォレットで支払う」という二層構造を実装。これはfaucet（他者からの一方的給付）ではなく、**エージェント自身の計算資源を対価として差し出す真の"働いて入場料を払う"モデル**。ウォレット残高ゼロの新規エージェントでも「まず無料枠で価値を出す→稼いだUSDCで有料枠に上がる」という段階的な資本形成ループが技術的に用意されている。

### 2-2. 売り手側の無料参入 — 供給側コストゼロ

> "list your API free · health-ranked"
> — [agent402.tools/sell](https://agent402.tools/sell)

売る側の掲載自体は無料（health-rankedで質に応じて露出が変わる仕組み）。これは1-5のBazaar掲載問題への直接的な代替導線 — **facilitator依存のBazaarだけでなく、agent402のような第三者マーケットプレイスにも無料で並行掲載できる**、というのが最も具体的な"copyできる"戦術。

### 2-3. Try-before-you-pay の無料枠（BlockRun）

> "Free — Try without paying — no card, no signup"
> — [blockrun.ai](https://blockrun.ai)（一部モデルを無料枠で試用可能）

有料APIゲートウェイ自体も「無料モデルで動作確認→有料モデルへ移行」という段階を用意。買い手側の資本ゼロ状態への配慮がエコシステム標準になりつつある。

### 2-4. テストネットからの段階移行（x402公式ガイダンス）

> "This quickstart begins with testnet configuration for safe testing. When you're ready for production, see Running on Mainnet..."
> — [docs.x402.org/getting-started/quickstart-for-sellers](https://docs.x402.org/getting-started/quickstart-for-sellers)

Base Sepolia / Solana devnetで無料検証してからmainnetへ、という公式に推奨された「$0で配線を検証してから資本を投入する」順序。我々のfranklin1がまだ本番未掲載である状況を「まず配線を$0で固める段階」と捉え直せる。

### 2-5. 「$0→$1→再投資」の体系的方法論記事

★確認できず★。x402公式・a16z crypto（該当タグ404、記事未発見）・x402scan運営元Merit Systemsのブログいずれにも、エージェント視点の「元手ゼロから最初の$1を作り再投資する」体系的な方法論記事は見つからなかった。存在するのは上記2-1〜2-4の**個別プロダクトが用意した実装レベルの入口**のみ。この分野はまだ「事例」より「インフラの部品」が先行している段階と判断する。

---

## 3. 「AI が人間に x402 で売る」の可能性

x402公式ローンチ記事は「humans, scripts, or AI agents」を明示的にクライアント側の対象として含めており（[Coinbase blog](https://www.coinbase.com/developer-platform/discover/launches/x402)）、Cal.comの例（"paid human interactions... accessible by both agents and users alike"）は人間の買い手を想定した実例。ただし x402scan の実測データ（1-2, 1-3）に出てくる買い手はほぼ全てエージェント/bot（EIP-3009 delegation、relayer EOA経由等）で、**人間が直接x402でAIから買うユースケースは公式には可能とされているが、実データ上の主流はまだagent-to-agent**。人間側は依然として「クレカ→サブスク」が主流であり、x402は「エージェントが払う」文脈で先行している。

---

## 4. 我々の薄い市場問題への処方箋3つ

### 処方箋1: 掲載面を増やすこと自体が最大のレバー（価格競争力より優先）

x402scan実測（1-3）で「稼働店舗数千 対 正式登録店舗わずか30」という事実は、**良い商品を安く出しても正式な発見経路に載らなければ客が来ない**という我々自身のMKT-1の結論と独立に一致する。処方: franklin1のBazaar掲載（ポート問題の解消）と並行して、agent402.tools（2-2で確認済み・無料掲載）のような**facilitator非依存の第三者マーケットプレイスにも同時掲載**し、発見経路を複線化する。

### 処方箋2: 実需の証明されたカテゴリ（トレード/市場情報）に留まる

x402scanのカテゴリ別実測（1-2, 1-4）で、Otto AI・Syra・SniperX・twit.shなど「トレード/市場情報」系が実売上を持つ数少ないカテゴリの一つであり、しかも我々の唯一の実需(ottoai鯨bot)そのものがこのカテゴリの買い手。T9で選んだfunding-rates商品はこの検証済みレーンに正しく位置している — 方向転換は不要、**掲載面拡大に全リソースを振るべき**という現行STATUS.mdの結論（T8/MKT-1優先）を外部データが裏付ける。

### 処方箋3: 鯨botの「probe」コストを極小化する

U9実測（STATUS.md）で鯨botは「$0.001〜0.01で数千エンドポイントを1回ずつprobeし、良かった少数だけ本採用して連打する」行動様式と確定済み。処方: 2-1のAgent402のPoW無料枠のように、**最初の接触コストをゼロまたはそれ以下に切り詰める**（例: 最初のN回は無料または$0.001未満にし、probe→採用の"probe"段階の摩擦を減らす）。価格を下げること自体より、「probeされた瞬間に良い応答を返す」ことがこの鯨1匹を捕まえる唯一の再現可能な戦術。

---

## 5. copy/着想できるアイデア（優先度付き）

1. **[高]** agent402.tools への無料掲載（`list your API free`）— 実装コストほぼゼロ、Bazaar掲載問題と並行して即着手可能。
2. **[高]** 最初の数回を無料/PoW型にする「probe摩擦ゼロ化」— 鯨botのprobe行動様式に直接対応。
3. **[中]** スキルパック型の複合商品（Agent402の"skill pack"モデル: 複数ツールを1回の支払いでオーケストレーション、単価$0.05〜$1.50）— 単発$0.003より高単価を1コールで回収できる可能性。ただしfranklin1のLLM無料化方針（sol-trade KILL済み）と矛盾しないよう、LLM不要な純算術オーケストレーションに限定する必要あり。
4. **[低・後回し]** 信頼/評判スコアリング（crest-counterparty-intelligence、beacon、moltguard等、gh検索で複数の類似ハッカソン系プロジェクトを確認）— x402がpay-first・無登録ゆえに生まれた需要だが、既に複数の競合が同時多発的に参入しており差別化が困難。

---

## ソース一覧

- Coinbase, "Introducing x402: a new standard for internet-native payments" (2025-05-06) — https://www.coinbase.com/developer-platform/discover/launches/x402
- x402.org homepage（30日統計）— https://x402.org/
- x402.org Blog（v2 launch, batch settlement告知）— https://x402.org/blog/
- docs.x402.org, "Bazaar (Discovery Layer)" — https://docs.x402.org/extensions/bazaar
- docs.x402.org, "Quickstart for Sellers" — https://docs.x402.org/getting-started/quickstart-for-sellers
- docs.x402.org, "MCP Server with x402" — https://docs.x402.org/guides/mcp-server-with-x402
- x402scan（Merit Systems運営、on-chain実測ダッシュボード）— https://www.x402scan.com/、https://www.x402scan.com/resources、https://www.x402scan.com/ecosystem
- agent402.tools（PoW無料枠・無料掲載の実例）— https://agent402.tools
- blockrun.ai（無料モデル試用枠の実例）— https://blockrun.ai
- useotto.xyz（ottoaiの正体 = Virtuals Protocol上の自律DeFiエージェント群）— https://useotto.xyz
- gh search repos "x402 agent economy"（信頼/評判スコアリング系の同時多発参入を確認）
- 内部: `docs/STATUS.md`（我々の実測データ全般）、`docs/research/2026-07-17-agentservices-competitor-analysis.md`
- 未発見（確認できず）: a16z cryptoのx402特化記事（該当タグ404、featured articlesにも該当なし）
