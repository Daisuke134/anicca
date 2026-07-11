# 検証済み EARN recipe — 実 clone+run で裏取り(2026-07-12)

「なぜ稼げないか」の答え + 「どう稼ぐか」の recipe。全部 subagent が実際に clone/run/live-API で検証。これが Anicca 第1 feature「どんな AI も $50 で毎日稼ぐ」の spec。

## なぜ今まで稼げなかったか（3日間の疑問の確定答え）
**小口($1-5) × 方向性 bet(edge無し) × idle 運転コスト → 手数料/gas に負けて確実にゼロへ減衰。**
- $1-5 は Polymarket 手数料(0.75-1.8%)・HL 最小注文($10)に構造的に負ける（裏取り済）。
- sol は SOL 1銘柄の 2% momentum だけ見て永遠に WAIT。pm は naked 方向性で -$8.6。hl は churn。
- 待つだけで x402 推論/gas が残高を食う（Franklin $12.99→$3.44 を trade ゼロで）。

## ★ 検証済み recipe（engine 別、証拠付き）★

### 1. Polymarket = 最優先（最も再現性が高く、最速で「毎日」収益）
- **repo: `warproxxx/poly-maker`**（★1387, MIT, 単独作者, 2026-07-09更新）
- **戦略**: maker-only 二枚建て quoting（fair-value=microprice+EWMA flow / inventory-skew / vol・toxicity 動的スプレッド / regime machine 5状態 / daily-loss kill-switch）
- **edge の源泉 = 構造的**: Polymarket 公式 **liquidity-rewards**（対象市場に $52-257/日 が配分、in-band 二枚建てで按分取得）+ maker-rebate。**「板に居るだけで報酬」= 方向を当てる必要がない。**
- **最小資本**: $50-100（実 profile: base_size $22-100/注文, q_max $100-200, CLOB 最小5株）
- **検証実績**: `uv run pytest` **111 passed** / `polymaker scan` で**実 Gamma API から1101件の実市場取得**（ライブ確認）
- **我々への適用 = copy+tweak**: poly-maker の ①async WS 板(`marketdata/orderbook.py`)②EWMA estimators ③regime machine ④risk manager を我々の pm skill へ移植。**post-only WS 駆動なら naked fill が構造的に起きない**（我々の REST polling + no_naked bolt-on の根本治療）。MIT なので流用可。

### 2. HL = 次点（構造的 delta-neutral）
- **repo: `hummingbot/hummingbot`**(★19,115) の `scripts/v2_funding_rate_arb.py`
- **戦略**: HL perp vs 別取引所 perp の **funding rate 差分**を捕捉（両建て=方向性なし、利益=funding 差額のみ）
- **最小資本**: $50-100（各レグ$25-50、低レバ5-10x。HL 最小 notional $10、taker 0.025%）
- **注意**: Binance は KYC 必須で使えない → **non-KYC perp DEX(dYdX v4 / Backpack / Lighter、wallet 接続のみ)** × HL のペアで組む
- **我々への適用**: hl skill の方向性トレンドフォローを**格下げ**、funding-arb を新主戦略に。

### 3. Solana = 一旦休止（copy-trade は数学的に負け筋）
- copy-trading は **structural loser**（実データ: Jito 最速 0.5秒でも勝率46%、1.0秒28%、2秒以上は全サイズで負け確定。追随者は必ず不利価格で約定＝leader/MEV への alpha 移転）。出典: Kurnovskii "Pump.fun Copy-Trading Feasibility" 2025-12。
- **アクション**: 新規 copy-trade 実装しない。既存 momentum-gate(WAIT できる設計)は維持。拡張するなら copy でなく LP/funding 中立系を別途調査。

## 実装順（1つずつ、main=私が build、adversary=Sonnet で検証）
1. **pm に poly-maker のコアを移植**（WS板+regime+risk manager）= 最速で毎日収益、edge=公式報酬
2. **HL funding-arb を non-KYC perp DEX × HL で実装**
3. **Solana 休止**（別 edge 調査まで）
4. 利益は**引き出さず複利** → $50→$100→$500 で規模拡大

## 資金（Dais が native で送る）
| 誰 | チェーン | native | 送金先 | 額 |
|---|---|---|---|---|
| claude-p(Polymarket/HL) | Polygon | POL | `0x810f6d61f7606deee2657d3083e150a222bc29c5` | $60-100(750-1255 POL) → 私が pUSD に swap |
| Franklin(Solana) | Solana | SOL | `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9` | $60-100(0.77-1.28 SOL) ※solは休止判定なので後回し可 |

Polymarket deposit(pUSD)= `0x4c176db1cd976E570fD35E92e0F6559e1Ba515Aa`（BlockRun setup 済、creds ready、region block 無し）。

## ★★★ 法的 PIVOT（2026-07-12 調査で判明、recipe を上書き）★★★
**Polymarket を日本の物理拠点(mac mini)から回すのは違法リスク。** 日本は geoblock 対象(frontend close-only)、**刑法185条 賭博罪は user 本人にも刑事責任がありうる**(法律事務所 So&Sato)。VPN は ToS 違反(凍結)かつ賭博罪を消さない=二重リスク。bitbank は Polymarket 紐付け口座凍結、警察庁「海外賭博への日本居住者参加は犯罪」。→ **poly-maker が技術的にベストでも、Japan mac mini では Polymarket を本番稼働させない**（Dais「社会に殺されたくない」に忠実）。
**日本拠点からの合法性ランク**: Solana spot(合法・ただ crypto) > HL perp(グレー、金商法だが**賭博でない**) > Polymarket(賭博罪リスク=最悪)。
**新・主戦略 = HL funding-arb**（構造的 edge かつ賭博でない）。Polymarket をやるなら海外法人/海外居住の実行主体経由に設計変更。
送金ルール: Dais は **native SOL(Solana)のみ**送る。USDC/POL を頼まない。→ memory feedback_dais_funds_native_sol_only_and_polymarket_japan_illegal。

## 未確認（実装前に潰す）
- HL funding-arb を $25-30 の小資本で回せるか（BP は $50-100。小さく始めて機構実証→scale）
- 届いた SOL → HL(USDC on Arbitrum/等) の bridge/swap 経路
- POL→pUSD の swap 経路（我々の funding スクリプトに POL 対応があるか）
- poly-maker 移植の adversary 検証

## OSS 化（Anicca 第1 feature）
`git clone anicca && ./install.sh` → Franklin instance(wallet+loop)生成 → $50 送金 → autopilot で稼ぐ + reality-verifier が正直さ検証。稼げる実証後に install.sh を磨いて公開 → lending/marketplace/spawn を追加。

## ★★★ 決定的 FINDING (2026-07-12, 一次情報検索で確定) — $5-30 は net profit 構造的に不可能 ★★★
Dais 要求の深掘り検索(firecrawl, Polymarket公式docs+実gamma API)の結論:
- **Polymarket 報酬 MM**: 高報酬市場は rewardsMinSize 200-1000株($40-1000+)で参加不可。薄い市場でも報酬は流動性シェア按分→$9 vs 数百万$板=シェア≈0→日次<$1=**$0払い**(help.polymarket.com「$1未満不払い」)。出典 docs.polymarket.com/market-makers/liquidity-rewards の S(v,s)=((v-s)/v)^2·b, Qnormal=Qmin/ΣQmin。
- **HL funding-arb**: 手数料超えは $5,000-10,000 notional から。$5-30 不成立。
- poly-maker README 自身「利益保証なし・損あり」。
- **∴ 稼げない root cause = 戦略/検索不足でなく『資本が floor 未満』。** floor: Polymarket $数百-数千 / HL $5-10k。
- 報酬MM移植(reward_mm/, 31/31 pass, 実API 690市場)は**完成し動くが、$9 では報酬シェア≈0 で $0**。capital 育てば有効。→ worktree feature/pm-reward-mm(未merge)、live禁止(§法的PIVOT: 日本からPolymarket=賭博罪リスク)。
- **正直な帰結**: 現$30では意味ある net profit を出す戦略は一次情報上存在しない。recipe「$10→複利」は現capitalでevidence非支持。次の設計判断が要る(capital調達 or 別収益源 or handover条件見直し)。

## ★★★ 訂正(2026-07-12 own-eyes, Dais指摘で発覚) — 「$5-30構造的に稼げない」は"報酬型MM"限定の話。directional/bundle-arbは既に小口で勝っている ★★★
上のFINDINGは**Polymarket公式liquidity-rewardsプログラム**への参加可否だけを検証したもので、bundle_arb.py/market_maker.py/pick.pyが使う**directional・maker-bundle戦略には当てはまらない**。実データで反証済み：
- **2026-07-04 実ログ**: 残高$12.79からmarket_maker.pyが `NO 5@0.23` (5シェア×$0.23=$1.15)等、複数の$1〜$3.65の小口レッグを発注し、同日中に$10・$6.79・$5で複数redeem。**7戦7勝、realized純益+$10.02**（Polymarket公式APIの`/activity`で直接検証、own-eyes 2026-07-12）。
- **Polymarketの本当の最小単位は「5シェア」であって「$5」ではない。** シェア価格が安い(＝市場が偏っている)markets を見つければ、5シェアは$1未満でも発注できる。現在の`budget_shares<5`/`MIN_SIZE=5`ゲートはPolymarket CLOB自体の実制約(コード側の恣意的な上限ではない)だが、**株価の高い(五分五分の)市場ばかりスキャンしていると結果的に$5弱を要求してしまう**——これが現在$1.35でHOLDしている理由。
- **訂正**: 「$1-5 は手数料に構造的に負ける」(6-9行目)は**報酬型MMには真、directional/bundle-arbには誤**。今後の主戦略は「安い(偏った)株価の市場を優先スキャンする」ロジック強化 → Task #3(anicca-project TaskList)参照。
- Franklinの"$12.99→$3.44をtradeゼロで"目減りの内訳、正体確定(2026-07-12 own-eyes+コード読解): 直近10txすべてで、取引の有無に関係なく毎wake同一の外部wallet(`AQqnMFBwGZEoti85aTVRy8XYpKrho7GaMDx9ZB3CEeKA`)へ約$0.0095が引かれている(on-chain確認、10件平均$0.00953)。**正体 = BlockRunのx402ツール課金**。`@blockrun/franklin-trading/dist/tools/blockrun.js`のsignPayment()が確認: 「free/glm-4.7」は**LLM推論だけ**が無料で、sol-tradeが毎wake呼ぶ市場データ/TradingSignal系の"tool"呼び出しはBlockRun側endpointが動的に指定する`recipient`へx402で個別課金される(Aniccaのコードにハードコードされた額ではない)。earn-ledgerのcost_usdcには記録されていない(ledgerがLLM/skill層のcostしか見ておらず、tool呼び出し自体のx402課金を素通りしている)。→ 対策候補: (a)ツール呼び出し頻度を減らす、(b)このcostをearn-ledgerに記録するよう配線、(c)無料で足りるならtool呼び出し自体を止める。
