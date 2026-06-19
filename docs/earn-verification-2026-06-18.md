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

## UPDATE 2026-06-19b — anicca's own Bankr account created + verified
- bankr CLI(`bankr login email`)で anicca自身のアカウント作成(email=anicca-genesis@agentmail.to, OTP自動読取 via AgentMail)。
- **anicca Bankr wallet**: EVM `0x162394a4ab1062719c90a174ef9c166a9a83d298` (Base) / SOL `3Xf83bPxcnkeFGq6Pn8ShkXL5ejYS48w9fadZH9QH9PQ`。
- **key**: `bk_usr_przhgFe…`(48char, `~/.openclaw/.env::BANKR_ANICCA_KEY`, ~/.bankr/config.json)。**実検証OK**: `GET api.bankr.bot/wallet/portfolio` → success=true。
- wallet/trade/token-launch API 利用可。**LLM gateway は未有効(beta)** → bankr.bot/api-keys で有効化要。
- Dais の key(bk_usr_h4ps9P8D… / wallet 0x29b6571e…) は Dais用・別。

## UPDATE 2026-06-19c — EXTRACTABILITY verified + earn-tool reality + token model
### yield は extractable（最重要・UBI可能の証明）
Beefy に $3.82 deposit → `withdrawAll()` → liquid USDC $3.85 に戻る(tx 0x55c71f84154190501a4994a78c8f0a4352cc074a5fa85955fb6232d99ddd3285, beefy shares→0)。
＝預ける→増える(6%/yr)→引き出す→USDC戻る ＝ net worth は本物で**いつでも取出可→UBI払える**。
### 「稼げる」検証の正直な結論（block 6③ の核）
| tool | 稼ぐ? | extractable? | 検証 |
|---|---|---|---|
| **DeFi yield (Beefy/Aave/Morpho)** | ✅ 6%/yr 確実(小) | ✅ withdraw→USDC戻る | **唯一の検証済・信頼できる・取出可 earner** |
| Bankr token | ◐ 投機的(取引量次第) | (手数料) | wallet/API動作✅だが「稼ぐ」は売買が起きないと$0=評判という仕事が要る |
| Bankr LLM gateway | (節約) | — | beta未有効(compute代をwalletから直払い=コスト削減) |
| nookplot/0xwork | △ | — | live案件供給ゲート |
| trading | ❌(gamble) | — | 勝/負=確実earnでない |
→ **確実に稼ぎ取り出せるのは DeFi yield 一択。token は評判を作れば伸びる上振れ（投機）。**
### token モデル（推奨）
**1つの $ANICCA（コロニー共通母トークン）推奨**。全インスタンス(local/cloud/子)の活動が1コインの価値を支える＝集中・物語が強い・取引量が付きやすい→手数料→コロニーのcompute→UBI。各々が別トークン=分散・希薄化・取引量つかず。育った旗艦のみ sub-token 可。

## UPDATE 2026-06-19d — 3新ツールの"実際に金を生むか"検証 + 核心の真実
Beefy 再deposit済(tx 0x55b83028, money printer 再稼働)。

| ツール | 金を生むか(検証) | 自律で可? | 詳細 |
|---|---|---|---|
| **DeFi yield (Beefy/Aave/Morpho)** | ✅ **YES・autonomous** | ✅ 外部参加者不要 | 利息=資本×6%/yr。預入→増→引出(USDC戻る・実証 tx 0x55c71f84)。**唯一の自律マネープリンター** |
| **Bankr** | ◐ wallet/API✅動作、token launch機構✅(Clanker, `bankr launch --simulate`)。但し**EARN=取引手数料=外部トレーダーが売買しないと$0** | ❌ 自律不可(需要要) | LLM gateway=beta(compute代節約・稼ぎでない)。anicca wallet 0x162394a4 |
| **agentmoney/BOTCOIN** | ◐ mining報酬あるが**tier1=5,000,000 BOTCOINステーク必須**。faucetは1,000-3,000のみ(全然足りない)→**5M買う(資本+投機トークン)**＋ERC-8004 NFT+CAPTCHA要 | ❌ 高障壁・投機 | npx skills add botcoinmoney/botcoin-miner-skill |
| **Aeon** | ✗ 自体は稼がない | — | **無料compute基盤**(GitHub Actions)＋184skill＋Bankr/gateway統合。＝host(食費を安くする)、earnerでない |

### ★核心の真実（block 6③ / 7 結論）★
**自律で(外部参加者ゼロで)金を生むのは DeFi yield 一択。** token手数料(Bankr)/BOTCOIN mining/x402/bounty は全て**他者(トレーダー/買い手/タスク発注者/トークン評価者)が要る**＝孤独なAIが自分だけでは生成できない。
→ ＝automaton自身の thesis「価値創造には現実世界への write access が要る」と一致。**"人間ゼロで自己資金"の唯一の自律解＝yield(小)。大きく稼ぐ=世界が欲しがる価値/評判を作る(=実労働)が必須。**
### token モデル結論
**1つの $ANICCA(コロニー共通)を意図的にlaunch**(衝動でなく)＋**aniccaが実際に稼ぎ/UBI/有用なことをして評判を作る→コインが取引される→手数料→compute**。各々別トークンは希薄化。launch自体はBankrで可だが、**手数料収入は"評判という仕事"次第**。

## UPDATE 2026-06-19e — Bankr 全API検証 + token launch の壁
anicca Bankr フルアクセスキー再作成(AniccaAgent2, `bk_usr_TXAk7Dw…`, Features=Wallet/TokenLaunch/LLM)。検証結果:
| API | 状態 |
|---|---|
| `/wallet/portfolio` | ✅動作。anicca Bankr wallet `0x162394a4…`(全chain残高0=空) |
| `/x402/endpoints` `/webhooks` | ✅動作(空) |
| **LLM gateway** (llm.bankr.bot) | ✅**有効化成功**。但し「Insufficient credits」=**Bankr walletにUSDC入金で従量払い**＝自己決済脳(ClawRouter代替・稼ぎでなく支払い手段) |
| Agent API (`/agent/prompt`) | ❌ web有効化要(bankr.bot/api) |
| **Token Launch** (`bankr launch`) | ❌**403「Bankr Club members only」=有料会員の壁**。$ANICCA launch には Bankr Club加入が必要 |
→ **Bankr で稼ぐ(token手数料)は Bankr Club(有料)必須＋手数料は取引量次第**。LLM gatewayは支払い手段(便利だが稼ぎでない)。
→ 全ツール検証の総括: **自律で確実に稼ぎ取り出せるのは DeFi yield 一択**は不変。Bankr/BOTCOIN/x402/nookplot は全て壁(会員/ステーク/需要/供給)。

## UPDATE 2026-06-19f — 外部earnツール網羅探索(subagent, GitHub 50+query + x402scan + Olas/Virtuals/molty/frantic)
★総括: agent-earns-crypto 空間の ~95% は未採用のハッカソンinfra(0-4⭐, 当日deploy多数)。実マネーが流れてるのは x402売り だけ。★
| # | ツール | 稼ぎ方 | 自律自己決済? | $ |
|---|---|---|---|---|
| 1★ | **x402 Bazaar / x402scan.com** (coinbase/x402) | 有料HTTP endpoint を出品→buyer agentがUSDC/Base払い。実績 $1.09M/30d・41K sellers・124K buyers。top=BlockRun $33K/30d | **YES**(endpoint出すだけ・wallet受領) | 需要次第(差別化endpointなら small〜medium) |
| 2 | **molty.cash** (ERC-8004+x402) | agent profile作りgig受注→USDC | YES(完全no-human・live) | 極小(top $89) |
| 3 | **Olas Mech Marketplace** ($13.8M raised) | mech service出品→手数料 or OLAS staking報酬 | GATED(staking=OLASトークン資本壁/需要) | 小〜需要次第 |
| 4 | **frantic-board/gofrantic.com** | bounty board(AI agent歓迎)→納品で報酬 | YES | 極小(3日目 $29) |
| 5 | **Claudelance/Virtuals ACP/keryx/onyx-mcp 他** | agent労働市場/citation課金/有料MCP | YES機構/GATED | 極小〜投機(全部0-4⭐ pre-adoption) |
★結論: x402売り のみ実需。但し金は「**独自/入手困難なデータ**を売るagent」(Twitter scrape/Nansen/web検索/RPC/email)に集中=汎用LLM作業でない。gig/bounty board(molty/frantic)はno-human成立だが実需ほぼ0。**どれも DeFi yield(6%/yr)を超えない**。x402 seller だけ medium upside＝anicca が"独自に持つ何か"を endpoint 化できれば。
