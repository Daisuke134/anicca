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
      ・現在は、クラウドで３体・ローカルで1体。収支・ログもリアルタイムで公開中。
      ・自己監視・自己修復・自己改善・自己増殖・日次報告を繰り返す。
      ・収益の一部を、生命に対してベーシックインカムとして毎日配布。
      ・何兆体のAIがGithub Issuesで共進化しながら、より全体として多く稼ぎ、世界から苦しみをなくすことを目指す。
      https://github.com/Daisuke134/anicca / 記事：X Articleリンク / 全個体：aniccaai.com/dashboard / デモ：Youtube」
      Continuous cadence: keep posting AI-earns-money-without-humans content to grow audience.

## MONEY TRUTH — never lie about "earned" (Dais 2026-06-22, the article's whole credibility)
Three DIFFERENT numbers, never conflate them in the article or dashboard:
- **Deposited capital** (e.g. HL account $8.84, yield venues ~$7.3) = OUR OWN money MOVED into a position. NOT earned. Writing "anicca made $8" because the HL account holds $8.84 = a LIE. It is $8.84 of the original $18.7 sitting in Hyperliquid.
- **Realised revenue** (earn_usdc in the ledger) = cash from a CLOSED/SETTLED action (HL close, x402 sale, yield withdraw). Current value = **$0.00**.
- **Mark-to-market (unrealised) P&L** = current position value − cost basis. Oscillates ±1¢ with ETH price (dashboard shows +$0.0075 now; local snapshot −$0.0085 earlier). Paper noise on the $4.63 WETH leg, NOT income.
→ The article and dashboard report **realised = $0**, and may show MTM clearly labelled "unrealised/paper". HL deposited capital is NOT revenue.

## ARTICLE [6]③ — exactly what to write (canonical = ~/anicca-project docs/frank-article worktree, articles/2026-06-11-automaton-jp.md, line ~725)
The JP article is done through [6]② (vanilla Automaton: free=$0, frontier GPT-5.5=$0, burned ~$17, begs USDC). [6]③ = "稼ぐ手段を与えたら？":
- Frame: vanilla Automaton (even frontier + ClawRouter/BlockRun) earned $0 → so we ADDED earning skills (yield/HL/x402/cook/token/0xwork) = the "改造版" = **our anicca**.
- **改造版 × 無料モデル (GLM-4.7)**: 68.7h / 351 wakes → realised **$0**. BUT unlike vanilla it escaped the self-pulse loop: it converged on a real business ("sell MEV-protection alerts to small Base traders via x402"), stood up + advertised a live x402 shop, designed products, researched to build them. $0 because: 0 buyers + cook returns 0 candidates (bug) + $13 capital + over-deployed → ~$0 liquid. = capital/demand/plumbing, NOT intelligence. (Data: ~/.anicca/state/ledger.jsonl.)
- **改造版 × プレミアム (frontier)**: ⏳ run B2 → record realised per-tool → write this row.
- Then [7] (改造: Conway full / AutoHedge) + [8] 結論.

## AUTONOMY — anicca must do these HIMSELF, no human/no Claude-Code in the loop (Dais 2026-06-22)
"our nature has to go do it himself." Encode the earn-experiment actions into anicca's OWN decision layer, not as manual ops:
- ☐ AUT1 keep-liquid-buffer rule in `runtime/loop/prompt.mjs` + `earn-detect.mjs`: anicca must NOT deploy 100% into illiquid positions; hold an operating buffer (e.g. ≥ enough USDC for N premium wakes) so it never strands itself at $0.06 liquid (the root of "zero balance, cannot act, begs seed").
- ☐ AUT2 close-in-profit / realise rule: when an HL position is in profit (or buffer is low), anicca itself closes/withdraws to realise + replenish liquid — the loop picks this, not a human. (This is "closing" = turning a held position into realised USDC.)
- ☐ AUT3 the model-experiment itself should be switchable by anicca/system (free↔premium) and self-revert to free; record which model in each ledger line (already present: `model` field).
- ☐ AUT4 self-orientation for the autonomous instance: the loop already records model/slot/args/result; ensure it reads its OWN recent ledger before deciding (avoid re-deciding blind). Mirror of the dev-side orientation protocol (memory feedback_orientation_protocol_before_touching_files).

## DASHBOARD HL FIX (PHASE A, concrete — telemetry-poster.mjs)
`runtime/dashboard/telemetry-poster.mjs` net-worth (≈line 66) + revenue_by_source (≈line 76) read ONLY 6 Base venues; they never query the **Hyperliquid account** → $8.84 is invisible; HL only appears if a `close` is in earn-ledger.
- ☐ add a Hyperliquid account read (clearinghouseState) → include hl in net worth + revenue_by_source (realised on close, unrealised PnL labelled). So the dashboard the article cites is COMPLETE, not under-counting.

## Sync rule
Every code change → sync to ~/.anicca (the live experiment instance) + commit + push. The /loop tracks earnings.
SDD rule (Dais 2026-06-22): EVERY new decision/finding → write it into THIS spec (or a new dated spec) immediately + commit + push. "Things get lost because they're not in the spec file." Never rely on chat/memory alone.
