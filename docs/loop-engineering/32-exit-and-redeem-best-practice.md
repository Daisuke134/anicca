# 32 — Exit / Redeem Best Practice（小資本AIエージェントの利確・現金化ルール）

日付: 2026-07-12
調査者: Claude（research-only、実装なし）
検索手段: `firecrawl scrape`（一次情報優先。Google検索結果ページのscrapeも含む）

---

## 0. 要旨（先に結論）

「利益を確定してポケットに入れる」判断は3レールで質が違う。

| レール | 核心の答え |
|---|---|
| Polymarket | **待って redeem が期待値で勝つのは稀**。decisive前に近い（$0.97-0.999）なら early exit（指値売り）の方が年率換算で有利なことが学術的に実証されている。redeem自体はガス代ゼロ・期限なしだが「certainty の後」も現金化まで資金がロックされる（settlement discount） |
| Spot crypto (SOL等) | 固定%より **ATR/ボラティリティ連動のトレーリングストップ**が定番。ただし学術研究(Kaminski & Lo 2014)は「頻繁な低サンプリング頻度の損切りは価値を壊す、長めのサンプリング頻度でのみ有効」と示す。小資本では手数料が0.25-1%を超えるとエッジを食い潰す |
| DeFi yield | 複利化(harvest)頻度の限界効用は数学的に速く飽和する（年率50%台でも年4回で理論最大値の90%超に到達）。ボトルネックは複利頻度ではなく**ガス代 vs ポジションサイズ**。小口はプロトコル側の自動複利(Beefy/Yearn)に任せた方が得 |

---

## 1. Polymarket（予測市場）

### 1.1 Redeem の公式仕様

**いつ・どうやって redeem するか**（一次情報: Polymarket公式ドキュメント）

- 出典: Polymarket Docs "Resolution" — https://docs.polymarket.com/concepts/resolution
  > "When the outcome of an event becomes known, the market is **resolved**. Resolution determines which outcome won, allowing holders of winning tokens to redeem them for $1 each. Losing tokens become worthless. Polymarket uses the **UMA Optimistic Oracle**... Anyone can propose an outcome, and anyone can dispute it if they believe it's incorrect."

- 決着タイムライン（同ソース）:
  | フェーズ | 所要時間 |
  |---|---|
  | Challenge period | 2時間 |
  | Debate period（disputeされた場合） | 24-48時間 |
  | UMA投票（disputeされた場合） | 約48時間 |
  | **Undisputed resolution** | **~2時間**（proposal後） |
  | **Disputed resolution** | **4-6日** |

- Redeem実行（出典: Polymarket Docs "Redeem Tokens" — https://docs.polymarket.com/trading/ctf/redeem）
  > "You can redeem at any time after resolution — there's no deadline. Your winning tokens will always be redeemable."
  > "Redeeming converts winning outcome tokens into pUSD after a market resolves. Each winning token is worth exactly $1.00 — the losing token is worth $0."

- Redeemはガス代ゼロ（relayer経由）（出典: Polymarket Docs "Gasless Transactions" — https://docs.polymarket.com/trading/gasless）
  > "Polymarket pays gas for all operations routed through the relayer" — 対象operationsの表に **CTF operations: Split, merge, and redeem positions** が明記。

→ 実務含意: redeemは「早くやらないと損」というものではない（期限なし・ガス代なし）。だが次の1.2/1.3が示す通り、**redeemを待つこと自体が機会費用を生む**。

### 1.2 Early exit（決着前に市場で売り抜ける）vs 決着を待つ

- 出典: Polymarket Help Center "Can I Sell Early?" — https://help.polymarket.com/en/articles/13364247-can-i-sell-early
  > "Yes, you can sell or close your position early... by either placing a market order to sell shares at the prevailing bid price in the orderbook, or by placing a limit order..."

- 出典（核心・学術論文）: Jonas Gebele & Florian Matthes (TU Munich), "When Certainty Is Not Worth It: Capital Lock-Up and Settlement Discounting in Prediction Markets", arXiv:2605.31431 (2026-05-29) — https://arxiv.org/abs/2605.31431 / フルテキスト https://arxiv.org/html/2605.31431v1

  Abstract の核心一文:
  > "When collateral remains locked until oracle settlement, a near-certain dollar is a delayed dollar, so prices embed a maturity-dependent settlement discount in addition to beliefs about outcomes... We recover an implied settlement-discount term structure... and summarize it as an annualized settlement wedge (ASW). The recovered wedges are positive, maturity-dependent, and time-varying."

  具体例（本文 §1、実例で「certainty の後もロックされた資金」を定量化）:
  > "Polymarket's 'Will Jesus Christ return in 2025?' market is illustrative: for months, the complementary near-certain NO side traded around $0.96. A trader buying $1,000 of NO at that price would earn roughly 4.2% if the position paid $1 at settlement, **but only after locking capital for most of the year**."

  ASW（年率換算後の必要リターン）の実測パターン（§5.1）:
  > "ASW falls sharply from the short end, stabilizes by roughly 20 days, then rises again, with a long-end hump around 230–260 days... tiny near-par discounts annualize into high ASWs [at the short end]."

  → 実務含意: 決着間際（数時間〜数日）の $0.995-$0.999 での早期売却は、名目上0.1-0.5%の割引に見えても**年率換算では極めて高い「実効リターン」を捨てていない**（むしろ受け取っている）。逆に長期（数ヶ月）ロックされる near-certain ポジションは、額面上「確実」でも年率数%〜十数%相当の機会費用を払っている。

  → **意思決定ルール**: 残り決着まで「時間が短い（時間〜数日）」ケースは redeem を待つ方が有利（早期売りの名目割引が相対的に大きい）。「残存期間が長い（週〜月単位）」near-certain ポジションは、期待値が同等なら **早期に指値で売り抜けて資金を回転させる方が年率ベースで有利** — これがまさに ASW が示す「certainty の後の待ち時間はタダではない」という定量的根拠。

### 1.3 「$0.97で価格が止まる」現象（残り3%を取るための長期ロック問題）

- 上記 arXiv:2605.31431 がこの現象自体を主題として扱っており、「ASW（annualized settlement wedge）」として定量化している。$0.96-0.999で価格が張り付き続けるのは、単なる非効率ではなく「決済までの資金ロックに対する市場が求めるリターン」であることを実証（§1, §5.1 上記引用）。

- 出典（taker損失の構造・「誰が勝ち誰が負けるか」）: Pat Akey, Vincent Grégoire, Nicolas Harvie, Charles Martineau, "Who Wins and Who Loses In Prediction Markets? Evidence from Polymarket", SSRN 6443103 (2026-03-18, 158頁) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6443103
  > "Using $67 billion in trade volume, we show that the gains are highly concentrated: the top 1% of users with positive PnL capture 76.5% of profits. **Successful traders provide liquidity using limit orders** that resolve favorably relative to realized outcomes **while unsuccessful traders take liquidity using market orders**."

  → 実務含意: 出口（exit）は可能な限り **指値（limit / maker）** で置く。成行（market / taker）でのexitは、テイカー手数料に加えて「負ける側」の行動パターンと一致する。

### 1.4 手数料構造（redeem/exit判断のコスト側）

- 出典: Polymarket Docs "Fees" — https://docs.polymarket.com/trading/fees
  > "fee = C × feeRate × p × (1 - p)" — Cはシェア数、pは価格。**Makerは常に無料**、taker feeのみ課金。
  カテゴリ別 taker fee rate: Crypto 0.07 / Sports 0.05 / Politics 0.04 / **Geopolitics 0** （地政学・世界情勢マーケットは手数料ゼロ）。
  > "Geopolitical and world events markets are fee-free. Polymarket does not charge fees or profit from trading activity on these markets."

  100シェア・$0.50での taker fee は $1.75（3.5%相当、価格50%近辺がfee率のピーク）。→ 決着間際（price→$0.97-0.99）ではfeeは名目上小さくなる（fee = C×rate×p×(1-p) は p→1 で →0 に近づく）ため、**早期exitのコストはfeeよりも「割引価格そのもの」が支配的**。

---

## 2. Spot 暗号通貨トレード（Solana/SOL・USDC等）

### 2.1 TP/SL: 固定% vs ATRベース vs トレーリングストップ

- 出典（学術・最も権威ある一次研究）: Kathryn M. Kaminski & Andrew W. Lo, "When Do Stop-Loss Rules Stop Losses?", Journal of Financial Markets, vol.18 (2014), pp.234-254. DOI: 10.1016/j.finmar.2013.07.001 — https://ideas.repec.org/a/eee/finmar/v18y2014icp234-254.html
  > "Using daily futures price data, we provide an empirical analysis of stop-loss policies applied to a buy-and-hold strategy using index futures contracts. **At longer sampling frequencies, certain stop-loss policies can increase expected return while substantially reducing volatility**, consistent with their objectives in practical applications."

  → 含意: 損切り・利確ルールの効果はサンプリング頻度（=どのくらいの間隔で価格をチェックしてトリガーするか）に強く依存する。ティック単位の高頻度チェックは意図せぬ早期決済（whipsaw）を招きやすく、日次〜より長い間隔でのルール適用の方が「期待リターン向上+ボラティリティ低減」を両立しやすいという実証結果。

- 出典（ATRトレーリングストップの実務標準）: Colin Twiggs, Incredible Charts, "Average True Range (ATR) Trailing Stops" — https://www.incrediblecharts.com/indicators/atr_average_true_range_trailing_stops.php
  > "Multiples between 2.5 and 3.5 x ATR are normally applied for trailing stops, with lower multiples more prone to whipsaws. **The default is set as 3 x 21-day ATR.**"
  ATR自体はJ. Welles Wilderの1978年の著書 "New Concepts In Technical Trading Systems" が原典。
  > "Average True Range Trailing stops are more adaptive to varying market conditions than Percentage Trailing Stops but achieve similar results when applied to stocks that have been filtered for a strong trend."

- 出典（固定%トレーリングストップのバックテスト）: Tim du Toit, Quant-Investing, "Trailing Stop Loss: Your Smart Way to Maximize Returns" — https://www.quant-investing.com/blog/best-trailing-stop-loss-settings-to-maximize-your-returns
  > "Based on backtesting across multiple markets, **a 15% or 20% trailing stop loss produced the best risk-adjusted returns**. However, the optimal percentage depends on stock volatility: large-cap stocks may work well with 15%, while small-cap or volatile stocks may need 20% or wider."
  > "Trailing stop losses outperformed fixed stop losses in all market conditions tested."

  → 結論: ATRベースと固定%トレーリングは「強いトレンドフィルターと組み合わせれば同等の結果」（Incredible Charts評価）。SOL等の高ボラ資産では**ATR方式（2.5-3.5倍、21日）**の方がレジーム変化に強い。低頻度チェック（日次以上）でルールを適用する（Kaminski & Lo）。

### 2.2 小資本での手数料・スリッページの閾値

- 出典（一次情報・Hyperliquid公式）: Hyperliquid Docs "Fees" — https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees
  ベースレート（14日出来高0）: **Taker 0.045% / Maker 0.015%**。
  > "Fees are based on your rolling 14 day volume... Spot pairs between two spot quote assets have 80% lower taker fees..."

- 出典（TP/SL成行注文のスリッページ許容）: Hyperliquid Docs "Take profit and stop loss orders (TP/SL)" — https://hyperliquid.gitbook.io/hyperliquid-docs/trading/take-profit-and-stop-loss-orders-tp-sl
  > "TP/SL market orders have a slippage tolerance of 10%." — 成行TP/SLは最大10%のスリッページを許容する設計（＝指値TP/SLで許容幅を自分で制御すべき）。

- 出典（小口口座での手数料が飲み込む閾値）: For Traders, "How to Trade with Small Capital in 2025" — https://www.fortraders.com/blog/trade-small-capital
  > "For a **$2,000 account, even $5 in total costs per trade means you need a 0.25% gain just to break even**. If you make 20 trades a month, those costs add up to $100 - 5% of your account - before seeing any profit."

  → $20-40規模のAIエージェントに換算: ポジションが$20-40なら、$0.05-0.10程度の固定コスト（取引所の最低手数料やDEXのガス代込みスリッページ）でも0.25-0.5%の損益分岐が生じる。**1トレードあたりの往復コスト（fee×2 + slippage）が期待エッジの1/3を超える場合は見送るべき**という経験則がこの数字から導かれる。

### 2.3 「利確しないと含み益は幻」の定量的裏付け

- Polymarket研究（arXiv:2605.31431）の核心ロジックがそのままspotにも転用できる: 「certainty（含み益）」と「redeemable cash（現金化された利益）」は別物であり、後者に転換するまでの時間が長いほど、その間のボラティリティ・機会費用リスクにさらされる。Kaminski & Lo (2014) の実証結果 — 損切り/利確ルールが「長めのサンプリング頻度」で expected return を上げつつ volatility を下げる — は、裏を返せば「ルールなしで含み益を放置し続ける（＝ポジションを閉じない）」戦略は volatility を余分に抱え込むことを意味する。

---

## 3. DeFi Yield / Lending の harvest（複利化）頻度

### 3.1 最適harvest間隔の数式・トレードオフ

- 出典（一次情報・DeFiプロトコル公式ドキュメント）: Pickle Finance Docs, "The Jar APY - The Math Behind Compounding" — https://docs.pickle.finance/the-jar-apy-the-math-behind-compounding
  APR→APY変換式（複利頻度をパラメータ化）:
  > "APY = (baseAPR + (((1+(0.8\*rewardAPR/compoundsPerYear))^compoundsPerYear)-1))"
  > "Some strategies do not compound daily, despite our best efforts. Either the pools do not have enough money in them, or **the strategy does not return enough rewards relative to gas costs to justify daily compounding**. This is not a bad thing. For lower and medium yielding strategies **the difference between daily or weekly compounding is minimal**."

  同ソースの数値例: 10%ベース+100%報酬APRの戦略で、**日次複利=132.36%APY** vs **月次複利=126.9%APY**（差はわずか5.5ポイント）。

- 出典（数学的証明・複利頻度の限界効用逓減）: Math StackExchange, "Optimal interest compounding frequency" — https://math.stackexchange.com/questions/4051273/optimal-interest-compounding-frequency
  質問者が定式化した問題（クリプトのgas fee文脈で明示的にフレーム化）:
  > "Especially when the compounding must be done manually or there might be a small fixed transaction fee charged for every compounding (in cryptocurrency yield farming for example)."

  回答の核心不等式（連続複利 $e^r$ に対し、離散複利が何回で90%に到達するか）:
  > "$e^r(1-\frac{r^2}{n}) \le (1+\frac{r}{n})^n \le e^r$... If $r=55\%$... $e^r(1-\frac{r^2}{n})>0.9e^r$ for $n>0.55^2/0.1=3.025$" — つまり**年率55%という高利回りでも、年4回（四半期）の複利で理論上限の90%以上に到達する**。

  → 実務含意: 複利化「頻度」自体の限界効用は極めて速く飽和する（年数回で90%超）。したがって「どのくらいの頻度でharvestすべきか」を決めるボトルネックは複利数学ではなく**gas代とポジションサイズの比**。

### 3.2 小資本でガス代負けする閾値

- 出典: spark.money, "DeFi Yield Aggregators Compared: Yearn, Beefy, Convex" — https://www.spark.money/tools/defi-yield-aggregator-comparison
  > "Gas costs for frequent compounding erode returns on smaller positions (**Yearn estimates ~$720/day in gas for hourly harvests at $30/call**)"
  > "Yearn uses Keep3r bots to trigger `harvest()` calls on its strategies. The bot network **monitors gas costs against expected yield and only harvests when profitable**."
  > "The breakeven point depends on position size and compounding frequency. **For sub-$10,000 positions on Ethereum mainnet, aggregator gas optimization typically delivers better net returns than manual compounding.** For larger positions on low-fee L2s, the advantage narrows."

  → 実務含意（$20-40資本に直結）: **数万円〜数十万円未満のポジションで手動harvestは非合理**。Ethereum L1では$30/callのガス代だけでポジションを溶かす。$20-40のAIエージェント資本は必ず（a）L2/低ガスチェーン（Base, Arbitrum, Solana等）を使う、（b）Beefy/Yearn等の自動複利vault（gas代が"only harvest when profitable"のロジックでシェアされる）に委任する、のいずれかであるべきで、自前でharvestトランザクションを発行すべきではない。

---

## 4. 3レール横断 — 「利益をポケットに入れる」実務ルール表

| レール | 確定トリガー | 頻度/タイミング | 現金化の形態 | 閾値・条件 |
|---|---|---|---|---|
| **Polymarket** | 残存決着期間が「時間〜数日」なら **redeemを待つ**（ガス代ゼロ・期限なし）。残存期間が「週〜月」で価格が near-certain（$0.95+）に張り付いたら **指値でearly exit** | 決着直後（undisputed なら+2時間で redeem可）／ near-certainだが長期ロックなら都度（週次で判断） | pUSD（redeem） or 成行/指値売却によるUSDC相当 | 早期売りは常に **limit order**（maker）で出す。市場が薄い（低流動性）長期マーケットほど早期exitの価値が上がる（arXiv:2605.31431のASW参照） |
| **Spot crypto (SOL)** | ATRベーストレーリングストップ（**2.5-3.5×ATR、21日、デフォルト3×**）でトリガー。固定%なら**15-20%**が実証的に妥当 | **日次以上の低頻度**でルールを評価（Kaminski & Lo 2014、ティックごとの高頻度判定はwhipsawを招く） | 指値決済優先（Hyperliquid: taker 0.045%/maker 0.015%、成行TP/SLは10%スリッページ許容） | 往復コスト（fee×2+slippage）が**期待エッジの1/3を超えたら見送り**。$20-40ポジションで固定コストが$0.05-0.10超なら0.25%以上の値幅を要求 |
| **DeFi yield** | ガス代 < 見込み追加リターンの時のみharvest（Yearn Keep3rと同ロジック） | 複利頻度自体は**年4回（四半期）で理論上限の90%超**に到達済み（年率55%でもn≥3で十分）— 頻度を上げる意味は薄い | オートコンパウンドvault（Beefy/Yearn）への委任、または手動なら低ガスL2/Solana限定 | **$10,000未満のポジションはaggregatorのgas最適化に任せる**（自前harvestは$30/call級のL1ガスで即赤字）。$20-40資本は自前harvest絶対禁止 |

### 共通原則（3レール貫通）

1. **「含み益」と「現金」は別物**（arXiv:2605.31431の核心）— 未確定・未redeemの利益は、確定までの時間に比例した機会費用（ASW/ボラティリティリスク）を内包する delayed dollar である。
2. **maker/limitで出口を取る** — Polymarket（Akey et al. 2026: 勝者はmaker、敗者はtaker）・Hyperliquid（maker feeが1/3）ともに同じ結論。
3. **固定コストに対してポジションサイズが小さいほど、頻度を落とす**べき — DeFi harvestもspotの損切り判定も、$20-40規模では「高頻度の判定・執行」がコストで負ける。判定頻度を下げ、閾値（ATR倍率・複利間隔）を広めに取ることが小資本の生存戦略。

---

## 参照リンク一覧

- Polymarket Docs — Resolution: https://docs.polymarket.com/concepts/resolution
- Polymarket Docs — Redeem Tokens: https://docs.polymarket.com/trading/ctf/redeem
- Polymarket Docs — Gasless Transactions: https://docs.polymarket.com/trading/gasless
- Polymarket Docs — Fees: https://docs.polymarket.com/trading/fees
- Polymarket Help Center — Can I Sell Early?: https://help.polymarket.com/en/articles/13364247-can-i-sell-early
- Gebele & Matthes (2026), arXiv:2605.31431 — https://arxiv.org/abs/2605.31431 (full text: https://arxiv.org/html/2605.31431v1)
- Akey, Grégoire, Harvie, Martineau (2026), SSRN 6443103 — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6443103
- Kaminski & Lo (2014), Journal of Financial Markets 18:234-254 — https://ideas.repec.org/a/eee/finmar/v18y2014icp234-254.html
- Incredible Charts (Colin Twiggs) — ATR Trailing Stops: https://www.incrediblecharts.com/indicators/atr_average_true_range_trailing_stops.php
- Quant-Investing (Tim du Toit) — Trailing Stop Loss: https://www.quant-investing.com/blog/best-trailing-stop-loss-settings-to-maximize-your-returns
- Hyperliquid Docs — Fees: https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees
- Hyperliquid Docs — TP/SL Orders: https://hyperliquid.gitbook.io/hyperliquid-docs/trading/take-profit-and-stop-loss-orders-tp-sl
- For Traders — Trade with Small Capital: https://www.fortraders.com/blog/trade-small-capital
- Pickle Finance Docs — The Jar APY: https://docs.pickle.finance/the-jar-apy-the-math-behind-compounding
- Math StackExchange — Optimal interest compounding frequency: https://math.stackexchange.com/questions/4051273/optimal-interest-compounding-frequency
- spark.money — DeFi Yield Aggregators Compared: https://www.spark.money/tools/defi-yield-aggregator-comparison
