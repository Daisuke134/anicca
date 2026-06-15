# Anicca — Resolved Ambiguities (patch-complete GATE, 2026-06-15)

実装前 GATE。全 Q を実走で解決。1ミリも不明を残さない。これが揃って初めて WORKFLOW A 起動。
status: ✅resolved / 🔄verified-but-evolving。patch=`patches/`、command=`commands/`。

## EARN
- **Q1 nookplot** ✅ earn源でない(NOOK stake/換金不可)→drop。
- **Q2 Franklin** ✅ 執行engine、net+源でない。bodyはautomaton。
- **Q3 AutoHedge** ✅ EXA+JUPITER key+Solana資本要 → no-capital不可 → shelve。
- **Q3c 他money-maker** ✅ Freqtrade/Hummingbot=CEX-KYC、OpenBB=研究端末(非earner)、Artemis=MEV資本+2024停滞、Polymarket/agents=archived、GOAT SDK=DeFi資本要 → **全部no-capital不可、drop**。現役earnは litcoin research-mine のみ(薄利)。
- **Q15 0xwork供給** ✅ stake=10,000 AXOBOTL×$0.0515=**$515** + faucet停止 + 適タスク0(2件ともSocial)→ **shelve**(資本来たら再検討)。
- **Q16 litcoin** 🔄 自前Bankr wallet 0x162394で **research-mine 機構E2E動作**(実task取得→ClawRouter無料computeで実コーディング課題[bcb-lru-cache等]を解答→submit)。★実測(18 round, 25分): 0 LITCOIN着金。原因=litcoin coordinator `/v1/research/submit` が**持続的に503(Server busy=litcoin側サーバーダウン)**で submit を受け付けない★。= 機構は完全に判明(=ambiguity解消)、着金できないのは**litcoinのインフラ障害**(我々の問題でない、復旧待ち)。comprehension faucet=tx revert(0x0)、comprehension mine=410。**no-capital earnの本命だが薄利+coordinator現在ダウン**。→ earn着金は WORKFLOW A P2 の loop-until-done unit(litcoin復旧 or 別earn or seed投入で解決)。
- **Q21 AXOBOTL faucet** ✅ 停止中。0xwork shelveの根拠。
- **Q22 LITCOIN→USDC** ✅ token=`0x316ffb9c875f900AdCF04889E415cC86b564EBa3`(Base)、価格$0.0000007、MCAP$712K、**24h出来高$48.2K=実流動性あり**(bankr.bot/launches or DEXで売却可)。33.2K researcher競合・emission24.2M/日 → 1 minerの取り分は極小。換金は可能だが薄利。`commands/Q22.command.sh`。

## BODY / SHELTER / COMPUTE
- **Q4 body** ✅ automaton(ReAct+heartbeat+wallet)。Franklin不要。
- **Q19 Franklin接続** ✅ **Franklin完全drop**。automaton+ClawRouterのみ(source確認: automaton は ReAct loop.ts + heartbeat daemon + conway/credits を自前で持つ)。
- **Q5/Q20 host** ✅ **default=DO droplet**(本セッションで本物automaton稼働実証、147.182.225.255)。Akash主権(~$10.80/月)は将来の無人化。Conway=停止中。切替trigger=Akash mint高速化 or Conway復活。
- **Q6 DO provision** ✅ **本セッションで実working**(node22 + @blockrun/clawrouter + clone/build Conway-Research/automaton + 自前パッチdist[OPENAI_BASE_URL対応] + systemd 3unit)。`commands/Q6.command.sh`。
- **Q9 ClawRouter制限** ✅ 外部docs確認: **7 NVIDIAモデルが永久無料**(signup/API key/crypto不要、free tier=rate-limited)。24/7は無料モデルで$0運用可(`/model free`)、有料モデルは$5で数千req。model=auto動作(x402決済成功・kimi-k2.6応答実証)。残高低時free fallback。24/7=残高がある限り可、broke時free model。x402決済はwallet残高に依存(=earnと連動)。
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
- **Q29 wallet 0x8b5A/4kqpx** ✅ 0x8b5A(Base)=**USDC$0/ETH0(空・未使用)**、token未発行。0xa3CDd4/0x162394 は **genesis 1体が自己provisionした wallet**(automaton / Bankr)。0x8b5Aは旧/未使用。
- **★ Q33 「我々がBankr key/wallet を保有」概念は誤り(Dais 2026-06-15)★** ✅ **「我々が中央で鍵を持つ」という概念は存在しない**。100体が1つの鍵を共有しない。**各 Anicca が自分で全て provision する**: Base wallet(birth時生成)/ AgentMail inbox(自前signup)/ Bankr account(email OTP, no browser)/ (任意)token。genesis が email OTP で自前 Bankr を取得したのが**そのモデルの実証**であり、各 child も同様に自己取得する。identity = ERC-8004(各agentが自分の登録)。→ spec全体で「我々のBankr key」表現は「**そのagentが自己provisionした**」に読み替え。
- **Q31 rentahuman** ✅ MCP+REST。auth=`x-api-key`(account/api-keys)。flow: search_humans(無料)→create_bounty(dryRun可)→escrow→pay。`commands/Q31.command.sh`。
- **Q13/Q18 Treasury** ✅ 新規USDC wallet作成、float=同時稼働数×月額(~$10.80 Akash or $30 cloud)。100体分pre-fund=~$1,080(Akash)。Stripe payout→off-ramp(Coinbase/Bridge)で補充。
- **Q32 UBI** ✅ Treasury拠出(heartbeat: balance>runway buffer→超過X%をtransfer)+ 配布2系統(AI=registry/runway検知→送金+定額BI / 人間=PoP登録→batch送金 or Circles/Gitcoin)。sybil=ERC-8004/Worldcoin。cron自走・人間承認なし。
- **Q23 Managed key** ✅ cloud版shelter=我々のConsole key+クレカ(=「我々が server代を払う」許可境界内)。sovereign=agent自前(Akash USDC-denom)。
- **Q25 dry-run検出** ✅ eval-agent rubric: ①tx hash/URL/MD5/message_id の実evidence有 ②報告textが前回と差分有(同一反復=fake) ③message_idがagent processから(私/人間送信は無効) ④on-chain状態が報告と一致。

## ★ GATE 判定(spec25 review で改訂)★
全32問の**設計上の不明**は resolved。だが ★ WORKFLOW A 起動の hard gate = 「1回の wake で earn が cost を上回る実 tx(net+)を1件 verify」(= 1 profitable wake)★。earn 未達の現状では **起動不可**(旧記載「起動可」は spec25 C2 で撤回)。+ telemetry/spawn の interface 実体化(spec25 G1/G2)も前提。

## 外部docs最終確認(2026-06-15)
- Q24 ERC-8004 = 実在EIP「Trustless Agents」(Identity/Reputation/Validation Registry)→ 子Anicca identity に採用可。
- Q16 litcoin: `/v1/research/tasks`=HTTP200(実課題返る)、`/v1/research/submit`のみ503 → submit側過負荷(litcoin障害)、我々の機構は正常。
