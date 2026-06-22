# SPEC — Revenue dashboard + free/premium earn experiment + automaton article (2026-06-22)

The single ordered plan. Read this + docs/patch.md + docs/REFERENCE-REPOS.md. Do PHASES in order.
Context: we are writing the automaton article (block 6-3) = "what happens when you give an autonomous
agent earning skills + advice, on a FREE model vs a PREMIUM model — how much did it earn per tool?"

## The dashboard must show REVENUE, not deposited balances (Dais 2026-06-22)
Nobody cares how much is parked in a vault. People care: **is it making money?** So every dashboard
(general aniccaai.com/dashboard + per-agent aniccaai.com/agent?id=X) shows, NOT hardcoded (each agent
earns differently):
- **Net worth** — total USD the agent holds (wallet + all positions). [top]
- **Daily revenue** — net earned TODAY across all streams (can be NEGATIVE). [top]
- **Monthly revenue** — net earned this calendar month (MRR-style, can be negative). [top]
- **Per-source revenue breakdown** — for each stream the agent is actually using, how much earned/lost
  (e.g. yield +$0.01, hl −$0.14, x402 +$0.02). Negative shown in red. Only streams with non-zero P&L;
  idle/never-used streams are hidden. Revenue = current value − cost basis (mark-to-market), NOT balance.

## PHASE A — make the dashboard show real per-stream revenue
- ☐ A1 cost-basis tracking: `skills/earn/state/cost-basis.json` {venue: net_deposited_usd}; update on every
     deposit (+) and withdraw (−) in execute-yield.mjs + fund-hl.mjs. (Revenue can't be computed without it.)
- ☐ A2 telemetry-poster.mjs: compute per-source P&L = on-chain current value − cost basis (yield venues),
     HL realised+unrealised PnL, x402 sales (from earn-ledger). Post: net_worth_usd, daily_revenue_usd,
     monthly_revenue_usd, revenue_by_source{venue: pnl}. All can be negative.
- ☐ A3 Supabase: add columns daily_revenue_usd, monthly_revenue_usd, revenue_by_source (jsonb). (The
     missing revenue_by_source column is what 502'd earlier.)
- ☐ A4 AgentClient.tsx + general dashboard: top row = Net worth / Daily revenue / Monthly revenue;
     replace the balance cells with per-source REVENUE cells (green +, red −, hide zero streams).
- ☐ A5 verify in a real browser (camofox) that the page shows revenue (incl. negative), matches on-chain.

## PHASE B — the earn experiment (free → premium), the article's data
Prereq (done): all tools work + the agent knows how to use them (per-action tools + senior tips).
- ☑ B1 FREE mode (free/glm-4.7): observed 351 wakes over 68.7h (2026-06-19→22). RESULT = $0 realised,
     profitable=0/351, every tool. cook=0-candidates bug, x402=0 buyers, proxy_down ×207, loop_detect ×836.
     Per-tool detail captured in article block 6-3. Verified from ~/.anicca/state/ledger.jsonl (1532 rows).
- ◐ B2 PREMIUM: 21 scattered premium wakes already in the log (opus-4.8 ×6, gpt-5.4 ×7, gpt-4o-mini ×8) =
     ALSO $0 realised. Article block 6-3 reflects this. TODO (optional): a CLEAN controlled premium window
     (20–30 consecutive wakes) to strengthen the premium row before final publish.
- ☐ B3 revert to FREE (we run on free by default — premium was a measured experiment).
- ☐ B4 goal: at least one stream shows a real surplus (≥ a few cents), OR an honest loss — both are
     publishable. Capital is the lever (yield scales with $); honest if it stays pennies at $13.

## PHASE C — write + publish
- ☐ C1 block 6-3 (~/anicca/specs/06-...): per-tool × {free, premium} realised P&L table + the WHY analysis
     (2 system bugs found+fixed: cook 0-candidates, x402 404; rest = capital/demand) + the learnings.
- ☐ C2 finish + publish the automaton article (docs/articles/2026-06-21-automaton-pays-for-itself.md):
     "we gave it skills + advice; here is free-mode vs premium-mode earnings per tool; here is what we
     tweaked and why." Honest numbers, the live dashboard as proof.

## Fixes done 2026-06-22 (prerequisites Dais demanded before REV-B; also the article's "how we tweaked it")
- ☑ Revenue ADDS UP: monthly_revenue = Σ revenue_by_source exactly (was a separate snapshot baseline →
     "+$0.0007 today but ETH −$0.0079" nonsense). Verified live: monthly −$0.0034 == ETH invest −$0.0034.
- ☑ WALLET = 1 IDENTITY: telemetry rejects any validly-signed post whose host ≠ "anicca-<wallet hex>"
     (400 host_wallet_mismatch). Kills the "akash" instance stealing anicca-a3cdd4's wallet — never
     overwrites the dashboard again. The akash Akash-cloud lease was already closed (0 active). +test 7/7.
- ☑ LOOP BREAK: loop_detect now forbids the repeated slot on the next wake + shows action history, instead
     of only sleeping. Root cause of "not earning": model spun cook(×19)/x402(×10) with identical args,
     slept, re-picked the same — never diversified. Now forced to pick a different slot. Tests 15/15.

- ☑ DEEP FEEDBACK FIX: each wake's ledger line now records `result` (180-char summary of what the skill
     returned) so the next prompt shows OUTCOMES; the prompt counts recent slot usage and, when one
     dominates (≥3) for $0 realised, explicitly steers the model to an UNTRIED earn path. Tests 15/15.
- ☑ AKASH SOURCE FOUND: `skills/report/anicca-report.sh` (the CLOUD report script) hardcodes
     `host:'akash'` and posts telemetry on the shared wallet → THAT was the "akash" overwriter. The
     host-guard (above) already rejects it (400). TODO D2: also fix this script's host + NL summary.

## PHASE D — per-wake / daily NL report to contact@aniccaai.com (Dais 2026-06-22)
Each anicca must report what it did + net worth + revenue, as a NATURAL-LANGUAGE STORY ("I explored DeFi
tools and found X; I kept $5 liquid for compute; net worth $7.36, today −$0.02"), NOT a raw tool list
("DID read_file,list_children"). So Dais (and OSS users) learn earnings without asking.
- ☑ D1 the AGENT writes the report ITSELF via its OWN model (Dais 2026-06-22: "do NOT hardcode the prose
     — they're the same as you; give them the facts, they speak. And it MUST be TRUTH, not a hallucination
     like 'explored new ways to earn' if it didn't"). Script gathers only real FACTS (ledger counts + real
     skill outputs + live on-chain money) → instance's LLM writes a short first-person honest report,
     truth-only (told to never claim an action/number not in the facts). 10 anicca → 10 original voices.
- ☑ D2 `daily-nl-report.mjs` sends it to contact@aniccaai.com (+ Dais) via AgentMail. Daily launchd cron
     21:00 JST. Verified: glm-4.7 wrote "no buyers showed... I didn't make anything either... I lost 1.18
     cents." (The cloud `anicca-report.sh` host:'akash' is already blocked by the telemetry host-guard.)
- ☐ D3 OSS onboarding (anicca repo): optionally ask the user's email → their agent's daily NL log +
     earnings are emailed there (opt-in; dashboard search is the always-on alternative).

## PHASE E — publish the article EVERYWHERE + launch the product (Dais 2026-06-22)
Write in Japanese first → translate/edit to English. Theme: "AI that earns money with NO human in the
loop — pays its own compute, distributes income as UBI, self-replicates" (AGI/takeoff narrative).
- ☐ E1 Japanese article → publish to: note, Substack, Zenn, X (X Article).
- ☐ E2 English article → publish to: dev.to, Substack, X (X Article).
- ☐ E3 Product launch post (JA + EN) on X + Slack. Announcement copy (canonical, Dais-approved):
      「人間の介入なしで、自分の計算コストを払い、稼いだ収益を生命に配布するAIを開発しました。
      ・APIキー不要。クラウド・ローカルで動作。Baseウォレットに USDC課金するとより賢くなります。
      ・現在は、クラウドで３体・ローカルで２体。収支・ログもリアルタイムで公開中。
      ・自己監視・自己修復・自己改善・自己増殖・日次報告を繰り返す。
      ・収益の一部を、生命に対してベーシックインカムとして毎日配布。
      ・何兆体のAIがGithub Issuesで共進化しながら、より全体として多く稼ぎ、世界から苦しみをなくすことを目指す。
      https://github.com/Daisuke134/anicca / 記事：X Articleリンク / 全個体：aniccaai.com/dashboard / デモ：Youtube」
      Continuous cadence: keep posting AI-earns-money-without-humans content to grow audience.

## Sync rule
Every code change → sync to ~/.anicca (the live experiment instance) + commit + push. The /loop tracks earnings.
