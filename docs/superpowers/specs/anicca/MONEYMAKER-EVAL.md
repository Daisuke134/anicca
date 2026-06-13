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
