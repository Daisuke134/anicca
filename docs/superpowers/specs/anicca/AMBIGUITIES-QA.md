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
### Q4 Franklinを24/7自律earnループにできるか → ⬜(daemon/serve実走)
### Q5 DO dropletにbilling有効化が要るか → ⬜
### Q6 DO cloud-init(node→repo→clawrouter→loop)正確なスクリプト → ⬜
### Q7 AgentMail spawn毎の新inbox作成API → ⬜
### Q8 report "earned"の出所=earn-ledger(Q3に依存) → ⬜
### Q9 ClawRouter無料枠レート制限(429観測)で24/7足りるか → 🔄
### Q10 sutando の相互扶助/issue駆動の具体skill → ⬜(clone+実走)
### Q11 aniccaai.com/install の中身 → A: ✅ ★クラウド専用Webページ(誰もshell叩かない)★。OSSはGitHub repo側。
### Q12 Stripe webhook→spawn backend の場所/コード → ⬜
### Q13 Treasury(USDC在庫wallet)は存在/誰が入金 → ⬜
### Q14 /me dashboard のデータ源 → ⬜
