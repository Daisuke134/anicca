# Capafy Self-Improving Revenue Loop Design

**Date:** 2026-08-01  
**Status:** Design approved in direction; implementation not started by this spec  
**Objective:** Turn the existing Capafy Builder and Marketer into one autonomous, self-healing, self-improving revenue system that reports verified outcomes and links in natural language.

## 1. Current verified baseline

- Revenue: 1 lifetime order, $9.99 lifetime gross, $8.00 pending seller balance, $0.00 realized payout, $0 MRR.
- Supply: 27 listings online; 31 listings tracked across online, review, rejected, and draft states.
- 2026-08-01 Builder: initial browser identity collision was repaired by the existing self-fixer. `Portfolio Tracker — Daily Position Review` (`agent_id=9480246345`) reached `status=1`, `isConfirmedSkills=1`, `isConfirmedConfigKeys=1`; its verified review URL is `https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review`.
- Instagram: `@capafy.skills10491` is recorded as a calendar-age day-3 warming account with `session_owner=browser`. A durable posting session is not established, so neither health nor ban is proven.
- Marketing execution: the 2026-07-30 and 2026-07-31 passes both timed out at 180 seconds because the multi-step video/post job still uses the short `tool-agent` lane.
- Reporting defect: Telegram reported the Builder failure but did not report the later verified repair and submission. `already_live` currently means the LaunchAgent is loaded, not that a post is live.
- OpenRouter: approximately $4.777 lifetime usage, approximately $20.223 remaining, recent measured increments below $0.001/day, host key capped at $2/day, account key caps totaling $5/day, auto-top-up off.

## 2. Product promise

Capafy operates like an autonomous two-person company:

1. **Builder** discovers demand, selects a commercially valid opportunity, builds and submits one product, verifies the remote state, and learns from sales.
2. **Marketer** receives the verified product event, chooses the best content/channel action, publishes it, verifies a public URL, measures traffic and sales, and learns from results.

The human does not babysit either worker. The human receives concise, natural-language evidence of outcomes, money, repairs, and decisions.

## 3. Recommended architecture

```text
Market Intelligence
  Firecrawl / Crawl4AI / marketplace APIs / GitHub / Context7 docs
                          |
                          v
                  Opportunity Backlog
                          |
             +------------+------------+
             |                         |
             v                         v
      Builder Agent              Marketing Agent
  research/build/price/       content/publish/measure/
  submit/verify/learn         attribute/iterate/learn
             |                         |
             +------------+------------+
                          v
             Shared Revenue Event Ledger
 listings/posts/clicks/orders/MRR/cost/incidents/experiments
                          |
                +---------+---------+
                |                   |
                v                   v
       Telegram Renderer     Public Web Dashboard
```

Telegram is a projection, not the database. Every report is rendered from the same structured, append-only event ledger used by the web dashboard and both agents.

## 4. Responsibility boundaries

### 4.1 Deterministic control plane

Deterministic code owns:

- schedules, leases, timeouts, budgets, retries, idempotency, state transitions, arithmetic, ledgers, URLs, remote-status reads, cost caps, and alert delivery;
- proof that an artifact exists, a URL resolves, a post is public, or a remote field changed;
- starting or resuming a repair and preventing duplicate concurrent work.

It must not decide which niche is attractive, which content angle is persuasive, or whether a new opportunity is meaningfully differentiated.

### 4.2 Agent judgment plane

The models own:

- opportunity selection from observed demand evidence;
- product design and renewal reasoning;
- pricing recommendation within hard unit-economic limits;
- marketing channel, hook, creative, and iteration decisions;
- diagnosis and repair strategy when the deterministic tools return concrete evidence.

Prompts use right-altitude criteria and a small set of canonical examples, not regex-based business judgment or exhaustive if/else instructions.

## 5. Canonical event model

Minimum event types:

- `opportunity.observed`, `opportunity.selected`, `experiment.started`, `experiment.decided`
- `listing.created`, `listing.submitted`, `listing.approved`, `listing.rejected`, `listing.retired`
- `content.created`, `content.published`, `content.measured`
- `account.created`, `account.warmup_completed`, `account.session_ready`, `account.challenge_detected`, `account.replacement_started`
- `order.received`, `subscription.started`, `subscription.cancelled`, `refund.received`, `payout.received`
- `cost.measured`, `cost.breaker_triggered`
- `incident.detected`, `incident.repair_started`, `incident.repaired`, `incident.verified`, `incident.unresolved`

Each event contains:

- stable `event_id`, timestamp, loop, entity type/id, correlation/incident id;
- plain-language summary;
- machine status before/after;
- evidence URLs and local evidence references;
- gross, pending, realized, MRR, cost, and contribution-margin deltas where applicable;
- next owner and next automatic retry time when unresolved.

## 6. Self-healing contract

The terminal state is not “error reported.” The lifecycle is:

```text
detect -> contain -> diagnose -> repair -> re-run -> verify -> report closure
```

Rules:

1. Every incident has one correlation id and one durable owner.
2. A failed primary pass immediately starts or resumes its repair within the same outcome chain.
3. Telegram sends either a verified closure or an unresolved incident with attempted repairs, external blocker, and next retry time.
4. A repair is successful only when the original business observable changes: remote listing state, public post URL, session verification, revenue read, or budget status.
5. Repeating the same ineffective action is prohibited. The agent must inspect new evidence and choose a materially different action.
6. Recovery state survives process death and machine restart.
7. Health is derived from recent successful business outcomes, not merely a loaded scheduler or exit code zero.
8. A watchdog remains silent while healthy and wakes the repair owner when an outcome SLA expires.

Outcome SLAs:

- Builder daily pass: verified terminal state by 10:00 JST.
- Marketing daily pass: verified content/account terminal state by 17:30 JST.
- Sale/payout reconciliation: less than 24 hours stale.
- Incident repair start: within 5 minutes of detection.
- Repair closure report: immediately after verification.

## 7. Self-improvement contract

The loop optimizes verified net revenue, not listing count, content count, or activity.

North-star metric:

```text
net recurring contribution = recognized recurring revenue
                           - marketplace fees
                           - sandbox/compute/model costs
                           - refunds
```

Daily learning cycle:

1. Crawl marketplace demand and competitor changes.
2. Join impressions, detail views, clicks, orders, retention, refunds, and cost by listing.
3. Let the agent explain the strongest observed bottleneck with evidence.
4. Choose one bounded experiment: niche, positioning, price, packaging, landing page, channel, hook, or creative.
5. Pre-register the primary metric, guardrails, sample/time limit, and stop condition.
6. Execute once, measure, and retain or revert based on the pre-registered rule.
7. Feed the result into the next opportunity and marketing decision.

Hard guardrails:

- no demand claim without a source and timestamp;
- no invented proof, credentials, sales, or reach;
- no subscription unless the buyer receives recurring value from recurring input or changing data;
- no hosted-key product without positive worst-case unit economics and a hard per-product cap;
- no scale-up until the end-to-end funnel and attribution are measurable;
- kill or reposition products after a declared evidence threshold rather than letting dead listings accumulate.

## 8. Account lifecycle

The Instagram account state machine is:

```text
needed -> created -> warmup_1 -> warmup_2 -> session_ready
       -> first_noncommercial_post -> reach_measured -> commercial_ready
       -> healthy
```

Failure transitions:

```text
challenge/session failure/verified zero-reach pattern
  -> contained -> replacement_started -> created
```

Calendar age is never called warmup completion. `live` is reserved for a verified public post. `healthy` requires an established session and a recent successful verification. A replacement begins as soon as the terminal failure criterion is verified; it does not wait for the next daily content pass.

## 9. Telegram user experience

### 9.1 Message principles

Every message answers:

1. What happened?
2. What changed in the real world?
3. Where can I open it?
4. How much money did it make or cost?
5. If it failed, what repaired it and how was the repair verified?
6. What happens next without human intervention?

All published skills, articles, videos, Reels, landing pages, and review pages include clickable URLs. Internal paths are never presented as the user's primary evidence.

### 9.2 Scheduled cadence

| Time JST | Report |
|---|---|
| 08:00 | Morning CEO brief: yesterday's gross/net/realized/MRR/cost, funnel, incidents, today's Builder and Marketer objectives. |
| 08:10 | Builder starts silently. |
| On Builder terminal state | Immediate verified listing result with real URL. |
| 09:30 | Consolidated company state after any Builder repair. Replaces the misleading 09:00 goal dump. |
| 11:20-14:20 | Warmup runs silently. Report only a lifecycle transition, terminal failure, or verified replacement. |
| 16:00 | Marketer starts silently. |
| On Marketing terminal state | Immediate content/post result with public URL, media, caption, promoted listing URL, and attribution link. |
| 20:00 | Only if content was published: first performance snapshot with views, clicks, buyers, and interpretation. |
| 23:50 | Daily close: gross, net, pending, realized, MRR, model/tool spend, contribution, experiment result, next automatic action. |

Event-driven immediate reports: order, cancellation, refund, payout, listing approval/rejection, public content, account challenge/replacement, cost breaker, and verified repair closure.

### 9.3 Exact example: morning brief

The examples below are message contracts. Braced values such as `{verified_reel_url}` are runtime fields that must be replaced from a verified event before delivery; the renderer must refuse to send a literal brace token.

> **Capafy — Morning brief, Aug 1**  
> We have 27 skills online, 2 under review, and 1 draft that should be retired. Lifetime sales are 1 order / $9.99 gross. Pending seller balance is $8.00; realized bank payout and MRR are both $0.00. OpenRouter spend since yesterday was $0.000261; the Capafy host key remains capped at $2/day.  
>  
> Yesterday's Instagram pass did not publish: it was killed at the 180-second runner limit. The repair owner is active; no human action is required.  
>  
> Today's Builder target: submit one recurring-input product derived from measured marketplace demand. Today's Marketer target: establish the new account session and publish its first verified non-commercial Reel.  
>  
> Dashboard: https://capafy-skills-daily.netlify.app

### 9.4 Exact example: skill submitted

> **Capafy Builder — New skill submitted and verified**  
> I built **Portfolio Tracker — Daily Position Review** because portfolio tracking is a proven recurring category and the buyer has fresh positions every day.  
>  
> Capafy agent ID: `9480246345`  
> Status: under review  
> Skill package: confirmed  
> Hosted configuration: confirmed  
> Price: $9.99/week, 20 runs, no free trial  
>  
> Open the real Capafy review page:  
> https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review  
>  
> Revenue change: $0.00 today; MRR remains $0.00.  
> Next: I will watch for approval and automatically hand this exact skill to the Marketer when it becomes public.

### 9.5 Exact example: repair closure

> **Capafy incident resolved — no action needed**  
> At 08:14 the Builder could not submit because the Dais browser identity was colliding with the Gig browser. I separated the browser ownership, re-acquired the correct session, resumed the same submission, and verified the remote result.  
>  
> Recovered skill: **Portfolio Tracker — Daily Position Review** (`9480246345`)  
> Verified state: under review; skill/config checkpoints confirmed  
> Evidence: https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review  
>  
> Nothing is waiting on you. The next scheduled action is approval monitoring.

### 9.6 Exact example: Reel published

> **Capafy Marketer — Reel published**  
> I published the first non-commercial Reel for **Portfolio Tracker — Daily Position Review** on `@capafy.skills10491`.  
>  
> Watch the Reel: {verified_reel_url}  
> Open the skill: https://capafy.ai/agent/9480246345  
> Campaign link: https://capafy-skills-daily.netlify.app/go/9480246345?utm_source=instagram&utm_medium=reel&utm_campaign=portfolio-tracker-launch  
>  
> Caption:  
> “Your portfolio changed today. Your old review did not. This skill checks the positions and notes you paste across eight fixed risk and thesis dimensions—without pretending it has live market data.”  
>  
> Current result: public and verified. Views/clicks/buyers will be measured at 20:00. Commercial bio link remains off until reach is proven healthy.

### 9.7 Exact example: sale

> **Capafy sale — real money event**  
> **Portfolio Tracker — Daily Position Review** received a new $9.99 weekly subscription.  
>  
> Skill: https://capafy.ai/agent/9480246345  
> Attributed source: Instagram Reel  
> Source content: {verified_reel_url}  
>  
> Today: 1 order / $9.99 gross  
> Estimated publisher proceeds before model cost: $7.59/week  
> Realized bank payout: unchanged until Capafy pays it  
> MRR run rate added: approximately $43.29 gross  
>  
> I will now increase allocation to this product and test the next creative without changing the winning offer simultaneously.

### 9.8 Exact example: unresolved external blocker

> **Capafy incident remains unresolved — automatic retry scheduled**  
> Instagram returned a platform challenge while establishing the posting session for `@capafy.skills10491`. I stopped retries to avoid worsening the account, preserved the evidence, and started the replacement-account workflow.  
>  
> Attempts completed: session verification, one clean reattach, challenge confirmation.  
> Current containment: no posting or login retries on the affected account.  
> Next automatic action: create the replacement account at {next_retry_time_jst}, then begin the two-successful-warmups lifecycle.  
> Human action required: none. I will send the replacement handle when creation is verified.

## 10. User experience

The owner uses Capafy at three levels:

1. **Telegram:** the daily operating interface. It shows decisions, verified outcomes, links, money, repair closure, and the next autonomous action.
2. **Public web dashboard:** a readable company page showing products, live content, gross/pending/realized revenue, MRR, costs, incidents, experiments, and last update. It is generated from the event ledger and is safe to open source.
3. **Deep evidence:** each Telegram/dashboard item links to the real marketplace listing, public post, campaign URL, or review evidence. Technical logs remain available but are not the normal UX.

The owner does not approve routine choices. Human escalation is reserved for legal consent, unavailable credentials, irreversible financial commitments beyond declared caps, or a platform action that explicitly requires a human.

## 11. Revenue architecture

### 11.1 Product packaging

- Recurring changing input -> subscription.
- Value proportional to records/results/actions -> usage or pay-per-event.
- One completed installation/methodology -> one-time or BYOK download.
- High variable model cost -> BYOK, usage pricing, or hard low cap; never an uncapped flat subscription.

One core capability may be packaged as:

- a Capafy subscription agent;
- an Apify pay-per-event Actor;
- a RapidAPI endpoint;
- a Gumroad/Whop one-time bundle or membership;
- a free GitHub/registry edition that creates discovery and trust.

### 11.2 Path to $10K MRR

At the current Capafy benchmark of approximately $32.9 net per active weekly subscriber per month, $10K requires approximately 304 concurrent subscribers. The plan is not to publish hundreds of weak listings. It is to find two to five category winners and distribute them across compatible marketplaces.

Milestones:

1. **$0 -> $100 MRR:** prove one end-to-end attributed subscription and positive contribution margin.
2. **$100 -> $1K:** find one repeatable niche/offer/channel combination; reach approximately 30 net-equivalent subscribers.
3. **$1K -> $10K:** expand the winning capability across Capafy, Apify, RapidAPI, and direct packaging; reach approximately 304 Capafy-equivalent subscribers or an equivalent mixed revenue portfolio.

Required gates:

- every order attributable to product and source where platform data permits;
- positive worst-case unit economics;
- renewal and churn observable;
- at least one marketing channel with repeatable qualified traffic;
- product portfolio allocation based on net revenue per impression, not intuition.

### 11.3 Path to $10M MRR

$10M MRR cannot credibly come from manually accumulating low-price skills. At $30 ARPU it needs about 333,000 subscribers; at a 20% marketplace take rate it needs $50M monthly GMV; at $10,000/month enterprise ACV it needs 1,000 customers.

The business must change shape:

1. **$10K -> $100K:** productize winning skills into reliable APIs/SaaS and add higher-value business plans.
2. **$100K -> $1M:** sell the proven Skill Selling Agent to other creators and companies; charge subscription plus usage/revenue share.
3. **$1M -> $10M:** become distribution and monetization infrastructure: marketplace adapters, billing, metering, evaluation, security, attribution, and autonomous portfolio management for third parties.

The $10M product is not an individual skill. It is the platform that continuously discovers, builds, distributes, markets, measures, repairs, and improves revenue-producing agent products.

## 12. Remaining implementation backlog

### Execution status

- **Active priority:** P0 — Truthful outcomes and repair closure.
- **Implementation plan:** [`../plans/2026-08-01-capafy-p0-truthful-outcomes.md`](../plans/2026-08-01-capafy-p0-truthful-outcomes.md)
- **Execution rule:** complete and verify one numbered task at a time; after each task, append the command evidence and commit hash here before beginning the next task.
- **Current state (2026-08-01):** Tasks 1-2 verified. Capafy failures now have an atomic, reusable incident identity that survives detached self-fix association without changing the compatibility result marker.
- **Next action:** Task 3, watch terminal self-fix results and deliver one evidence-gated Telegram repair closure exactly once.

#### P0 execution log

| Task | Status | Verification evidence | Commit |
|---|---|---|---|
| 1. Reporting contract | Verified | `python3 -m py_compile .../capafy_outcome.py`; `python3 -m pytest -q .../test_capafy_outcome.py` → `8 passed in 0.39s`; RED was `8 failed` before implementation | `548b382e1` |
| 2. Incident identity | Verified | RED: 4 incident tests + 2 sidecar assertions failed; GREEN: outcome `12 passed`, self-fix `23 passed`, Capafy loop `7 passed` | `c73d53b63` |
| 3. Repair closure monitor | Not started | — | — |
| 4. Builder handoff | Not started | — | — |
| 5. Marketer handoff | Not started | — | — |
| 6. 09:30 report | Not started | — | — |
| 7. Watchdogs + end-to-end proof | Not started | — | — |

### P0 — Truthful outcomes and repair closure

- Replace metric labels that confuse loaded schedulers with successful business outcomes.
- Introduce one incident id across primary failure, repair, verification, and Telegram closure.
- Send the missing repair-completed Telegram message automatically.
- Require a real URL for every listing/content success report.
- Separate gross, pending, realized, MRR, cost, and contribution in all reports.
- Load and verify the actual health watchdog; health must check recent business outcomes.

**Done when:** a seeded failure produces one coherent detect-to-verified-closure story and no stale contradictory report.

### P1 — Make the Marketer complete reliably

- Route the IG workflow to the 900-second marketing/browser lane and arm its token budget.
- Split deterministic account/session/post verification from creative judgment.
- Make warmup completion count verified successful sessions/actions, not calendar age.
- Reserve `live` for a verified public content URL.
- Implement the explicit account lifecycle and immediate replacement transition.
- Add a Marketing outcome gate: public URL or explicit dry/warmup terminal state.

**Done when:** a fresh test lifecycle reaches one verified public non-commercial Reel and Telegram contains the Reel, skill, and campaign URLs.

### P2 — Shared revenue event ledger and renderer

- Define the versioned event schema and append-only store.
- Add idempotent event writers to Builder, Marketer, account manager, sales reconcile, costs, and repairs.
- Build a deterministic natural-language Telegram renderer with the message contracts in this spec.
- Build the public dashboard from the same ledger.
- Preserve technical evidence separately from public/user-safe evidence.

**Done when:** Telegram and web display the same current state and each claim traces to evidence.

### P3 — Builder quality and portfolio cleanup

- Retire or reposition one-shot products that cannot pass the renewal test.
- Resolve or remove orphan drafts and review-rejected dead weight.
- Enforce one new validated experiment per pass rather than one new listing regardless of evidence.
- Verify approval/publication and hand the resulting public URL to Marketing automatically.

**Done when:** every active subscription product has a documented recurring value mechanism, unit economics, and experiment owner.

### P4 — Cost containment and attribution

- Freeze new products using the shared OpenRouter key.
- Provision one provider key and daily cap per hosted product where supported.
- Join provider usage to listing/run and calculate contribution margin.
- Automatically pause promotion or hosting when worst-case margin becomes negative.
- Migrate suitable products to BYOK or marketplace-native usage billing before retiring the shared key.

**Done when:** every hosted product has a measurable maximum loss and net margin.

### P5 — Market intelligence and experimentation

- Use official marketplace APIs first, then sitemap/static extraction, Crawl4AI for self-hosted bulk extraction, and Firecrawl for dynamic/agentic fallback.
- Use Context7 only for current implementation documentation, not market demand.
- Store source URL, timestamp, extracted metric, and confidence for every demand claim.
- Join marketplace sold deltas with internal funnel and cost data.
- Introduce pre-registered experiments and portfolio allocation by net revenue per impression.

**Done when:** the next product and marketing action can cite fresh demand and the previous experiment result.

### P6 — Multi-market revenue adapters

- Publish compatible capability variants to Apify Store, RapidAPI, and a direct one-time/membership channel.
- Maintain one canonical capability manifest and marketplace-specific packaging/pricing adapters.
- Add cross-market revenue, cost, and customer reconciliation.

**Done when:** one core capability earns verified revenue from at least two independent marketplaces.

### P7 — Selling Agent productization

- Extract the proven discovery/build/publish/market/measure/repair interfaces into a tenant-safe product.
- Add credential isolation, customer budgets, security review, billing, metering, and audit trails.
- Sell first to skill creators, then agencies and enterprise automation teams.

**Done when:** a third party reaches a verified sale without Capafy operators touching its workflow.

## 13. Explicitly out of scope for the first implementation plan

- Building a new marketplace before the Capafy loop produces repeatable revenue.
- Adding many social channels before one channel posts and attributes reliably.
- Replacing the agent's product/creative judgment with hardcoded keyword or regex rules.
- Claiming $10M feasibility from current sales without passing the staged revenue gates.
- Requiring routine human approval or babysitting.

## 14. Acceptance criteria for the “perfect Capafy loop” milestone

1. Builder completes one daily bounded outcome and supplies a verified listing/review URL.
2. Marketer completes one daily bounded outcome and supplies a verified public content URL or an honest lifecycle terminal state.
3. Every detected operational failure automatically enters repair within five minutes.
4. Every successful repair re-runs and verifies the original business observable.
5. Telegram never leaves a failure as the final message when the repair later succeeds.
6. Telegram reports are natural language, contain real links, and distinguish gross/pending/realized/MRR/cost.
7. Dashboard and Telegram agree because both use the same event ledger.
8. Account health distinguishes calendar age, warmup completion, session readiness, public live state, and reach health.
9. Every hosted product has a hard loss cap and measurable contribution margin.
10. The next product and marketing action are chosen from fresh evidence and prior experiment outcomes.
11. Routine operation, account replacement, retries, and repair require no babysitting.
12. A full seven-day run completes without a silent failure or contradictory report.
