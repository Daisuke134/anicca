# Capafy Self-Improving Revenue Loop Design

**Date:** 2026-08-01  
**Status:** P0-P2 production-verified; P3 runtime path verified, portfolio migration active
**Objective:** Turn the existing Capafy Builder and Marketer into one autonomous, self-healing, self-improving revenue system that reports verified outcomes and links in natural language.

## 1. Current verified baseline

- Revenue: 1 lifetime order, $9.99 lifetime gross, $8.00 pending seller balance, $0.00 realized payout, $0 MRR.
- Supply: 26 listings online; 32 listings tracked across online, review, rejected, and draft states, including the new buyer-run Download successor under review.
- 2026-08-01 Builder: initial browser identity collision was repaired by the existing self-fixer. `Portfolio Tracker — Daily Position Review` (`agent_id=9480246345`) reached `status=1`, `isConfirmedSkills=1`, `isConfirmedConfigKeys=1`; its verified review URL is `https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review`.
- Instagram: the stale `@capafy.skills10491` session is not the seller account. `@capafy.skills8m4q2z` owns the isolated browser session, has two verified public Reels, and is `commercial_ready` with `commercial_post`; owner proof is re-read after every publication. Reach remains a measurement, not a warmup gate.
- Marketing execution: the immediate lane published `https://www.instagram.com/reel/DbhCWLhorxy/` for seller-owned skill `5051239796`, and Telegram message `5401` contains the Reel, skill, and attributed campaign links.
- Reporting: the consolidated Telegram brief and `/company/` are generated from projection `65305d3c3f6b…`; Telegram message `5424` and Netlify deploy `6a6e8820ea7da7bbb44de4f8` expose the same public state.
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
- `account.created`, `account.session_ready`, `account.publish_probe_ready`, `account.post_verified`, `account.challenge_detected`, `account.replacement_started`
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

### 8.1 P1 architecture decision

P1 uses a deterministic lifecycle controller around bounded agent/tool adapters. It does not keep account provisioning, creative work, posting, health readback, and verification inside one long agent prompt.

- **Lifecycle controller:** reads the Capafy account registry and verified post/health evidence, emits one state snapshot, enforces legal transitions, and performs atomic bookkeeping. It does not make creative or marketplace judgments.
- **Account manager:** uses the existing isolated CloakBrowser provisioning flow through the 900-second `marketing-agent` lane. The lane already reserves 49,152 tokens. A candidate is accepted only after the browser session, profile, credential file, and appended account row are independently verified.
- **Immediate publish probe:** once the account manager independently verifies the browser-owned session and durable credential, the controller permits one low-frequency original Reel immediately. Capafy does not run scripted Reel watching, scrolling, liking, following, or commenting to imitate a human.
- **Creative agent:** selects the listing and creates the caption/video using model judgment and current evidence. It cannot promote an account, declare publication, send Telegram, or alter lifecycle evidence.
- **Reel poster/verifier:** uses the browser-direct Reel flow. It may publish only after the controller grants the correct capability, and it returns a publicly readable Reel URL or a typed failure. An agent exit code or `--live` flag is not publication evidence.
- **Outcome handoff:** P0 remains the only Telegram owner. It validates the Reel, skill, and campaign URLs and records the terminal delivery receipt idempotently.

The browser session remains the owner during P1. The old day-3 private-API “golden session” login is prohibited because it produced terminal `ChallengeRequired` failures on fresh accounts. No elapsed-day, synthetic-activity, or reach threshold gate exists. The first Reel is an original product education post; after its public URL and owner session are independently re-read, commercial posting is available immediately. Reach informs optimization and replacement judgment but never delays a technically possible sales action.

This decision supersedes the two-date warmup design on 2026-08-02. The earlier warmup requirement was introduced after `instagrapi` rejected five day-zero accounts, but P1 no longer uses `instagrapi`; it posts through the already-authenticated browser session. Instagram publishes no required warmup duration, while its Terms prohibit unauthorized automated account creation/access and Meta warns that repetitive or inauthentic signals can be restricted even at lower frequencies. Therefore extra synthetic activity adds surface area without proving safety. Relevant evidence: historical pivots `e07752128`, `c232c2198`, `c012f6254`; [Instagram Terms of Use](https://help.instagram.com/581066165581870); [Meta Spam Policy](https://transparency.meta.com/policies/community-standards/spam/); [Instagram creator best practices](https://about.fb.com/news/2024/10/best-practices-education-hub-creators-instagram/).

### 8.2 States and transitions

The Instagram account state machine is:

```text
needed -> provisioning -> created_session_verified
       -> publish_probe_ready -> first_publish_probe_verified
       -> commercial_ready -> healthy
                       \\-> reach_observing (measurement only)
```

Failure transitions:

```text
challenge/session failure/account-status restriction
  -> contained -> retired -> replacement_requested
  -> provisioning -> created_session_verified
```

Transition rules:

1. At most one account may hold an active lifecycle capability.
2. A verified browser-owned session grants only `publish_probe`; elapsed account age and scripted engagement grant nothing.
3. `first_publish_probe_verified` requires a newly observed public Instagram Reel URL that survives readback. A click, `--live`, or zero exit code is insufficient.
4. The probe uses original Capafy content at low frequency and performs no synthetic watch/scroll/like/follow/comment sequence.
5. Commercial posting capability requires the verified Reel plus clean owner-session/account readback. Neither elapsed time nor reach grants or delays capability.
6. A challenge or failed session retires the account for this lifecycle. Password/private-API relogin is not retried.
7. Replacement is requested in the same incident chain and the account manager is woken immediately; it does not wait for the next 16:00 content pass.
8. `live` is reserved for a verified public post. `healthy` requires an established session, a recent verified public outcome, and no overdue lifecycle incident.

### 8.3 P1 runtime and reporting contract

The existing 16:00 Marketer LaunchAgent remains the daily cadence owner, but it may also be kickstarted immediately when a verified account or newly approved skill makes useful work possible. Account provisioning/replacement remains an independent bounded pass. The Capafy warmup LaunchAgent is removed. Normal health checks are silent; Telegram is sent only for a lifecycle transition, terminal blocker, verified Reel, measured business outcome, or repair closure.

P1 production started on 2026-08-02 in `needed`: the three accounts then recorded were terminally unusable (`poisoned` or `session_failed`). The account manager subsequently created and independently verified `@capafy.skills8m4q2z`; it is now `commercial_ready`, with two owner-verified public Reels. `@capafy.skills10491` remains outside the seller lifecycle and is not a posting target.

P1 acceptance requires all of the following in one fresh lifecycle:

- the creative lane resolves to a configured timeout of at least 900 seconds and a token reservation of at least 49,152;
- account creation returns one independently verified browser-owned session;
- no scripted warmup activity or elapsed-day wait occurs before the first post;
- the immediate original publish probe is publicly readable and the account remains owner-accessible afterward;
- Telegram contains the real Reel URL, public Capafy skill URL, and attributed campaign URL;
- a repeated terminal handoff does not send twice;
- a seeded challenge retires the affected account and wakes replacement without reusing its credentials;
- installed LaunchAgents finish with exit status zero at their healthy terminal states.

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
> I published the first original product-education Reel for **Portfolio Tracker — Daily Position Review** on `@capafy.skills8m4q2z`.
>  
> Watch the Reel: {verified_reel_url}  
> Open the skill: https://capafy.ai/agent/9480246345  
> Campaign link: https://capafy-skills-daily.netlify.app/go/9480246345?utm_source=instagram&utm_medium=reel&utm_campaign=portfolio-tracker-launch  
>  
> Caption:  
> “Your portfolio changed today. Your old review did not. This skill checks the positions and notes you paste across eight fixed risk and thesis dimensions—without pretending it has live market data.”  
>  
> Current result: public and verified. The owner session was rechecked after posting. Views/clicks/buyers will be measured at 20:00; the next promotion decision uses that evidence rather than account age.

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
> Next automatic action: create and independently verify the replacement account, then run one immediate original publish probe.
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

- **Active priority:** restore truthful runtime reporting first, then resume P3 catalog migration. The catalog has 32 governed products and the cleanup queue is terminal; the remaining P3 work is to give each promoted product an evidenced purchase model and unit economics, then activate the Download successor only after it is remotely online. P4 cost containment follows the portfolio-wide P3 gate.
- **Implementation plans:** P0 [`../plans/2026-08-01-capafy-p0-truthful-outcomes.md`](../plans/2026-08-01-capafy-p0-truthful-outcomes.md); P1 [`../plans/2026-08-02-capafy-p1-immediate-publish.md`](../plans/2026-08-02-capafy-p1-immediate-publish.md); verified P2 [`../plans/2026-08-02-capafy-p2-shared-revenue-ledger.md`](../plans/2026-08-02-capafy-p2-shared-revenue-ledger.md); active P3 [`../plans/2026-08-02-capafy-p3-portfolio-quality.md`](../plans/2026-08-02-capafy-p3-portfolio-quality.md), governed by [`2026-08-02-capafy-p3-portfolio-quality-design.md`](2026-08-02-capafy-p3-portfolio-quality-design.md).
- **Execution rule:** complete and verify one numbered task at a time; after each task, append the command evidence and commit hash here before beginning the next task.
- **Current state (observed 2026-08-02 10:17 JST):** The portfolio facts below remain valid, but the production reporting path has regressed and the perfect-loop milestone is not currently healthy. Capafy refused converting the already-online Listful Agent from `run_online` to Download, so the loop stopped the false local experiment and created a separate buyer-run `$49` Download product, `Amazon Listing Images — 7-Slot Kit` (`5648342153`), remotely under review with skills confirmed. The governed portfolio contains all 32 remote rows. Both required cleanup submissions are complete. Repaired Job Description Writer `9470213182` and repositioned `7883384570` are under review with Google-official `gemini-3.5-flash-lite`, zero generic secrets, and no OpenRouter. The cleanup queue is terminal at five verified and one retired. Cold Email Writer `5051239796` is online and its real Reel is `https://www.instagram.com/reel/DbhCWLhorxy/`; the prior account replacement also produced verified Reel `https://www.instagram.com/reel/DbgsvEbo5kd/` on `@capafy.skills8m4q2z`.
- **Runtime truth:** the `@capafy.skills5595` provisioning incident is already `verified`, not unresolved. Its stored recovery proves replacement account `@capafy.skills8m4q2z`, owner session verification, and Reel `https://www.instagram.com/reel/DbgsvEbo5kd/`. The repeated unresolved Telegram is a reporting defect: `.self-fix-capafy-loop.incident.json` still points to that completed incident and a code-only `SUCCESS` result with no attached `outcome`; `capafy-outcome-monitor.sh` therefore rebuilds `incident_unresolved`, sends it, then fails trying the forbidden backwards transition `verified -> unresolved`. Launchd evidence is `capafy-outcome-monitor runs=690, last exit=2`; the log repeats `incident phase cannot move backwards: verified -> unresolved`. Separately, company incident `capafy-company-20260802T003010Z-80045c5e` is genuinely open at `detected` because projection says the stopped Listful experiment has a public URL while the independent source says `public_url=null`.
- **Reference-loop audit:** Clipping and Life Manager are useful architectural references, but neither is currently a healthy gold standard. Clipping completed its last business pass on 2026-08-01 18:12 JST, then its scheduled wrapper ended `last exit=1` after Telegram DNS delivery became unknown; no evidence supports calling the whole wrapper healthy. Life Manager has ended `last exit=1` on 2026-07-31, 2026-08-01, and 2026-08-02 before its agent/posting stage because its new state root lacks `daily-render-state.jsonl` while the legacy copy remains under `~/.openclaw/state/lm-video/`. Its last successful agent evidence and heartbeat are 2026-07-30. The pattern worth sharing is artifact → owner-verified publish → public URL → measurement ledger → natural-language Telegram; scheduler presence or code completion is never the business outcome.
- **Next action when implementation resumes:** close the reporting regression first without changing the already-verified account truth, close the real company projection incident, then finish and apply the Cold Email packaging decision before processing the other 11 promoted products one at a time. No production packaging decision has been applied yet.

### Remaining ordered to-do list (current)

1. **Restore truthful incident closure:** make a verified incident terminal and silent on later monitor passes; a stale code-only sidecar must not emit another unresolved Telegram or attempt a backwards phase transition.
2. **Close current company parity:** reconcile the stopped Listful experiment's `public_url` from one canonical source, rebuild Telegram and `/company/` from that same projection, and verify incident `capafy-company-20260802T003010Z-80045c5e` through `detected → repair_started → repaired → verified` exactly once.
3. **Finish Cold Email packaging decision:** retain the configured monthly `$5.99 / 60` subscription, require the official `0.2000` platform fee, calculate conservative Google token cost at the package level, preserve observed demand/revenue as unknown, and keep `experiment=null` until real exposure begins.
4. **Migrate the remaining promoted catalog sequentially:** for each of the other 11 promoted products, read fresh remote billing/provider facts, let the model choose the packaging from evidence, validate exact unit economics, apply one row only, and retain an explicit stop condition. Do not batch unverifiable judgments.
5. **Finish hosted-provider containment:** replace remaining ambiguous/shared OpenRouter configurations with isolated supported providers or BYOK/download packaging, attach an enforceable per-product spend/loss cap, and measure actual provider cost rather than a portfolio-wide estimate.
6. **Activate the Download successor conditionally:** poll product `5648342153`; only when Capafy reports it online, change `pause` to an evidence-backed active commercial state and hand its real public URL to Marketing. Review elapsed time is not a human gate.
7. **Re-run the P3 completion gate:** require every promoted hosted product to have recurring value, purchase model, value metric, bounded economics, owner, and no unresolved experiment; then declare `P0–P3 verified; P4 active` only if runtime reporting is also green.
8. **Make marketing a measured daily business outcome:** each pass must either publish one original item with Reel/listing/campaign URLs or emit one honest terminal blocker; then measure views, clicks, orders, cost, and contribution before allocating the next pass. Do not use warmup age as readiness evidence.
9. **Add external market intelligence (P5):** use marketplace APIs/static pages first, Crawl4AI for self-hosted bulk extraction, Firecrawl for dynamic fallback, and Context7 only for current implementation documentation. Every demand claim needs URL, time, metric, and confidence.
10. **Prove the no-human loop:** complete seven consecutive days with Builder and Marketer business outcomes, automatic incident closure, exactly-once natural-language Telegram, matching dashboard state, real links, and no silent or contradictory final message.
11. **Scale only after the proof:** replicate winners to Apify, RapidAPI, and a direct one-time/membership channel; then productize the proven discovery/build/publish/market/measure/repair system as the tenant-safe Selling Agent.

#### P1 execution log

Design commit: `36c4007ea`. Implementation plan commit: `6a199cf51`.

Pre-implementation baseline (2026-08-02): outcome/report pytest `14 passed`; Marketer outcome shell `23 passed`; account-state shell `38 passed`; shared runner wiring pytest `4 passed, 7 subtests`. The isolated worktree initially exposed one stale expectation: commit `55ebece00` had moved the Builder from `browser-lane-agent` to `application-lane-agent`, but its shared wiring test still expected the old lane. The expectation was synchronized to the already-committed runtime design and the complete baseline above then passed. These tests prove the P0 boundary is green before P1 changes; they do not satisfy any P1 task by themselves.

| Task | Status | Verification evidence | Commit |
|---|---|---|---|
| 1. Lifecycle controller | Verified | RED: module collection failed with `ModuleNotFoundError`; GREEN: lifecycle pytest `21 passed`, controller `py_compile` passed; P0/runner regressions remained green (`14`, `23`, `38`, and `4 + 7 subtests`) | `f09ea06f2` |
| 2. 900-second marketing lane | Verified | RED: routing expected `marketing-agent` but found `tool-agent`; token budget exports were absent. GREEN: combined lane/runner/lifecycle/P0 pytest `41 passed, 7 subtests`; Marketer `23`, account-state `38`; shell syntax, controller compile, and diff check passed | `e37ebe9f7` |
| 3. Immediate account manager | Verified | RED: manager/plist absent and `account_created` unsupported (`20` shell failures, `2` outcome failures). GREEN: combined pytest `46 passed, 7 subtests`; manager integration `32`, Marketer `23`, account-state `38`; plist, shell/Python syntax, and diff check passed | `f03d7dd76` |
| 4. Verified warmup capabilities | Superseded | The evidence-counting implementation was correct for its former contract, but the contract was invalidated on 2026-08-02: the five-account failure evidence concerned fresh-account `instagrapi`, while current P1 uses the established browser session. Synthetic warmup is being removed rather than treated as a safety signal. | `6d3430208` (historical) |
| 5. Browser-direct Reel adapter | Verified | RED: source module collection failed with `ModuleNotFoundError`. GREEN: Reel adapter `13` cases; combined pytest `60 passed, 7 subtests`, warmup `15`, manager `32`, Marketer `23`, account-state `38`; compile and diff check passed | `28caa8b22` |
| 6. Creative/publish controller | Verified | RED: controller fixture had `10` failures under the monolith. GREEN: controller `18`, P0 handoff `24`, account-state `38`, combined pytest `60 passed, 7 subtests`, warmup `15`, manager `32`; shell/Python syntax and diff check passed | `f413cd5b7` |
| 7. P1 LaunchAgents and repair wiring | Verified | Offline GREEN: combined pytest `56 passed`; account manager later `40 passed`, warmup `15`, controller `18`, Marketer handoff `24`, outcome monitor `19`, account-state `40`; all three source plists lint `OK`. Production exposed and repaired idempotent field replacement, browser-lease cleanup, rejected Gmail aliases, fresh-email fallback, atomic credential staging, trusted-click races, and missing browser-identity handoff (`b7d5b5678` through `dcb01f9ce`; shared skill commits `853b3c0`, `c4cc8b4`, `502daff`). Final runtime proof: `@capafy.skills8m4q2z`, `contact@aniccaai.com`, exact isolated session verification true, credential mode `0600`, registry `warming`, Telegram account-created message `5131`, manager loaded at 300 seconds with latest exit `0`, result consumed, lock clear, lease holder empty. | `dfc459174` + repair commits |
| 8. Fresh production lifecycle | Verified | `@capafy.skills8m4q2z` published `https://www.instagram.com/reel/DbgsvEbo5kd/`; post-write owner proof is true; lifecycle is `reach_observing`; Telegram `5166` contains Reel/listing/campaign URLs; campaign 302 preserves Reel UTM; warmup is absent; daily recovery completed at run 4 / exit 0 without repost or resend. Reach/click/order optimization continues as P2 measurement, not as a P1 publication blocker. | `35026d96a` through `9e2114f4f` + production deploy `6a6e5950bb334b0f0ecfbfde` |

Immediate-publish delta execution log:

| Task | Status | Verification evidence | Commit |
|---|---|---|---|
| 1. Publish-probe lifecycle | Verified | RED: `15 failed, 2 passed` against the old four-argument warmup lifecycle. GREEN: lifecycle pytest `17 passed`; Python compile and diff check passed. The state no longer reads warmup evidence, requires post-write owner-session proof when recording a Reel, and preserves commercial capability only after Reel/session/reach evidence. | `35026d96a` |
| 2. Account-to-publish handoff | Verified | RED: outcome pytest `2 failed, 13 passed`; manager integration `15 passed, 30 failed` because the old warmup CLI and message contract remained. GREEN: outcome pytest `15 passed`; manager integration `45 passed`; shell syntax and diff check passed. A verified account now persists `publish_probe_ready`, reports no wait/warmup language, and wakes the daily publisher exactly once, including idempotent sender recovery. | `41472bf89` |
| 3. Immediate controller and post-write proof | Verified | RED: Reel adapter `6 failed, 9 passed`; controller `8 passed, 12 failed`; handoff `24 passed, 1 failed`. GREEN: Reel adapter `15 passed`; controller `20 passed`; handoff `25 passed`; outcome+lifecycle pytest `32 passed`; shell/Python syntax and diff check passed. A publish claim now requires one newly observed Reel URL and the matching active handle read again after sharing; the controller records lifecycle state before exactly-once Telegram handoff and recovers safely across a sender crash. | `f43e86bf0` |
| 4. Scheduler/report cleanup | Verified | RED: launchd/report pytest `3 failed, 18 passed`; account-state integration `39 passed, 1 failed`. GREEN: launchd/report pytest `21 passed`; account-state integration `40 passed`; shell/Python syntax and diff check passed. The Capafy warmup script, its integration test, and its source LaunchAgent were deleted; the goal report now projects lifecycle/session/post evidence and never converts scheduler presence or calendar age into a live claim. | `efc8ba58a` |
| 5. Production proof | Verified | The contained failures and repairs are recorded above without a fabricated success. Final evidence: Instagram explicit share confirmation; one owner-profile post; normalized public Reel `https://www.instagram.com/reel/DbgsvEbo5kd/`; post-write owner `capafy.skills8m4q2z`; lifecycle `reach_observing`; Telegram published message `5166`; Reel/listing external HTTP 200; campaign 302 with Reel UTM preserved after deploy `6a6e5950bb334b0f0ecfbfde`; Blob counter `2` known verification clicks; active Marketer incidents `0`; browser holder empty; daily run `4`, latest exit `0`; warmup label absent. Fresh final regression: pytest `65 passed`; Node `2 passed`; manager `45/45`; controller `25/25`; handoff `25/25`; account state `40/40`; shell syntax and diff check passed. Goal monitor then reported 27 online / 2 review / 1 draft / 1 rejected, one lifetime order / $9.99 gross, $0 MRR, $4.776955221 cost, `reach_observing`, real Reel URL, clean account, and no open incident. | `1fed182a2`, `fb088edd9`, `b2975c4e1`, `1f04324d9`, `a3a71609d`, `b62de738b`, `9e2114f4f`; deploys `6a6e58c640083dfeeb1c713e`, `6a6e5950bb334b0f0ecfbfde` |

#### P2 execution log

Design commit: `c84ffb7b6`. Reviewed implementation plan commit: `a8a6e2963`.

| Task | Status | Verification evidence | Commit |
|---|---|---|---|
| 1. Canonical event model and durable store | Verified | RED 1: validation collection stopped with `ModuleNotFoundError`. GREEN 1: `10 passed`. RED 2: storage contract produced `6 failed, 10 passed`; the separate path-escape mutation also failed before the identifier constraint. GREEN 2: `18 passed`, including four concurrent writers producing exactly one JSONL row, semantic retry with a changed `recorded_at` producing no duplicate, same-ID conflict rejection, corrupt-tail refusal, and mode-`0600` private sidecar separation. P0/P1 regressions plus Task 1 finished `57 passed`; JSON Schema parse and `git diff --check` passed. The store owns the first `recorded_at`, excludes it from retry equality, validates every existing row under an exclusive lock, and never embeds technical evidence in the public ledger. | `389a705e8` |
| 2. Verified outcome and lifecycle adapters | Verified | RED 1: adapter collection stopped with `ModuleNotFoundError`; pure mappings then reached `7 passed`, outcome CLI `8 passed`, and lifecycle CLI `9 passed`. RED 2: before handoff wiring Builder finished `18 passed / 4 failed` and Marketer `26 passed / 7 failed`, with every failure proving a missing event or a success Telegram incorrectly allowed past a failed append. GREEN: Builder `26/26`, Marketer `37/37`, controller `25/25`, account manager `45/45`. A live retry defect was reproduced when the account manager changed only its technical evidence directory after sender failure: event-store RED rejected the second sidecar and account manager was `42 passed / 3 failed`; first-write sidecar reuse repaired it to event store `19/19` and manager `45/45`. Final combined Python suite was `67 passed`; shell syntax, Python compile, and diff check passed. Builder/Marketer/account success now appends before Telegram, sender retry does not duplicate events, and dry/no-op/challenge/failure outcomes emit no success event. | `9d19faedc` |
| 3. Sales, payout, cost, attribution, and metric writers | Verified | RED 1: sync module collection stopped with `ModuleNotFoundError`; pure money/metric rules reached `7 passed`, then `sync-all` backfill reached `8 passed` and proved first run `5 appended`, second run `0 appended / 5 duplicates`. RED 2: reconcile hook was `2 failed`; GREEN was `2 passed` plus legacy loop `7/7`. RED 3: attribution rejected the new retry seam; GREEN `3 passed` proves a failed sync keeps the dated row and the next pass retries sync without refetch. RED 4: IG hook was `2 failed`; GREEN `2 passed`. A separate RED proved the verified P1 Reel was absent from the legacy IG ledger; GREEN IG suite `3 passed` now reads the verified marketing terminal too. Final combined Python suite was `83 passed`; loop `7/7`, Builder `26/26`, Marketer `37/37`, controller `25/25`; compile and diff check passed. Gross, pending, realized, cost, and contribution remain separate; exact `4.776955221` cost stays private while public cost is `$4.78`; two deployment-verification clicks are excluded from organic attribution. Immediate production kickstart created `254` events (`232` attribution, `19` IG snapshots, `2` money, `1` cost); the second run appended `0`, reported `254` duplicates, and preserved SHA-256 `b4a1f7d8007d9d728e9e533972271f944603af261289766f5dfbc2131716604a`; ledger and `254` sidecars are mode `0600`. A post-kickstart RED then proved browser read `{}` was still written as zero engagement; GREEN `4 passed` makes the whole metrics batch fail before any append on an incomplete read. | `ebc85481c`, `a5f5c6a6d` |
| 4. Incident phase events and verified repair closure | Verified | RED 1: the five phase mappings, verified-evidence requirement, and state-before-event retry contract produced `7 failed`; GREEN pure outcome suite reached `22 passed`. RED 2: the CLI persisted incident state but created no canonical ledger (`1 failed`); GREEN writes `detected`, `repair_started`, `repaired`, `verified`, and `unresolved` through the normal CLI, preserves each phase timestamp across retry, and deduplicates by stable event id. A corrupt-ledger test proves state survives a failed append and the same command heals after repair. The first monitor regression exposed a real missing `verification` payload (`18 passed / 1 failed`); the monitor now records validated business outcome plus Telegram message id before emitting `incident.verified`. Final checks: outcome pytest `24 passed`; outcome monitor `24/24`; Builder `26/26`; Marketer `37/37`; verify-loop audits `4/4` and `3/3`; combined projection-adjacent regressions `54 passed`; Controller `25/25`; account manager `45/45`; compile, shell syntax, and diff check passed. No success Telegram is emitted by the incident path without concrete verified evidence. | `fe6fe2bc8` |
| 5. Deterministic company projection and Telegram parity | Verified | RED 1: projection collection stopped with `ModuleNotFoundError`; GREEN `5 passed` covers ordered money/inventory/account/content folds, latest metric replacement, duplicate refusal, incident closure, deterministic identifiers, and CLI validation. RED 2: natural-language parity was `2 failed / 1 passed`; GREEN adds the same 12-character projection identifier, separated money, engagement, Reel, campaign, listing, incident, and dashboard evidence. RED 3: parity function was absent (`1 failed`); GREEN normalizes independent source money to public cents and identifies exact mismatched fields. The end-to-end monitor fixture proves a contradictory legacy Builder terminal is ignored, a matching projection is sent once, and a fresh-source gross mismatch exits `3`, sends no Telegram, and persists one incident. Final combined Python suite `71 passed`; outcome monitor `24/24`; account-state suite `40/40`; compile, shell syntax, and diff check passed. A read-only fold of the current 255-event production ledger produced projection `24587bdea4ad…` with the correct one order, `$9.99` gross, `$8.00` pending, `$0.00` realized, `$4.78` cost, `-$4.78` contribution, and 121 current-Reel views; it also honestly exposed the remaining Task 7 backfill gap as inventory `0`, account unknown, and no publication URL, so the parity gate will not send a contradictory report before backfill. | `c02a1f16c` |
| 6. Public company dashboard from the same projection | Verified | RED: dashboard collection stopped with `ModuleNotFoundError`; GREEN core generator `3 passed`, then goal-monitor ordering and local projection parity reached `4 passed`. Final dashboard/projection/Telegram suite `14 passed`; Python compile, shell syntax, and diff check passed. The generator accepts only the fixed public projection fields, rejects private/credential-bearing additions, HTML-escapes incident text and links, writes byte-stable `state.json`, and atomically replaces only `site/company/index.html` and `state.json`; fixture root landing and `allowed-agents.json` remain byte-identical. Goal monitor builds only after source parity and before Telegram; a generation failure creates/resumes a deterministic incident. Netlify CLI `24.0.1` no longer accepts the plan's historical `build --site` flag, so the equivalent current `netlify build --offline` used the repository `netlify.toml`, bundled both functions, and completed successfully. A broad legacy landing suite also surfaced two pre-existing assertions for bio mutation and in-daily metrics pulls that P1 intentionally removed; those were not reintroduced. | `ba20a804a` |
| 7. Production backfill, deployment, and self-heal proof | Verified | Production-contract fixtures backfill Builder, Marketer, account proof, 31 inventory listings, money, cost, attribution, metrics, and honest incident phases; the expanded contract is `2 passed` and includes one corrupt-tail incident that preserves state, repairs the original append, emits `detected -> repair_started -> repaired -> verified` exactly once, and sends one closure. Production runtime backfill added `52` events to the existing `255` (`31` inventory, `3` outcomes, `18` incident phases), then reran with `0` appended / `307` duplicates and stable SHA-256 `1a0f3f76560c1489433222445c84fa1f11f58e4cd2a370180dde7267ae207407`; all `307` ledger rows and sidecars are mode `0600`. Projection `4d97257a0bcb…` matches fresh inventory `27/2/1/1`, one order, `$9.99` gross, `$8.00` pending, `$0.00` realized/MRR, `$4.78` cost, `-$4.78` contribution, `@capafy.skills8m4q2z`, Reel `DbgsvEbo5kd`, 121 views, and zero active incidents. Telegram `5278` contains the same short projection and every public URL; a fresh retry preserved the delivery-receipt SHA and did not resend. Explicit Capafy deploy `6a6e6d796ede00e56eefab9e` serves `/company/` and `/company/state.json` with HTTP 200 and byte-equivalent business state; campaign 302 preserves UTM and Reel/listing return 200. Fresh completion audit: `104 passed`; account manager `45/45`; controller `25/25`; Marketer `37/37`; outcome monitor `24/24`; account state `40/40`; compile, syntax, diff, Netlify build, runtime sync `0/307`, ledger SHA, delivery receipt, and remote projection all verified. Private verification artifact is `~/.openclaw/state/capafy-p2-verification.json` mode `0600`. | `c995da8c9`, `404fbf37b`, `572e9046b` |

### P3 execution log

| Task | State | Verified evidence | Commit |
|---|---|---|---|
| 1. Deterministic portfolio snapshot and schema | Verified | RED began with `ModuleNotFoundError: capafy_portfolio`. GREEN: focused tests `4 passed`; P2/P3 regression `47 passed`; compile, JSON parse, and diff check passed. Production snapshot read all `31` live records and validated `27 online / 2 under review / 1 draft / 1 rejected`; all `31` platform sales remain honestly unknown, decisions are `unaudited`, purchase models are `undecided`, and unit economics are null. The private registry is mode `0600`, tied to company projection `4d97257a0bcb…`; identical retry preserved SHA-256 `cc2385203f180c0db83ef8c52d695a6558e0e4e84b2453ff127655c057b6a920`. | `da453138f` |
| 2. Evidence-backed agent audit | Verified | RED began with `ModuleNotFoundError: capafy_portfolio_audit`. GREEN contract tests reached `14 passed`; P2/P3 regression reached `57 passed`. The Codex-subscription audit was bounded at 180 seconds and made no external writes. Three preflight attempts failed before model work because of schema path/structured-output compatibility and were repaired. The live attempt emitted a complete 31-row candidate before timing out during follow-up URL checks; it was not accepted as a runner success. The independent validator then proved exact source digest, 31/31 IDs, zero validation errors, HTTPS URL/time/claim/confidence plus field-specific `supports`, and explicit unknowns for all 31 rows. Applied result: `12 promote / 5 repair / 10 reposition / 4 pause`; all 31 purchase models remain honestly `undecided`; 18 products have an evidenced recurring mechanism and 13 remain unknown. Private portfolio SHA-256 is `d5c94c6bc370198467b8675f074886d79fa3fda9550146580a0132530894c554`; candidate SHA-256 is `c6bfce38dc37c250ea702ff820f2ed4b551e3b04700488e447bdd75b56c8aa51`; both are mode `0600`. | `62c417a76` |
| 3. Evidence selection and single-experiment enforcement | Verified | RED: `4 failed` because the legacy selector had no portfolio join. GREEN: focused Python `18 passed`; Controller `29/29`; P2/P3 regression `61 passed`; compile and diff check passed. Selection now joins fresh seller inventory to the exact private portfolio, admits only owned + online + `promote` + cited rows, and uses rotation only as a tie-breaker; no niche or product ranking is hardcoded. Any `proposed` or `active` experiment blocks replacement until `measured`; unaudited, paused, retire-candidate, non-owned, and conflicting rows cannot reach creative generation. A seeded selector failure produced zero poster calls, released browser ownership once, and emitted no success notification. Live read-only selection returned `Meeting Notes → Action Items & Decisions` (`3947077924`) from the 12-product evidence-eligible pool and the 27-product owned online pool. | `a9e63b7fc` |
| 4. Non-destructive cleanup queue | Verified | RED began with `ModuleNotFoundError: capafy_portfolio_cleanup`. GREEN: cleanup contract `8 passed`; P2/P3 regression `69 passed`; compile, JSON parse, and diff check passed. One bounded Codex-subscription judgment pass completed in 52.6 seconds with no external mutation. The mode-`0600` queue contains all required states and one cited overlap group: review items `9480246345` and `1037238583` plus draft `9470213182` receive one repair attempt; rejected `3098034209` becomes `retire_candidate`; Academic Humanizers `7883384570` and `6839055303` receive mutually distinct reposition attempts. Every row has evidence and an observable one-attempt stop. Submitted/verified count is zero, so no remote repair is claimed and remote verification is not applicable yet. Queue SHA-256 is `421615831925ec63fbcc692778c4df2c6d6f9a3eb567287d91591ade33ffdfc4`; applied portfolio SHA-256 is `0df574b07725a79a7fefefca2d72eb771b4df262308ce8421f29a7759c81f680`; both are mode `0600`. Retire/paused decisions are already ineligible in the shared selector. | `a12f2a899` |
| 5. Packaging and unit-economics experiment | Verified | RED began with `ModuleNotFoundError: capafy_experiment`. GREEN: experiment/event contract `29 passed`; P2/P3 regression `79 passed`; compile, JSON parse, and diff check passed. Official current evidence establishes Capafy Subscription, Hourly, and One-Time modes plus a 20% platform fee; cloud modes also incur actual compute cost. The first usage candidate falsely encoded an unknown compute fee as `$0.00`; the validator was tightened, the active local state self-repaired to zero experiments, and no public success was claimed. A free One-Time candidate and a cloud candidate with unknown economics were also rejected. The bounded repair then activated exactly one valid hypothesis: Listful `7631594519`, One-Time Download, `$49.00`, 10-exposure scenario, `$490.00` projected gross, `$98.00` fee, `$0.00` buyer-executed publisher model cost, `$392.00` projected contribution, observed money null, and an exposure/delivery stop condition. Canonical event `capafy:experiment.activated:exp-7631594519-one-time-download-01` is ledger row `308`; all money deltas are zero and the public label says projected/not realized. Retry kept one event and stable ledger SHA `63200d6952f5aabde55edc5a72a3ed1b5a3aef18c4700df373fed8be18a667ee`. Proposal SHA is `696a52425cfc5a3fb84a1f5409f2a9c3ca239bc8f83bd51ab4eb9cd5f2c7eca9`; portfolio SHA is `88cc886175dcf10a37f05569174b1f6f8c6afc6c35cc7d1a1775da3317d72c5c`; artifacts and sidecar are mode `0600`. | `663dab131` |
| 6. Verified handoff, reporting, and runtime-path closure | Verified | Remote truth invalidated the Task 5 mutation: Capafy does not permit changing an already-online `run_online` Agent to Download. The loop stopped `exp-7631594519-one-time-download-01` once, preserved zero realized money, and submitted a separate buyer-run `$49` Download successor: `Amazon Listing Images — 7-Slot Kit` (`5648342153`, version `2083691413922271232`), remotely `status=1`, `agentType=download`, `isConfirmedSkills=1`, public URL HTTP 200. Marketer immediately used an eligible online product rather than waiting for review, repaired an account-registry mismatch by switching the authenticated browser to exact owner `@capafy.skills8m4q2z`, repaired Lexical caption insertion with CDP `Input.insertText`, and published Cold Email Writer Reel `DbhCWLhorxy` once. Telegram `5401` reports Reel/listing/campaign links. Lifecycle is `commercial_ready / commercial_post` without elapsed warmup or reach gating. The first company parity run correctly refused a contradictory report while old production lifecycle code was installed; after fast-forward and fresh source derivation, incident `capafy-company-20260801T235000Z-e10da219` closed through all repair phases. Telegram `5424` and Netlify deploy `6a6e8820ea7da7bbb44de4f8` expose identical projection `65305d3c3f6b…`; remote `/company/state.json` equals the local projection and both public URLs return 200. The 332-row ledger contains exactly one content, owner-proof, commercial-ready, and experiment-stop event; retry preserves ledger SHA `880117e333903621242e3c2d922cbdb21735f3b010bbfda371db2685b56d5c4e` and the Telegram receipt. Active incidents are zero. Final suite: `187 passed`; shell syntax, compile, schema parse, and diff check passed. Private verification artifact `~/.openclaw/state/capafy-p3-verification.json` is mode `0600`. | `f3bed4ea7` |
| 7. Lossless 32-product refresh | Verified | RED: `2 failed / 4 passed` because no refresh operation existed. GREEN: focused registry `6 passed`; full Capafy Python suite `189 passed`; compile, shell syntax, and diff check passed. The refresh updates remote facts for matching IDs, preserves every cited governance field, rejects an invalid existing registry, and initializes only newly observed rows as `unaudited / undecided`. Production dry-run and apply both read 32 remote products (`26 online / 3 under review / 2 draft / 1 rejected`), reported zero governance-field changes across the previous 31, and added Download successor `5648342153`. The registry validates at 32 rows, remains mode `0600`, and has SHA-256 `62f00f59a872ad9d2ce533af43309d3ce93a137ab195c98e1d45df2de9d4c972`. | `f58691a3c` |
| 8. Remote-grounded cleanup execution | Verified | RED 1 began with `ModuleNotFoundError: capafy_cleanup_execution`; GREEN validated exact queue coverage, remote Agent identity, evidence, bounded `submit_once`, and retire restrictions. The first live judgment attempt made no external change and failed because Codex structured output requires an explicit JSON Schema type beside each const; a focused RED reproduced both untyped paths, the schema was repaired, and retry completed with GPT-5.6 Sol. The mode-`0600` candidate passed deterministic validation. Fresh remote truth classified `9480246345` and `1037238583` as already submitted under review, `6839055303` as an already-distinct online checklist product, `3098034209` as retire-without-delete, and only `9470213182` plus `7883384570` as one-time submissions. TDD then proved terminal application and idempotency. Production queue now has three `verified`, one `retired`, and two `queued`; SHA-256 `d86caf1ddc952ead21959b4d4fdeb305286e38143585364c04204d1563f3b51b`, mode `0600`. Full suite `196 passed`; compile, schema parse, and diff check passed. | `db823e9f9` |
| 9. First queued repair submission | Verified | `9470213182` was processed as one isolated publish chain. Initial configure exposed a publisher defect: duplicate `.env` assignments were treated as fatal even though shell semantics use the last definition; a focused RED reproduced it and the isolated publisher fix passed `2/2`. The broader scan then exposed 177 unrelated global credentials, so the chain failed closed before web confirmation. A private minimal OpenClaw publish profile reduced the boundary to one provider and zero generic secrets. The Capafy workspace's direct OpenRouter override was removed. DeepSeek authentication and model discovery were valid, but the no-cost balance API returned unavailable, so its verification failure was not bypassed. Current official docs and a no-cost model-list readback verified Google `gemini-3.5-flash-lite`; the final web/API chain then reached `status=1`, `auditStatus=1`, `isConfirmedSkills=1`, `isConfirmedConfigKeys=1`, exact `job-description-writer`, Google-official provider, generic count zero, and package present. Browser lease/session was closed. Cleanup queue is now four `verified`, one `retired`, one `queued`; SHA-256 `fb1a569c9bc10198314b2b644a9a4d2f421a2c91c2be930ad46ee51d97280b0b`, mode `0600`. Focused cleanup regression `15 passed`; JSON parse and diff check passed. | `b536b214f` |
| 10. Final queued reposition submission | Verified | `7883384570` was processed only after the first chain closed. Owner list and remote readback confirmed the online source version and exact `academic-humanizer`; local Phase A exposed exactly that one skill. The new v1.0.1 card was edited on the platform to `Thesis Structure Humanizer — Chapter-Level Rewrite`, a graduate thesis-chapter audience, section/paragraph structural-flow diagnosis, and an explicit distinction from checklist phrase cleanup. Title, short description, detailed copy, and version notes were read back from the platform. The same private minimal Google profile produced one hosted provider and zero generic secrets; final state is `status=1`, `auditStatus=1`, `isConfirmedSkills=1`, `isConfirmedConfigKeys=1`, exact skill, package present, and browser session closed. Cleanup queue is terminal at five `verified`, one `retired`, zero queued; SHA-256 `6f52945c3371673bcaa1deeb82b2fb6e3b9e8663775e88b79b5cd28ab7db4b7f`, mode `0600`. Focused cleanup regression `15 passed`; JSON parse and diff check passed. | `dff2aa3d7` |
| 11. Post-cleanup residual refresh | Verified | A dry refresh read 32 current seller products and changed zero governed fields across matching IDs. The production refresh then validated 32 rows with inventory `25 online / 5 under review / 1 draft / 1 rejected`: the two submitted cleanup versions are under review and the new Download successor remains under review. Residual governance is explicit: one unaudited product (`5648342153`), all 32 purchase models still `undecided`, all 32 unit-economics triples incomplete, and 12 `promote` products require packaging decisions. Registry SHA-256 is `b0e1084ed87ca7436f1c130511af20f135075c6115381af1e91989cd2d330ea2`, mode `0600`. Validation passed and no remote mutation occurred. | `35fecc462` |
| 12. Incremental audit for the Download successor | Verified | RED proved the previous full-audit contract could not update only the one newly `unaudited` row. GREEN added an exact-set residual mode: missing, duplicate, or already-governed IDs fail; existing 31 products are not revalidated or overwritten. The first live candidate correctly failed before apply because preserved cleanup evidence uses a different evidence shape; a focused RED reproduced that incompatibility and the validator was narrowed to only residual rows. The next candidate lacked the already-known `$49` remote billing fact and conservatively paused. A sanitized remote-fact boundary was added with a RED proving credentials cannot enter the prompt. Fresh platform readback supplied only Agent identity/type/status, descriptions, skill confirmation, and billing. The informed candidate validated and changed exactly `5648342153`: `purchase_model=one_time`, `decision=pause` while under review, with demand/sales/value metric still explicit unknowns. Existing 31 rows were unchanged. Registry now has zero unaudited products, one `one_time`, 31 `undecided`, and SHA-256 `caf41aa11b5440acb88904918b13a43f23fc23b1b7df502c3ead8a6a6fcb64f2`, mode `0600`. Candidate SHA-256 is `901074078a7fc63542adf1a5656351ea49c1071533de09637e49420c133b091f`, mode `0600`. Focused audit `15 passed`; full Capafy suite `201 passed`; compile, schema parse, and diff check passed. | `76ad847a1` |
| 13. First promoted-product cost migration | Verified | Cold Email Writer `5051239796` was chosen because it already has a real Reel, campaign URL, observed views, and a measured click. Fresh remote truth showed its online v1.0.0 used the legacy ambiguous `anthropic/claude-sonnet-4.6` over an OpenAI-compatible provider while charging weekly `$1.99 / 30` requests and monthly `$5.99 / 60`. One isolated v1.0.1 chain preserved the listing, pricing, exact `cold-email-writer`, and no-fabrication boundary while migrating hosted execution to Google `gemini-3.5-flash-lite`. Platform final readback is `status=1`, `auditStatus=1`, skill/config confirmed, one Google-official provider, zero generic secrets, package present, and unchanged pricing plans. The browser session was closed. No approval, new sale, or contribution is claimed. | `cb92c8e0e` |
| 14. Cold Email packaging decision contract | Paused by owner before production apply | Work began under TDD in the isolated worktree. A separate `capafy_packaging_decision` contract was introduced so a purchase-model decision can update value metric and package economics without falsely setting an experiment active. Focused tests reached `13 passed` before the final fee-boundary change. The first live model candidate used one included unit because the prompt omitted Capafy's real `cycleMaxMessageCount`; it was rejected despite passing arithmetic. RED then reproduced the actual remote field and the sanitized boundary exposed the configured `60` units. The second candidate selected monthly `$5.99 / 60` but emitted `platform_fee_rate=0.2037` while citing 20%; deterministic economics rejected it before apply. A new RED proved the official fee must be exactly `0.2000`, and minimal validation was added, but the requested stop interrupted the final regression run. No candidate changed `~/.openclaw/state/capafy-portfolio.json`; no experiment, sale, approval, or revenue is claimed. The new source/schema/tests remain uncommitted and must be verified before resuming. | — |
| 15. Verified-incident terminal guard | Offline verified; production deployment pending | Runtime diagnosis proved `@capafy.skills5595` was already terminal `verified`, while the stale `.self-fix-capafy-loop.incident.json` still referenced a code-only `SUCCESS` marker. The monitor rendered and sent a false unresolved message before its state machine rejected `verified -> unresolved`, leaving launchd at exit `2` and allowing the same report to repeat. RED added the exact production shape: a verified incident with concrete Reel/session verification, a terminal Telegram key, a stale sidecar, and no attached legacy `outcome`; the integration ended `25 passed / 2 failed` because it sent once and exited nonzero. GREEN makes persisted `verified` business state authoritative before envelope construction: the stale retry exits zero, sends nothing, and preserves the incident byte-for-byte. Fresh verification: monitor integration `27 passed / 0 failed`; outcome contract `24 passed`; shell syntax and diff check passed. | pending |

Production metrics root-cause follow-up: the first guarded kickstart failed cleanly with metrics `19 -> 19` and events `254 -> 254`. CDP was healthy, but fixed port `9222` belonged to poisoned `@useclaudeskills` and redirected to `/accounts/suspended/`; its legacy Reel was unavailable. The current account's isolated port `65063` was healthy, and `@capafy.skills8m4q2z/reels/` exposed the verified `DbgsvEbo5kd` link with a grounded live view counter. RED tests then required account-specific `(handle, port)` routing and unavailable-metric preservation; GREEN sync/IG suite `13 passed` (`10922adbc`). The repaired immediate kickstart succeeded: metrics `19 -> 20`, events `254 -> 255`, and the new canonical snapshot records `views=121` for `https://www.instagram.com/reel/DbgsvEbo5kd/`; likes/comments were not rendered and remain absent rather than zero. The live reader now prioritizes the verified current terminal, uses its registry port/profile grid, and never turns unavailable engagement into zero.

#### P0 execution log

| Task | Status | Verification evidence | Commit |
|---|---|---|---|
| 1. Reporting contract | Verified | `python3 -m py_compile .../capafy_outcome.py`; `python3 -m pytest -q .../test_capafy_outcome.py` → `8 passed in 0.39s`; RED was `8 failed` before implementation | `548b382e1` |
| 2. Incident identity | Verified | RED: 4 incident tests + 2 sidecar assertions failed; GREEN: outcome `12 passed`, self-fix `23 passed`, Capafy loop `7 passed` | `c73d53b63` |
| 3. Repair closure monitor | Verified | RED: monitor absent, 15 contract failures; GREEN: monitor integration `19 passed`, outcome regression `12 passed`, plist `OK` | `59b39d0a4` |
| 4. Builder handoff | Verified | RED: handoff/probe absent; GREEN: Builder integration `17 passed`, outcome `12 passed`, self-fix `23 passed`, loop `7 passed` | `f78446b62` |
| 5. Marketer handoff | Verified | RED: 17 missing-handoff failures; GREEN: Marketer `23 passed`, related pytest `22 passed`, account lifecycle `38 passed` | `cda11e4be` |
| 6. 09:30 report | Verified | RED: unsupported `company_state`; GREEN: report/outcome `13 passed`, account lifecycle `38 passed`, source+installed plist lint `OK`; Task 7 then verified the installed `09:30` job with `runs>=1` and latest exit `0` | `a6139d48b` |
| 7. Watchdogs + end-to-end proof | Verified | RED: scheduler-only health, overdue retries, repaired-but-unverified incidents, and older stale incidents were not enforced. Final GREEN: combined pytest `22 passed`; outcome monitor `19`; Builder `17`; Marketer `23`; health shell `5`; loop `7`; self-fix `23`; account lifecycle `38`; shared Telegram pytest `9` plus unittest `3`. Runtime after explicit kickstart: health watchdog `runs>=7`, outcome monitor `runs>=34`, goal monitor `runs>=1`; all latest exit `0`; intervals `300s`/`60s`, brief at `09:30`. Production reconciliation: Builder Telegram `5063`; incident `capafy-builder-20260801T131506Z-062735e9` reached `verified` and delivered exactly-once closure Telegram `5065`. | `1b9729ba4` |

#### P0 final runtime evidence

The live Builder outcome recovered **Portfolio Tracker — Daily Position Review** (`9480246345`) and verified remote status `1`, skill/config presence, and the review URL below. Telegram delivery `5063` contains that successful terminal outcome. The browser-ownership collision was then reconciled under one incident id through `detected -> repair_started -> repaired -> verified`; the outcome monitor delivered the following closure as Telegram message `5065` and stored its terminal delivery key, so later monitor passes remain silent:

```text
Capafy incident resolved — no action needed
The Builder could not submit because browser ownership collided.
Separated browser ownership, reacquired the correct session, resumed the same submission, and verified the remote result.
Recovered skill: Portfolio Tracker — Daily Position Review (9480246345)
Verified remote state: status 1; skill/config confirmed
Evidence: https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review
Lifetime gross: $9.99
Pending seller balance: $8.00
Realized bank payout: $0.00
MRR: $0.00
Model/tool cost: $4.78
Contribution after recorded cost: -$4.78
Next: Watch for approval and hand the public listing to Marketing
```

The same production reconciliation rendered the 09:30 brief from machine state without using scheduler presence as a business result:

```text
Capafy — Consolidated company state, 2026-08-01
Products: 27 online, 2 under review, 1 draft, 1 rejected.
Sales: 1 lifetime order / $9.99 gross.
Pending seller balance: $8.00
Realized bank payout: $0.00
MRR: $0.00
Model/tool cost: $4.78
Contribution after recorded cost: -$4.78
Instagram @no-active-account — Calendar age: day 0. The posting session is not established. Ban status: unproven.
Marketing is scheduled; no public post is verified.
Latest Builder evidence: https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review
Dashboard: https://capafy-skills-daily.netlify.app
```

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
- Remove synthetic warmup and permit one immediate original publish probe after independent session verification.
- Reserve `live` for a verified public content URL.
- Implement the explicit account lifecycle and immediate replacement transition.
- Add a Marketing outcome gate: public URL or an explicit account/publish blocker.

**Done when:** a fresh browser-owned lifecycle immediately reaches one verified public original Reel, retains its owner session, and Telegram contains the Reel, skill, and campaign URLs.

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
8. Account health distinguishes session readiness, public live state, account-status signals, and reach health; calendar age and synthetic activity are not health evidence.
9. Every hosted product has a hard loss cap and measurable contribution margin.
10. The next product and marketing action are chosen from fresh evidence and prior experiment outcomes.
11. Routine operation, account replacement, retries, and repair require no babysitting.
12. A full seven-day run completes without a silent failure or contradictory report.
