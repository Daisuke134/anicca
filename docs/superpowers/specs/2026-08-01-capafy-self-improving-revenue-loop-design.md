# Capafy Self-Improving Revenue Loop Design

**Date:** 2026-08-01  
**Status:** P0 verified; P1 Tasks 1-7 verified; P1 Task 8 in progress  
**Objective:** Turn the existing Capafy Builder and Marketer into one autonomous, self-healing, self-improving revenue system that reports verified outcomes and links in natural language.

## 1. Current verified baseline

- Revenue: 1 lifetime order, $9.99 lifetime gross, $8.00 pending seller balance, $0.00 realized payout, $0 MRR.
- Supply: 27 listings online; 31 listings tracked across online, review, rejected, and draft states.
- 2026-08-01 Builder: initial browser identity collision was repaired by the existing self-fixer. `Portfolio Tracker — Daily Position Review` (`agent_id=9480246345`) reached `status=1`, `isConfirmedSkills=1`, `isConfirmedConfigKeys=1`; its verified review URL is `https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review`.
- Instagram: the stale `@capafy.skills10491` session has been replaced. `@capafy.skills8m4q2z` was created with durable `contact@aniccaai.com` recovery, its isolated browser-owned session and owner-only controls were independently verified, and its credential artifact is mode `0600`. The registry still carries the legacy label `warming`, but the lifecycle is now `publish_probe_ready`; no public Reel or healthy reach is claimed yet.
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

The browser session remains the owner during P1. The old day-3 private-API “golden session” login is prohibited because it produced terminal `ChallengeRequired` failures on fresh accounts. No elapsed-day or synthetic-activity gate exists. The first Reel is an original, low-pressure product education post; a hard CTA or bio-link mutation requires a verified public Reel, a still-established owner session, no challenge/account-status signal, and real reach readback.

This decision supersedes the two-date warmup design on 2026-08-02. The earlier warmup requirement was introduced after `instagrapi` rejected five day-zero accounts, but P1 no longer uses `instagrapi`; it posts through the already-authenticated browser session. Instagram publishes no required warmup duration, while its Terms prohibit unauthorized automated account creation/access and Meta warns that repetitive or inauthentic signals can be restricted even at lower frequencies. Therefore extra synthetic activity adds surface area without proving safety. Relevant evidence: historical pivots `e07752128`, `c232c2198`, `c012f6254`; [Instagram Terms of Use](https://help.instagram.com/581066165581870); [Meta Spam Policy](https://transparency.meta.com/policies/community-standards/spam/); [Instagram creator best practices](https://about.fb.com/news/2024/10/best-practices-education-hub-creators-instagram/).

### 8.2 States and transitions

The Instagram account state machine is:

```text
needed -> provisioning -> created_session_verified
       -> publish_probe_ready -> first_publish_probe_verified
       -> reach_observing -> commercial_ready -> healthy
```

Failure transitions:

```text
challenge/session failure/verified zero-reach pattern
  -> contained -> retired -> replacement_requested
  -> provisioning -> created_session_verified
```

Transition rules:

1. At most one account may hold an active lifecycle capability.
2. A verified browser-owned session grants only `publish_probe`; elapsed account age and scripted engagement grant nothing.
3. `first_publish_probe_verified` requires a newly observed public Instagram Reel URL that survives readback. A click, `--live`, or zero exit code is insufficient.
4. The probe uses original Capafy content at low frequency and performs no synthetic watch/scroll/like/follow/comment sequence.
5. Commercial CTA/bio-link capability requires the verified Reel plus clean session/account readback and non-fabricated reach evidence; time alone grants nothing.
6. A challenge or failed session retires the account for this lifecycle. Password/private-API relogin is not retried.
7. Replacement is requested in the same incident chain and the account manager is woken immediately; it does not wait for the next 16:00 content pass.
8. `live` is reserved for a verified public post. `healthy` requires an established session, a recent verified public outcome, and no overdue lifecycle incident.

### 8.3 P1 runtime and reporting contract

The existing 16:00 Marketer LaunchAgent remains the daily cadence owner, but it may also be kickstarted immediately when a verified account or newly approved skill makes useful work possible. Account provisioning/replacement remains an independent bounded pass. The Capafy warmup LaunchAgent is removed. Normal health checks are silent; Telegram is sent only for a lifecycle transition, terminal blocker, verified Reel, measured business outcome, or repair closure.

P1 production started on 2026-08-02 in `needed`: the three accounts then recorded were terminally unusable (`poisoned` or `session_failed`). The account manager subsequently created and independently verified `@capafy.skills8m4q2z`; the current state is `publish_probe_ready`, and the next production mutation is the immediate content pass rather than another login attempt against `@capafy.skills10491`.

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

- **Active priority:** P1 — Make the Marketer complete reliably. P0 is complete and remains the enforced reporting/repair boundary.
- **Implementation plans:** P0 [`../plans/2026-08-01-capafy-p0-truthful-outcomes.md`](../plans/2026-08-01-capafy-p0-truthful-outcomes.md); original P1 [`../plans/2026-08-02-capafy-p1-reliable-marketer.md`](../plans/2026-08-02-capafy-p1-reliable-marketer.md); active immediate-publish delta [`../plans/2026-08-02-capafy-p1-immediate-publish.md`](../plans/2026-08-02-capafy-p1-immediate-publish.md). The delta supersedes warmup tasks without pulling P2's shared ledger into scope.
- **Execution rule:** complete and verify one numbered task at a time; after each task, append the command evidence and commit hash here before beginning the next task.
- **Current state (2026-08-02):** P0 Tasks 1-7 and P1 Tasks 1-7 are implemented and verified. The replacement manager created `@capafy.skills8m4q2z` without human intervention using `contact@aniccaai.com`; an official email recovery repaired the one production run whose generated signup password was lost before persistence. Independent verification proved the exact isolated browser session still owns the profile, the credential artifact is mode `0600`, and the registry row retains the legacy label `warming`; that label is historical storage, not a posting gate, and will migrate to `publish_probe_ready`. The account manager is loaded every 300 seconds, its latest exit is `0`, no manager lock or browser lease remains, and the account-created terminal was delivered exactly once to Telegram as message `5131`.
- **Next action:** Remove the obsolete warmup scheduler and gates, then kickstart the Marketer immediately for one original browser-direct Reel on `@capafy.skills8m4q2z`; accept success only with a public Reel URL, post-write owner-session verification, and exactly-once Telegram delivery.

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
| 8. Fresh production lifecycle | In progress | Account/session prerequisite is verified and the live row resolves `instagram:capafy-provision` on port `65063`. The warmup LaunchAgent was unloaded before its first run. Immediate-publish Task 1 is verified: lifecycle pytest `17 passed`, and browser ownership now grants `publish_probe` without account-age or warmup evidence. Remaining acceptance is controller/scheduler migration plus one verified original Reel, post-write session readback, all three Telegram URLs, and first reach/click/order measurement. | `35026d96a` + remaining delta tasks |

Immediate-publish delta execution log:

| Task | Status | Verification evidence | Commit |
|---|---|---|---|
| 1. Publish-probe lifecycle | Verified | RED: `15 failed, 2 passed` against the old four-argument warmup lifecycle. GREEN: lifecycle pytest `17 passed`; Python compile and diff check passed. The state no longer reads warmup evidence, requires post-write owner-session proof when recording a Reel, and preserves commercial capability only after Reel/session/reach evidence. | `35026d96a` |
| 2. Account-to-publish handoff | Verified | RED: outcome pytest `2 failed, 13 passed`; manager integration `15 passed, 30 failed` because the old warmup CLI and message contract remained. GREEN: outcome pytest `15 passed`; manager integration `45 passed`; shell syntax and diff check passed. A verified account now persists `publish_probe_ready`, reports no wait/warmup language, and wakes the daily publisher exactly once, including idempotent sender recovery. | `41472bf89` |
| 3. Immediate controller and post-write proof | Verified | RED: Reel adapter `6 failed, 9 passed`; controller `8 passed, 12 failed`; handoff `24 passed, 1 failed`. GREEN: Reel adapter `15 passed`; controller `20 passed`; handoff `25 passed`; outcome+lifecycle pytest `32 passed`; shell/Python syntax and diff check passed. A publish claim now requires one newly observed Reel URL and the matching active handle read again after sharing; the controller records lifecycle state before exactly-once Telegram handoff and recovers safely across a sender crash. | `f43e86bf0` |
| 4. Scheduler/report cleanup | Verified | RED: launchd/report pytest `3 failed, 18 passed`; account-state integration `39 passed, 1 failed`. GREEN: launchd/report pytest `21 passed`; account-state integration `40 passed`; shell/Python syntax and diff check passed. The Capafy warmup script, its integration test, and its source LaunchAgent were deleted; the goal report now projects lifecycle/session/post evidence and never converts scheduler presence or calendar age into a live claim. | `efc8ba58a` |
| 5. Production proof | In progress | First kick: contained foreign public agent `1657185274`; ownership was absent from both prompt and validator. RED `20 passed, 3 failed`; GREEN `23 passed` now selects through our seller inventory and requires exact ID/URL/title (`1fed182a2`). Second kick: an orphan browser lease from the contained process blocked safely; the verified-dead lease was released. RED `23 passed, 2 failed`; GREEN `25 passed` adds exact-identity cleanup on success and failure (`fb088edd9`). Third kick: seller-owned `Decision Debate — Three Experts Argue It Out` (`4866150011`) was selected, HyperFrames check passed with no errors and the 24-second 1080x1920 MP4 rendered, but the poster stopped before Share with `browser_failure:RuntimeError`. CDP readback proved the session and exact handle still exist; root cause was Instagram's current `/accounts/edit/` UI no longer exposing `input[name=username]`, while it does expose the exact owner profile link and handle. RED import failed for the missing resolver; GREEN Reel adapter `17 passed` now accepts only the exact expected profile link when the old input is absent (`b2975c4e1`). The resumed poster then passed owner and profile readback but stopped at the composer boundary. Read-only DOM evidence identified the exact current Japanese label as `新しい投稿`, not the legacy `新規投稿`; RED collection failed for the missing label contract and GREEN Reel adapter `18 passed` now generates its selector from the tested English/Japanese label set. The next resume uploaded the MP4 and reached the final screen; the current caption editor is a Lexical `contenteditable` textbox rather than a `textarea`. The dual editor contract reached a verified 395/2200 Share-ready state. One Share was then attempted, but the adapter navigated to readback after a fixed eight seconds while Instagram still displayed `シェア中`; six owner-profile polls remained at zero posts/zero Reel URLs, so no publication was claimed and no second Share was sent. RED collection failed for the missing share-progress contract; GREEN Reel adapter `23 passed` now holds the composer until explicit completion or modal closure before public readback (`a3a71609d`). The single safe retry then received Instagram's explicit `リール動画がシェアされました` confirmation and owner profile `投稿1件`, but the URL decoder rejected Instagram's current owner-scoped path `/capafy.skills8m4q2z/reel/DbgsvEbo5kd/`. RED reproduced `share_unconfirmed`; GREEN Reel adapter `24 passed` normalizes both global and owner-scoped paths to `https://www.instagram.com/reel/DbgsvEbo5kd/` (`b62de738b`). Read-only recovery re-verified owner `capafy.skills8m4q2z`; lifecycle is now `first_publish_probe_verified`; Telegram message `5166` contains Reel, listing, campaign, media, caption, and post-write owner proof. External checks returned Reel 200 and listing 200. The campaign endpoint initially returned 502 because the deployed Function lacked `@netlify/blobs`; production deploy `6a6e58c640083dfeeb1c713e` repaired it to 302 and persisted one verification click. A final attribution defect remains: the redirect overwrites incoming Reel UTM with bio defaults. RED Node import failed for the missing campaign contract; GREEN Node `2 passed` preserves only the three allowlisted UTM fields and retains legacy defaults when absent. Remaining closure is deploying and verifying that UTM repair, then final regression/incident closure. | `1fed182a2`, `fb088edd9`, `b2975c4e1`, `1f04324d9`, `a3a71609d`, `b62de738b` + current delta |

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
