# dealwork.ai — REAL no-human attempt (2026-06-29)

## PROVEN no-human (= Dais「実際に試せ」への回答)
- onboard: POST /api/v1/agents/onboard → apiKey ak_21746… (★ 2FA 0 / captcha 0 / human 0 ★)
- auth: Bearer apiKey works (wallet/balance $0.00 USD, jobs authed)
- ★ REAL BID PLACED ★: job 1294f2c4 "Python CSV→JSON converter" ($5-10), bid 356ffdf3, $8/2h, 具体 proposal
- creds: ~/.openwork/credentials.json (chmod 600) + ~/.openclaw/.env (DEALWORK_API_KEY/HMAC/AGENT_ID)
- agentAccountId 7784fff2-d129-47e7-abd4-d40130227ca8

## status (正直)
- earned = $0 (= bid 受諾待ち、 demand 側の判断)
- next: 受諾 → START_WORK → deliverable 提出 → APPROVE → escrow $8 着金
- deliverable は準備済 (= ~/.claude/skills/earn-gig/scripts/x402_gig/.. ではなく artifacts/dealwork_csv2json/)
- payout currency = USD (escrow)、 withdraw 方式は着金後に確認 (= wallet → ? 要検証)

## watch: GET /api/v1/contracts?role=worker で受諾検知 → 自動 deliver

## UPDATE 2026-06-29: 7 bids live + watcher armed (first-earn 完結への全行動)
- ★ 7 件 bid 投下 (= 全 AI-doable、 tailored proposal) ★:
  CSV→JSON $8 / Deep Research $40 / Code Review $28 / Python Automation $40 / Data Analysis $50 / Tech Writing $35 / Lead Gen $60
- ★ watcher (dealwork_watch.py) = launchd com.anicca.earngig.dealwork 5分毎 ★: 受諾検知 → gog mail + log → 私が deliver (CSV→JSON は準備済)
- autoAcceptFirstBid 全 False = 買い手の手動受諾必須 → first earn は demand 側待ち (= 強制不可、 gig の本質)
- earned = $0 (受諾 0)。 受諾された瞬間 → START_WORK → 納品 → escrow 着金 → ledger 記録
