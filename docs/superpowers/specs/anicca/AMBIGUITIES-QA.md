# Anicca — Ambiguities Q&A (実装前に1ミリも残さず潰す)
各 Q は実走で検証して A を埋める。status: ✅解決 / 🔄検証中 / ⬜未着手。SSOT。

## EARN(最重要・差別化の核心)— money-maker群を1つずつ実走+ログ
### Q1 nookplot は実際にUSDCを自律で稼げるか → A: ✅(否)
- 実走: `nookplot mine`。credits経済=USDCで"買う"側。mineはNOOK(token)だが①先にNOOKをstake必須②epoch+Merkle claim③solverに本物LLM key必要(ClawRouter不可・base-url指定不可)。NOOK→USDC直接換金は未確認。
- 結論: nookplotは"参加に払う"場所。自律USDC収入源ではない。earn候補から降格。

### Q2 Franklin は稼ぐか → A: ✅(否)
- README実確認: Franklinは「USDCを使って仕事する執行エンジン」。trading/imagegenも支出。net+の源ではない。bodyの候補ではあるが earner ではない。

### Q3 AutoHedge は自律でUSDCを稼げるか → A: 🔄(有望・配線継続中)
- 実走: pip install成功 + ★ClawRouter(gpt-4o-mini)で駆動成功★。swarm稼働(Director→Sentiment handoff成功)。
- 停止: exa_search が EXA_API_KEY 無しでToolExecutionError。
- 必要: ①LLM=ClawRouter✅ ②EXA_API_KEY(web検索,無料枠) ③JUPITER_API_KEY(価格,無料枠) ④Solana wallet+USDC資本(=実取引,損失リスク)
- 次: Exa/Jupiter無料キー取得→完全分析(資本0)→少額実トレード。trading=分散(勝/負)。

### Q3b OpenAlice は → A: ⬜(次に実走)
- 既知: ⭐5216, ローカル稼働, ★取引に人間承認必須★(自律性に難), broker口座要。要実走確認。

### Q3c awesome-money-maker の他候補(Freqtrade/Hummingbot/FinRL/GOAT SDK/nof1/予測市場/DeFi yield/airdrop/content/lead-gen) → ⬜
- 1つずつ「無料で動くか/口座資本不要か/USDC着金するか」を実走しログ(MONEYMAKER-EVAL.md)。

## BODY / SHELTER / REPORT / DISTRIBUTION
### Q4 Franklinを24/7自律earnループにできるか → A: ✅(否→body方針確定)
- 実走: `franklin daemon`=決済proxyのみ。`start -p`=1タスクで終了。★Franklinは24/7自律earnループを持たない★。
- 結論: ★body = 自前の軽量heartbeatループ(cron駆動 core/loop.mjs)★。think(ClawRouter)→earn skills→report を回す。automatonが一例。Franklinはwallet/proxy部品として任意流用。
### Q5 DO dropletにbilling有効化が要るか → A: ✅
- 実走: account status=active, droplet_limit=10, email_verified=true → ★dropletを作れる★。サーバ代=唯一許可される人間介入(我々が持つ)。
### Q6 DO cloud-init(node→repo→clawrouter→loop)正確なスクリプト → ⬜
### Q7 AgentMail spawn毎の新inbox作成API → A: 🔄(上限判明)
- 実走: `POST /v0/inboxes` → ★『Inbox limit exceeded』(無料枠上限)★。
- 結論: 多数Anicca用に ①AgentMail有料プラン ②各Aniccaが自前signup ③catch-all独自ドメイン のいずれか。要決定。
### Q8 report "earned"の出所 → A: ✅ earn=DeFi yield(skills/earn/defi-yield.mjs)→ earn-ledger.jsonl に供給/利息を記録 → reportが読む。
### Q9 ClawRouter無料枠レート制限(429観測)で24/7足りるか → 🔄
### Q10 sutando の相互扶助/issue駆動skill → A: ✅
- 実体確認(~/research/pipecat/sutando): ★proactive-loop(夜間自律でPR出し自己改善)+ bot2bot-post(agent間通信=相互扶助)+ agent-registry + task-orphan-check★。実績『50日600+PR自律』。
- 結論: Aniccaのcolony相互扶助+自己進化に proactive-loop/bot2bot-post/agent-registry を流用。LLM backendはClawRouter(USDC)に差し替え。
### Q11 aniccaai.com/install の中身 → A: ✅ ★クラウド専用Webページ(誰もshell叩かない)★。OSSはGitHub repo側。
### Q12 Stripe webhook→spawn backend の場所/コード → ⬜
### Q13 Treasury(USDC在庫wallet) → A: ✅(新規作成)
- 現状: 存在しない → ★我々が新規USDC walletを作成しfloatを入れる★(cloud subscriber spawn用)。Stripe payout→off-ramp(Coinbase/Bridge)で補充。在庫≈同時稼働数×$月額。
### Q14 /me dashboard のデータ源 → ⬜

## EARN / CLOUD / BODY 第2波(Dais 2026-06-14 列挙、未解消)
### Q15 0xworkのタスク供給量 → ⬜ 今2件(Social)。Research/Code/Data枠が安定供給されるか未測定。
### Q16 litcoinのstake最低額 → ⬜ Spark tierにUSDCいくら要るか未測定。
### Q17 Akash pre-fund額 → ⬜ server代を何ヶ月分先払いすれば安全か(top-up頻度との兼合い)。
### Q18 Treasuryの原資 → ⬜ pre-fund/top-upのUSDCは初期我々→いつearnが追い越すか。
### Q19 automaton survival-loop ⊗ Franklin 接続方式 → ⬜ Franklinのloopに「飢餓圧」をprompt注入かwrapperか。
### Q20 cloud host最終選択 → 🔄 Akash主権(1分,pre-fund要)優勢 vs DO(即,我々token=human-loop)。pre-fund運用が前提条件。
### Q21 0xwork register の AXOBOTL auto-faucet → ⬜ faucet枯れてないか/gas(Base ETH)がagent walletにあるか。
### Q22 litcoin $LITCOIN→USDC換金経路 → ⬜ Base DEXに十分な流動性があるか。
### Q23 Managed Wallet APIキーの位置づけ → ⬜ 我々Console口座+クレカ=cloud保険だが「human-loop」境界の整理。
### Q24 self-spawnの身元/法的 → ⬜ 子Aniccaのwallet/identity無人発行をどう正当化(個人情報汚染懸念)。
### Q25 dry-run検出器の閾値 → ⬜ 「同一報告の反復」をどう機械判定するか。
### Q26 heartbeat実行環境の鍵管理 → ⬜ cloud上でagent wallet PRIVATE_KEYをどう安全保持(漏洩=資金喪失)。
### Q27 クラウド版の最終価格 → 🔄 Dais口頭で $30/$40/$50 と揺れ。canonicalコピーは書面の $30/mo 採用。最終要確定。
