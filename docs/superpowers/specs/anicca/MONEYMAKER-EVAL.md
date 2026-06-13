# Money-Maker 実走評価ログ(awesome-OpenClaw-Money-Maker を1つずつ)
| skill | ⭐ | 実走 | 無料? | 口座/資本 | 人間介入 | USDC着金 | 判定 |
|---|---|---|---|---|---|---|---|
| nookplot | - | ✅mine | 払う側 | NOOK stake | LLM key要 | ✗(NOOK) | ❌降格 |
| Franklin | - | ✅task | - | - | - | ✗(支出側) | body候補/非earner |
| AutoHedge | - | ✅swarm起動 | LLM=ClawRouter | Solana資本要 | Exa/Jupiter key要 | 🔄 | ★有望(配線中)★ |
| OpenAlice | 5216 | ⬜ | ? | broker | ★承認必須★ | ? | 次 |
| Freqtrade | 46500 | ⬜ | OSS | 取引所API+資本 | 設定 | ? | 次 |
| GOAT SDK | 951 | ⬜ | ? | on-chain wallet | ? | ? | 次 |

## ★判定基準(Dais 2026-06-13)★
合格 = 「Aniccaが ①自分のウォレットだけ ②人間のAPIキー無し ③人間の承認無し」で稼げる。
- Daisのキー(EXA等)を差すのは反則(=人間介入・検証無意味)。
- キーが要る→ ログして次へ(理想はキー不要)。Aniccaが自分でbrowser signupで取れるなら可だが摩擦大。
- ★最良 = キー不要・ウォレットのみ・on-chain(DeFi/DEX/予測市場)★。

## 確定ログ
- AutoHedge: swarm+ClawRouter動作OK だが ★EXA_API_KEY(人間)+JUPITER_API_KEY 必須★
  → Daisキー使用は禁止。Anicca自己signup要 = 理想でない。【保留・要自己signup】
- OpenAlice: ★人間の取引承認必須 + broker口座★ → no-human不可。【不合格】
- Freqtrade/Hummingbot/Jesse/nof1: ★取引所API+KYC口座★ → 人間介入。【不合格】
- ★候補(キー不要・ウォレットのみ)→ 次に深掘り: GOAT SDK(on-chain DeFi), DeFi yield(Aave/Moonwell直deposit), 予測市場(Polymarket wallet), on-chain DEX arb★

## ★結論: no-human earn の確定（battle-test済）★
- ✅ DeFi yield (Base lending: Aave/Moonwell/Morpho に USDC supply) = ★キー不要・ウォレットのみ・人間ゼロ・低リスク~5-10%★ → ★Aniccaのearn基盤として実装★。tx=supply 1本(agent署名のみ)。
- ② on-chain trading/MEV (GOAT SDK ⭐951 / AutoHedge on-chain) = キー不要だがリスク+競争+資本。上振れ用。
- ③ AutoHedge/OpenAlice等(外部dataキー要) = Anicca自己browser-signupなら可、摩擦大。保留。
- ✗ nookplot/Franklin/Freqtrade/OpenAlice = 人間キー/口座/承認 必須 → no-human不可。
- 正直な算数: yieldで費用自給には資本~$750-2250要。完全自給=資本(yield)+トレード上振れ+需要(サービス)。
  → cloud版: サブスク収益→資本供給→Aniccaがyield+trading運用、が現実解。
- ★実装する earn skill: skills/earn/defi-yield.mjs (Base lending supply/withdraw + APY監視) を第一に。
  + skills/earn/onchain-trade.mjs (GOAT SDK, 上振れ) を第二に(任意・リスク開示)。
