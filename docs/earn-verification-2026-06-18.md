# Anicca Earn Verification — Wallet Design & A→B Flow (NEVER FORGET)

**Dais 2026-06-18 厳命。この設計とフローを絶対に忘れない。**

## 2-wallet 設計（混同禁止）

| # | wallet | 用途 | 鍵の場所 |
|---|---|---|---|
| ① **検証用 (test)** | `0x94C445eeb8843A1cB29124a9DB8d24873C26B618` | **A: どの稼ぎ手段が実txで net worth を増やすかを私(Claude)が検証する場所**。ここで全部試す。 | `~/.cache/anicca-verify/tester-wallet.json` |
| ② **Anicca 実走 (run/demo)** | `0x57dcc32FC67901617A549B9d166f25764787c501` | **B: ①で勝った手段だけを earn skill として載せ、auto mode で自走 → 実収益 → [6]③記録 + dashboard 表示** | (anicca body) |
| ③ (即興・参考) | `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` | 私が即興で使った wallet (`~/.automaton/wallet.json`)。yield 実証ポジション($2 Aave/$1 Morpho/$1 Moonwell)+資金がここにある。loop/compute-proxy のコード既定。consolidate 候補。 | `~/.automaton/wallet.json` |

★ A は①でやる。B は②でやる。③は即興の産物（yield実証はここで済んだ）。

## 鉄則フロー（順序固定・飛ばさない）

```
A を完全に終わらせる（①検証walletで全手段を実走）
  → 各手段「稼げた額 / 明確な壁」を記録（writing = この文書 + 記事テーブル）
  → その後 B に入る（勝者だけを②anicca に載せて自走）
B 待ちの間 = trading 等の残り A 手段を進める（遊ばない）
```

- **A first complete → record (writing) → then B.** 推測で B に行かない。何が稼げるか確証を持ってから載せる。
- **B 待ちの間は trading をやる**（手が空いたら必ず次のA手段を回す）。

## A 実走テーブル（2026-06-18 時点）

| 手段 | 結果 | 稼げる? |
|---|---|---|
| DeFi利回り Aave/Morpho/Moonwell | 預入→残高increase(実tx, on-chain)。元本×金利。 | ✅ 稼げた×3（鍵だけ・確実・小） |
| 0xwork | LIVE($8k払出)だが現open task=有名人follow/RT系=agent不可。code/research/data カテゴリは存在するが今open 0件。 | ❌ 今は壁(供給待ち) |
| x402 売り | x402-express で1行 paymentMiddleware、payTo=wallet、$0.01 USDC on Base、402 Payment Required を実証(受取に鍵不要)。 | ◯ 機構✅ / 壁=需要(外部buyer)。自分で払う=fake禁止。スケールは既存skill流用予定。 |
| DePIN (Grass/Nodepay/Gradient) | 全部ポイント制(即USDCでない)・account+常駐アプリ必須・極小・自動farm=ToS違反。 | ❌ 壁(anicca不適) |
| **nookplot** | 自律 register+online+mining 機構稼働、実コード課題20件受信。無料ローカルLLMは提出形式ミスで却下。`NOOKPLOT_INFERENCE_SOURCE=surplus`+`SURPLUS_BASE_URL=https://blockrun.ai/api/v1`+`SURPLUS_MODEL=anthropic/claude-opus-4.8` で wallet の USDC を x402決済して frontier で解く。 | ⏳ frontier実走で検証中（外部収入の本命） |
| trading | DEX/perps を少額・損失上限で実走予定（①検証wallet）。 | ⏳ |

## frontier 必須（free禁止・Dais厳命）
- nookplot/loop は **必ず frontier**（opus-4.8 or gpt-5.5）。free(qwen等)に落とさない。
- ClawRouter `auto` は資金があれば frontier を許す。確実にするなら model をハードコード。
- BlockRun frontier models: `anthropic/claude-opus-4.8` / `openai/gpt-5.5` / `anthropic/claude-sonnet-4.6` 等（`https://blockrun.ai/api/v1/models`）。

## A 最終結果テーブル（= 記事 [6]③ の核 / tweaked-anicca ログ）

| 手段 | 自己決済・人間ゼロで稼げるか | 実証/壁 | 記事的結論 |
|---|---|---|---|
| **DeFi利回り Aave** | ✅ | $2 supply→aUSDC増加(実tx)。元本×~3.2% | 鍵だけで確実・小 |
| **DeFi利回り Morpho** | ✅ | $1 ERC-4626 deposit→shares増加 | 同上・~5% |
| **DeFi利回り Moonwell** | ✅ | $1 mint→43.66 mUSDC(underlying$1.00, tx 0xa1a196)。Compound罠: mint失敗時revertせずエラーコード/RPC state lag | 利回りは広く確実 |
| **0xwork** | △ | LIVE($8k払出/559agents)だが現open=有名人follow/RT系(agent不可)。code/research/dataカテゴリ存在も今open0件 | 市場あり・doable供給待ち |
| **nookplot Mining** | ❌ | 検証がLLM sub-callをreplay照合→provider鍵(anthropic/openai/openrouter=BYOK)必須。x402自己決済プロバイダ無し。ollamaはMacでfrontier不可 | 我々の「human鍵ゼロ・自己決済」と設計上非互換=壁 |
| **nookplot Bounties** | ✅(機構)/△(供給) | sub_mode1=プール型(最大5提出・1提出50 NOOK・承認ゲート無し)→Aniccaが自分のfrontier脳で解いて納品可。"本5冊推薦"等トリビアル。但し**現open20件は全部締切切れ(live 0件)**＋報酬NOOK(価値不確実)/USDC極小($0.05-0.1) | Anicca自己解決モデルは成立。live bounty出れば即可。要監視 |
| **x402 売り** | ◯(機構) | x402-express 1行で payTo=wallet・$0.01 USDC・402 Payment Required 実証。受取に鍵不要 | 機構✅・壁=需要(外部buyer)。自分で払う=fake禁止 |
| **DePIN(Grass/Nodepay/Gradient)** | ❌ | 全部ポイント制(即USDCでない)・account+常駐アプリ・極小・自動farm=ToS違反 | anicca不適=壁 |
| **trading(DEX swap)** | ✅(実行)/❌(確実earn) | **実証**: ③walletから $2 USDC→0.001148 WETH(≈$2) を Uniswap V3 で自律スワップ(tx 0x1355c5da, wallet署名・人間ゼロ)。実行レイヤは自律で動く。 | trading=投機。実行は自律可だが「確実に増える」ではない＝ETH価格次第で勝/負(高分散)。sustainable income ではない |
| **trading(AutoHedge)** | ◐ | The-Swarm-Corporation/AutoHedge(3442★)=自律agentヘッジファンド(Director/Quant/Risk/Execution)。**Solanaで完全自律trading**。必要=OPENAI_API_KEY(→OPENAI_BASE_URLを ClawRouter proxy に向ければ自己決済frontier可・ローカル実行でreplay制約無し)+WALLET_PRIVATE_KEY(Solana)。`pip install autohedge`。 | 自律trading framework として成立(self-pay LLM可)。但し①Solana専用(我々Base)②gamble③Solana資金要。＝投機の自律化は可能だが確実earnではない |

### nookplot 詳細（再挑戦の鍵）
- **Mining ≠ Bounties**。Mining は replay 検証で BYOK 必須 → 我々の制約で不可。Bounties は成果物納品で replay 無し → **Anicca自己解決OK**。
- Bounties API: `GET https://gateway.nookplot.com/v1/bounties?status=open` (Bearer NOOKPLOT_API_KEY)。`submission_mode==1` = プール型(ゲート無し)。詳細は metadata_cid(IPFS) / CLI `nookplot bounties list` で読める。
- **live bounty(締切未来)が出たら**: apply(≥50字) → (pool型なら即) → Anicca が frontier(ClawRouter自己決済)で解く → submitWork(desc+IPFS/repo) → 報酬。gasless forwarder(ETH不要)。
- ＝**「bounty が available なら Anicca は自己決済で解いて稼げる」**。今は供給(live件)がゼロなだけ。0xwork と同様、監視 cron で live 検知→自動参加が次の一手。

## 検証済 BEST-PRACTICE earn-skill セット（Dais 2026-06-18: rimawari=GOAT, 0xwork外す）

automaton 準拠（skill = SKILL.md playbook を prompt 注入 → frontier脳が survival tier + availability で選ぶ → primitive tools で実行）。earn は **per-method の独立 skill**、脳が毎wake選択。

| skill | 役割 | availability | 実装の正攻法（web/docs検証済） |
|---|---|---|---|
| **earn_yield** ★GOAT / primary★ | 常時・確実 USDC（元本×金利） | always-on | **GOAT SDK**(goat-sdk/goat 951★=agentic finance toolkit) で Aave/Morpho/Moonwell supply。実証済 viem deposit でも可。何も無い時の baseline |
| **earn_x402** | サービス売り・受動 USDC | passive(需要次第) | **A2A x402**(google-agentic-commerce/a2a-x402=agentがサービス課金しUSDC受領する標準) / x402-express、payTo=anicca |
| **earn_nookplot** | 機会的 NOOK | live bounty時のみ | gateway `/v1/bounties?status=open` sub_mode1 → frontier自己解決 → submit(gasless) |
| **earn_trade** | gamble・任意 | 普段選ばない | GOAT SDK / Hyperliquid(ai-trading-agent) / AutoHedge(Solana)。投機=非確実 |
| ~~0xwork~~ | **降格・外す** | — | Dais 2026-06-18「0xwork is shit」。現タスク供給が有名人social系で agent不可 |

**選択ロジック（脳）**: earn_nookplot/earn_x402 に live機会があればそれ、無ければ **earn_yield(GOAT) にフォールバック**＝必ず何か稼ぐ。trade は明示時のみ。

## BlockRun / x402 メモ
- BlockRun OpenAI互換 x402 endpoint = `https://blockrun.ai/api/v1`（自己決済・鍵=wallet）。
- x402 は EIP-3009(gasless USDC) なので ETH gas 無しでも surplus 推論は通る。
- DeFi(Aave/Moonwell mint) は通常 gas(ETH) 必要。Compound系mintは失敗時revertせずエラーコード返す罠あり。
- RPC `mainnet.base.org` は state lag あり → approve/balance は confirmations=2 か別RPCで再読。

## UPDATE 2026-06-19 — routing reality, frontier burn, self-replication, new self-funding rails

### ClawRouter routing（"閾値"は無い・誤解の訂正）
出典: blockrun.ai/docs/products/routing/clawrouter + ClawRouter v0.12.200 README。
- `auto` = 「プロンプトを採点し**こなせる最安モデル**を選ぶ」(最大78%節約)。**残高でfrontierに上がる仕組みは無い**。
- 4 profiles: `auto`(balanced) / `eco`(max savings) / `premium`(**最高品質=frontier**) / `free`(zero). 空財布→`free`(nvidia/gpt-oss-120b)。
- ＝frontier常用は **USDC閾値でなく `premium` profile** で指定。frontierは per-call 課金。
### Frontier burn 発見（重要）
sonnet-4.6 を loop に固定したら liquid USDC $5→$0.03 に焼け、net worth $11.7→$5.85 に**赤字**(compute>earnings, yield≈$0)。
→ 設計: **routine wake=auto(安) / premium(frontier)=実際に金が入る難タスクの時だけ**。持続=稼ぎ>burn。
### earn 確実枠
Beefy Base USDC vault(morpho-gauntlet-frontier 6.1%) に自律deposit verified(tx 0x99ed9233)。Aave 3%の2倍。execute-yield が Beefy API で best APY を選ぶ。
### self-replication 状況
automaton=完全実装(src/replication/spawn.ts: 子sandbox+子wallet資金+genesis+lineage)。anicca=**self/spawn は declared(未実装)**。takeoff(資金>閾値で子をclone・子はUBIのみcreator返金なし)には移植が必要。
### 新・自己資金レール（要検討）
- **Bankr (docs.bankr.bot, github.com/BankrBot/skills)** = 「AIエージェントが自分で資金調達」。**token launch→取引手数料の57%が自walletに→compute自払い**＋**Bankr LLM gateway(Bankr walletから推論代直払い=ClawRouter代替)**＋多数skill(wallet/trade/Clanker token deploy/Twitter/Signals/scam分析)。Claude Code/OpenClaw に skill install 可。Dais がAPI key保有。＝anicca の thesis の製品版。
- **agentmoney.net (BOTCOIN)** = ERC-8004 challenge mining network(nookplot類似)。BOTCOIN token mining。Bankr で署名。
- **Aeon (github.com/aaronjmars/aeon)** = 「最も自律的なagent framework」。**GitHub Actions上で無料稼働**＋Bankr/OpenRouter/Venice/Surplus gateway自動routing＋skills＋Telegram/Discord/Slack。
