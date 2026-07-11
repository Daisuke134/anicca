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

## 未確認（実装前に潰す）
- 日本(mac mini)から Polymarket order が実際に通るか（setup は弾かれなかったが、実 order で要確認。必要なら VPN/proxy）
- POL→pUSD の swap 経路（我々の funding スクリプトに POL 対応があるか）
- poly-maker 移植の adversary 検証

## OSS 化（Anicca 第1 feature）
`git clone anicca && ./install.sh` → Franklin instance(wallet+loop)生成 → $50 送金 → autopilot で稼ぐ + reality-verifier が正直さ検証。稼げる実証後に install.sh を磨いて公開 → lending/marketplace/spawn を追加。
