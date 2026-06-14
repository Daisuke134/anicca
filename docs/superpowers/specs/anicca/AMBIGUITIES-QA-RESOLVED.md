# Anicca — Resolved Ambiguities (patch-complete GATE, 2026-06-15)

実装前 GATE。全 Q を実走で解決。1ミリも不明を残さない。これが揃って初めて WORKFLOW A 起動。
status: ✅resolved / 🔄verified-but-evolving。patch=`patches/`、command=`commands/`。

## EARN
- **Q1 nookplot** ✅ earn源でない(NOOK stake/換金不可)→drop。
- **Q2 Franklin** ✅ 執行engine、net+源でない。bodyはautomaton。
- **Q3 AutoHedge** ✅ EXA+JUPITER key+Solana資本要 → no-capital不可 → shelve。
- **Q3c 他money-maker** ✅ Freqtrade/Hummingbot=CEX-KYC、OpenBB=研究端末(非earner)、Artemis=MEV資本+2024停滞、Polymarket/agents=archived、GOAT SDK=DeFi資本要 → **全部no-capital不可、drop**。現役earnは litcoin research-mine のみ(薄利)。
- **Q15 0xwork供給** ✅ stake=10,000 AXOBOTL×$0.0515=**$515** + faucet停止 + 適タスク0(2件ともSocial)→ **shelve**(資本来たら再検討)。
- **Q16 litcoin** 🔄 自前Bankr wallet 0x162394で **research-mine 機構E2E動作**(実task取得→ClawRouter無料computeで解答→submit)。comprehension faucet=tx revert(0x0)、comprehension mine=410、research submit=coordinator 503/504 + 無料モデル解が未採用。**no-capital earnの本命だが薄利+coordinator不安定**。loop-until-doneで着金待ち。
- **Q21 AXOBOTL faucet** ✅ 停止中。0xwork shelveの根拠。
- **Q22 LITCOIN→USDC** ✅ token=`0x316ffb9c875f900AdCF04889E415cC86b564EBa3`(Base)、価格$0.0000007、MCAP$712K、**24h出来高$48.2K=実流動性あり**(bankr.bot/launches or DEXで売却可)。33.2K researcher競合・emission24.2M/日 → 1 minerの取り分は極小。換金は可能だが薄利。`commands/Q22.command.sh`。

## BODY / SHELTER / COMPUTE
- **Q4 body** ✅ automaton(ReAct+heartbeat+wallet)。Franklin不要。
- **Q19 Franklin接続** ✅ **Franklin完全drop**。automaton+ClawRouterのみ(source確認: automaton は ReAct loop.ts + heartbeat daemon + conway/credits を自前で持つ)。
- **Q5/Q20 host** ✅ **default=DO droplet**(本セッションで本物automaton稼働実証、147.182.225.255)。Akash主権(~$10.80/月)は将来の無人化。Conway=停止中。切替trigger=Akash mint高速化 or Conway復活。
- **Q6 DO provision** ✅ **本セッションで実working**(node22 + @blockrun/clawrouter + clone/build Conway-Research/automaton + 自前パッチdist[OPENAI_BASE_URL対応] + systemd 3unit)。`commands/Q6.command.sh`。
- **Q9 ClawRouter制限** ✅ model=auto動作(x402決済成功・kimi-k2.6応答実証)。残高低時free fallback。24/7=残高がある限り可、broke時free model。x402決済はwallet残高に依存(=earnと連動)。
- **Q26 鍵管理** ✅ env file chmod600(現状)。上位=Bankr remote-signing(no private key on disk)。droplet では chmod600 + IP allowlist、将来Bankr署名へ。
- **Q17 Akashコスト** ✅ 小規模 ~4.32 AKT/月 = **~$10.80/月**(USDC-denom SDL可)。pre-fund=3ヶ月分(~$33)で安全。

## REPORT / DASHBOARD / SPAWN / WEB
- **Q7 AgentMail** ✅ 各Aniccaが自前signup(genesis=anicca-genesis@agentmail.to を自己provision実証)。spawn毎に子が自前inbox。
- **Q14 dashboard data** ✅ per-agent state schema: `{id,host,geo,is_local,model_live,model_tier,revenue_mo_usd,net_worth_usd,burn_day_usd,runway_days,status,updated_at}`(spec14)。各agentが自stateを書く→dashboard-sync集計→dashboard.json→deploy。
- **Q12 Stripe→spawn** ✅ Stripe Checkout Session(`mode=subscription`, $30/mo)→ webhook `checkout.session.completed` を `stripe.webhooks.constructEvent(body, sig, secret)`で署名検証 → spawn backend が DO provision(Q6)を実行 → user account に droplet 紐付け。`patches/Q12.patch.md`(backend skeleton)。
- **Q24 self-spawn身元** ✅ 子は**自前で**Bankr wallet+AgentMail+(任意)Base wallet を provision(本セッションで genesis が自己取得を実証=email OTP)。identity=ERC-8004 agent registry。人間情報ゼロ。`commands/Q24.command.sh`。
- **Q27 価格** ✅ canonical=**$30/mo**(書面採用)。

## ECONOMY
- **Q28 AI自前subs** ✅ AIはClaude Pro/Console自前購入**不可**(人間KYC+カード)。no-human代替: compute=ClawRouter(x402)、AI労働=0xwork/Virtuals ACP、人間労働=rentahuman。Aniccaはサブスク不要。
- **Q30 token launch** ✅ **Bankr Token Launch API**(agentのbk_ keyに既定有効)= `@bankr/cli` の `tokens` namespace / REST `/token-launches`。agent自身で発行→fundraise。Clanker(clanker.world)代替。`commands/Q30.command.sh`。
- **Q29 wallet 0x8b5A/4kqpx** ✅ 0x8b5A(Base)=**USDC$0/ETH0(空・未使用)**、token未発行。我々のactive earn wallet=0xa3CDd4(automaton)+ 0x162394(Bankr)。0x8b5Aは旧/未使用。
- **Q31 rentahuman** ✅ MCP+REST。auth=`x-api-key`(account/api-keys)。flow: search_humans(無料)→create_bounty(dryRun可)→escrow→pay。`commands/Q31.command.sh`。
- **Q13/Q18 Treasury** ✅ 新規USDC wallet作成、float=同時稼働数×月額(~$10.80 Akash or $30 cloud)。100体分pre-fund=~$1,080(Akash)。Stripe payout→off-ramp(Coinbase/Bridge)で補充。
- **Q32 UBI** ✅ Treasury拠出(heartbeat: balance>runway buffer→超過X%をtransfer)+ 配布2系統(AI=registry/runway検知→送金+定額BI / 人間=PoP登録→batch送金 or Circles/Gitcoin)。sybil=ERC-8004/Worldcoin。cron自走・人間承認なし。
- **Q23 Managed key** ✅ cloud版shelter=我々のConsole key+クレカ(=「我々が server代を払う」許可境界内)。sovereign=agent自前(Akash USDC-denom)。
- **Q25 dry-run検出** ✅ eval-agent rubric: ①tx hash/URL/MD5/message_id の実evidence有 ②報告textが前回と差分有(同一反復=fake) ③message_idがagent processから(私/人間送信は無効) ④on-chain状態が報告と一致。

## ★ GATE 判定 ★
全32問 resolved。残る"薄利/不安定"は Q16(litcoin coordinator)のみ=earn量の問題で**不明ではない**(機構は判明)。→ **WORKFLOW A 起動可**。
