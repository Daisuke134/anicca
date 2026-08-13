# Capafy Self-Improving Revenue Loop Design

**Date:** 2026-08-01  
**Status:** Production incident active. Revenue/reporting truth, wrong-owner browser containment, and future incident/notification deduplication are restored; four historical active incidents remain, browser reauthentication and autonomous Builder action selection are not verified.
**Objective:** Turn the existing Capafy Builder and Marketer into one autonomous, self-healing, self-improving revenue system that reports verified outcomes and links in natural language.

## 1. Current verified baseline

### 1.1 Production truth observed 2026-08-13 JST

- **Capafy server money truth:** 5 lifetime orders, of which 2 are paid; $19.98 lifetime gross; $0.00 refunds. Paid events are $9.99 on 2026-06-23 and a $9.99 returning-buyer order on 2026-08-08. The server also reports three zero-dollar orders on 2026-08-05, 2026-08-10, and 2026-08-12. Their commercial meaning is unknown until product/order evidence exists; do not label them trials or subscriptions by inference.
- **Payout truth:** `$8.00 balancePayout`, `$6.40 balancePending`, `$0.00 balanceConfirmed`, and `$0.00 totalPayout`. Field names must be rendered with their Capafy semantics; no bank payout is realized.
- **Local money truth is reconciled and projected:** `skills/self/capafy-loop/state/capafy-earn-ledger.jsonl` contains all five dated server rows: 5 orders / 2 paid / $19.98 gross / $0 refunds, including zero-dollar orders on 2026-08-05, 2026-08-10, and 2026-08-12 without inferred commercial meaning. Telegram `15774` and the public `/company/` page now render the same totals; money is fresh while inventory, account, Marketing, and cost remain visibly stale.
- **Portfolio truth:** authenticated `GET /agent/agents` returns 32 rows: 21 `online`, 9 `review_rejected`, and 2 `draft` (`agent_ids_sha256=ca79da6481723d2bf59034770beacf86c7bfde6b99a1a1bb848ccaebb51190d6`). The decisive split is not the status total: exactly five rejected first versions have `hasOnlineVersion=false`; four rejected updates and both drafts have `hasOnlineVersion=true`. A prior fully valid `POST /agent/agents/addAgent` was rejected by Capafy's backend with `A maximum of 5 unlisted agents is allowed`. The exact match between five never-online Agents and the backend's five-unlisted gate is strong account-specific evidence that those first-version rejections still occupy creation capacity until they are approved/listed or removed; it is not evidence that all rejected updates or all drafts consume the gate. Capafy's public Publisher Guide confirms `Approved → live and purchasable` and `Rejected → revise and resubmit`, but does not say that rejection itself frees capacity. The operating queue is therefore: repair/resubmit the five never-online rejected Agents sequentially, keep at most five first-version submissions in review, and create a new Agent only after authenticated readback shows fewer than five never-online Agents and the platform accepts `addAgent`.
- **Builder runtime:** `ai.anicca.capafy-loop-daily` now reconciles server money and canonical events before its `CAP_FULL` branch, then exits 0 without invoking the model or `addAgent`. The remaining `CAP_FULL` action dead end and missing daily owner report are handled by later queue items; exit 0 alone is still not a verified business outcome.
- **Goal/report runtime:** `ai.anicca.capafy-goal-monitor` still has only its 09:30 schedule, but production runs 7 and 8 both exited 0. Run 7 delivered Telegram `15774` with 5 orders / 2 paid / $19.98 gross; run 8 preserved the canonical ledger, delivery state, and generated dashboard byte-for-byte and sent no duplicate. There is no hourly owner-report job and no daily-close job in production.
- **Outcome runtime:** `ai.anicca.capafy-outcome-monitor` wakes every 60 seconds and its verified consecutive wakes exit 0 without new immutable-event conflicts or duplicate notification. This is an incident watcher, not an hourly report scheduler.
- **Health runtime:** the source and installed `ai.anicca.capafy-loop-healthcheck` plist specify a 300-second interval, but the job is not loaded. Its health log is stale. The system cannot currently claim good watchdog coverage.
- **Marketing runtime:** `ai.anicca.capafy-ig-marketing-daily` runs at 16:00, has run 3 times, and last exited 2. Its latest deterministic result is `active Instagram browser tab is missing`; the log also contains browser-lease contention and the same stale incident event conflict.
- **Instagram durable evidence:** lifecycle state still identifies `@capafy.skills8m4q2z` as `commercial_ready`, with post-write owner proof and public Reel `https://www.instagram.com/reel/DbhCWLhorxy/`. This does not prove that a usable browser tab exists now. Durable lifecycle state and live browser truth currently disagree.
- **No-human status:** no human action is intrinsically required. The implementation is incomplete: deterministic reconciliation and repair must converge from fresh external truth before the system can be called self-healing.

### 1.2 Historical verified foundation

- The Builder and Marketer ownership boundary, canonical event model, Instagram browser-direct publication path, public URL verification, company projection, and outcome/incident primitives were previously built and tested.
- The last verified public Instagram asset remains `https://www.instagram.com/reel/DbhCWLhorxy/`, promoting Capafy skill `5051239796`.
- `YouTube Script Writer` is only a historical Capafy product/candidate name. It is not a YouTube publishing plan and must never be hardcoded into the loop or treated as Codex's product-building assignment.
- OpenRouter had approximately $4.777 measured lifetime usage in the last verified projection. It must be re-read before any current cost claim.

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

### 4.3 Execution ownership — no operator takeover

- The **Builder loop**, not Codex and not the human owner, owns routine catalog work end to end: demand research, opportunity selection, skill creation or revision, packaging, provider migration, submission, review polling, publication verification, and the next product decision.
- The **Marketing loop** owns distribution after a verified listing handoff. Instagram is the currently verified live channel. It may add another channel only from evidence and within its declared tools and budgets; a product name containing `YouTube` does not authorize or imply YouTube publishing.
- **Codex/session work** is limited to designing, testing, deploying, and repairing the reusable loops and their deterministic tools. A bounded live operation is allowed only as an explicitly approved bootstrap or recovery test with a named business observable. It must end by returning ownership to the scheduled loop; it must not become a product-by-product operating queue.
- Individual products in execution logs are historical verification evidence, not instructions for Codex to keep operating the Capafy catalog manually.
- The human owner receives verified outcomes and evidence links. Routine product, posting, repair, and optimization decisions require no approval and no babysitting.

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

### Daily commercial output contract

“Publish” has three different meanings and reports must never combine their counts:

| Output | Schedule and hard maximum | Selection rule | What counts |
|---|---|---|---|
| Builder commercial action | One bounded 08:10 JST pass; remote mutations run sequentially with a receipt before the next mutation | First drain review outcomes, then repair/resubmit eligible never-online rejections, then fill newly open first-version capacity with evidence-backed products; otherwise choose one optimization, Marketing handoff, or no-op | Every mutation has one durable action key and verified remote receipt |
| New Capafy product | Zero while five never-online Agents occupy the account gate; after a slot opens, submit only enough differentiated products to restore the first-version review queue to five, never more than five submissions in one day | Demand evidence, recurring buyer input, stale-in-a-week value, and positive bounded unit economics; no hardcoded niche, purchase model, or price | A remote under-review receipt, never a local draft |
| Never-online rejected repair | Process sequentially until the first-version review queue reaches five or no safe repair remains; hard maximum five resubmissions in one day | Use the exact platform rejection reason and change only the rejected surface | The same Agent has one verified resubmission receipt; immediate replay performs no second resubmission |
| Existing-online product update | At most one measured update per day; it does not share the first-version product count but still requires its own review | One registered experiment; change one measured surface | The existing public version remains sellable while one new version is reviewed |
| Marketing content | One candidate and at most one public product-education Reel in the 16:00 JST pass | One seller-owned listing, one registered content hypothesis, one original 9:16 asset | A public Reel URL plus post-write owner proof; a generated file or rejected share counts as zero published |
| Owner reporting | Hourly at minute 00, morning at 09:30 JST, and daily close at 23:50 JST | Report the latest canonical state; reports perform no product or content mutation | One deduplicated Japanese Telegram receipt per reporting period |

The loop optimizes paid recurring contribution, not daily output volume. Publishing one product or one Reel provides no revenue guarantee. Revenue projections require observed conversion, active recurring customers, renewal, churn, fees, refunds, and hosted cost; until those exist, the report states actual `$0 MRR` rather than extrapolating activity.

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

Money is rendered in two non-overlapping lanes:

- **One-time / Download:** order count, one-time gross, platform fee, seller-hosted inference cost, estimated or observed contribution, pending balance, and realized payout. `MRR change` is always `$0.00` for this lane.
- **Recurring / hosted:** new subscription or renewal, billing interval, charged gross, recognized recurring revenue, new-MRR movement, total MRR, platform fee, observed/estimated hosted cost, and contribution. A renewal adds recurring revenue but does not add new MRR; a cancellation reduces MRR; a refund reverses only the revenue lane to which the original order belonged.

Daily and lifetime totals never combine one-time revenue with MRR under a generic `revenue` label. MRR normalization is explicit: monthly price as-is, weekly price multiplied by `52/12`, and annual price divided by `12`. Projected fee/cost/contribution is labeled `estimated`; only platform settlement and measured provider/tool charges are labeled `observed` or `realized`.

### 9.2 Scheduled cadence

| Time JST | Report |
|---|---|
| 08:00 | Morning CEO brief: yesterday's one-time gross/contribution, recurring recognized revenue, new/total MRR, pending/realized payout, cost, funnel, incidents, and today's Builder/Marketer objectives. |
| 08:10 | Builder starts silently. |
| On Builder terminal state | Immediate verified listing result with real URL. |
| Every hour at `HH:00` | One period-keyed owner snapshot rendered from a fresh server reconciliation. It must arrive once per clock hour even when unchanged; an unchanged report says so plainly. It includes current money, Builder/Marketer state, data freshness, active repair, next automatic action, and all available public links. |
| 09:30 | Consolidated company state after any Builder repair. This is an additional checkpoint, not a substitute for the hourly report. |
| 16:00 | Marketer starts silently. |
| On Marketing terminal state | Immediate content/post result with public URL, media, caption, promoted listing URL, and attribution link. |
| 20:00 | Only if content was published: first performance snapshot with views, clicks, buyers, and interpretation. |
| 23:50 | Daily close: one-time and recurring lanes shown separately, new/total MRR, pending/realized payout, model/tool spend, contribution, experiment result, and next automatic action. |

Event-driven immediate reports: order, cancellation, refund, payout, listing approval/rejection, public content, account challenge/replacement, cost breaker, and verified repair closure.

Delivery idempotency is scoped by report period, not by identical business content. The hourly key is `capafy:owner-hour:{YYYY-MM-DDTHH-JST}` and the daily key is `capafy:owner-day:{YYYY-MM-DD-JST}`. Therefore an unchanged `CAP_FULL` or zero-sales state cannot suppress the next hour or next day. Event-driven business outcomes retain stable event-based keys and remain exactly once.

Before rendering any scheduled report, the reporting controller must reconcile Capafy sales trend in chunks of at most seven days, payout info, remote inventory, latest Builder/Marketer terminals, Instagram live-session evidence, costs, and incident state. A failed source is shown as stale/unknown with its last verified timestamp; an old value is never presented as current.

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

### 9.7 Exact example: recurring subscription sale

> **Capafy sale — real money event**  
> **Cold Email Writer — Get Replies, Not Templates** received one new `$5.99/month` subscription.
>
> Skill: https://capafy.ai/agent/5051239796
> Attributed source: Instagram Reel
> Source content: https://www.instagram.com/reel/DbhCWLhorxy/
>
> **Recurring lane**
> Charged today: `$5.99` gross
> New MRR: `+$5.99`
> Total MRR: `$5.99`
> Estimated platform fee: `$1.20`
> Estimated hosted model cost for the included 60 requests: `$0.27`
> Estimated monthly contribution: `$4.52`
> Pending seller balance: unchanged until platform reconciliation
> Realized bank payout: unchanged until Capafy pays it
>
> **One-time lane today:** `0 orders / $0.00 gross`
>
> I will now increase allocation to this product and test the next creative without changing the winning offer simultaneously.

### 9.8 Exact example: one-time Download sale

> **Capafy sale — one-time Download purchased**
> **Amazon Listing Images — 7-Slot Kit** received one `$49.00` one-time order. The buyer runs the downloaded package; this is not a hosted subscription.
>
> Download: https://capafy.ai/agent/5648342153
> Attributed source: Instagram Reel
> Source content: {verified_reel_url}
>
> **One-time lane**
> Orders today: `1`
> One-time gross today: `$49.00`
> Estimated platform fee: `$9.80`
> Seller-hosted inference cost: `$0.00`
> Estimated contribution before support/refunds: `$39.20`
> Pending seller balance: unchanged until platform reconciliation
> Realized bank payout: unchanged until Capafy pays it
>
> **Recurring lane**
> New MRR: `$0.00`
> Total MRR: unchanged
>
> I will measure delivery/refund status and increase Download promotion only after the order and attribution remain verified. I will not report this purchase as MRR.

### 9.9 Exact example: unresolved external blocker

> **Capafy incident remains unresolved — automatic retry scheduled**
> Instagram returned a platform challenge while establishing the posting session for `@capafy.skills10491`. I stopped retries to avoid worsening the account, preserved the evidence, and started the replacement-account workflow.
>
> Attempts completed: session verification, one clean reattach, challenge confirmation.
> Current containment: no posting or login retries on the affected account.
> Next automatic action: create and independently verify the replacement account, then run one immediate original publish probe.
> Human action required: none. I will send the replacement handle when creation is verified.

### 9.10 Exact example: daily close with both revenue types

> **Capafy — Daily close, Aug 2**
>
> **One-time / Download today**
> Orders: `1`
> Gross: `$49.00`
> Estimated platform fee: `$9.80`
> Seller-hosted inference cost: `$0.00`
> Estimated contribution before support/refunds: `$39.20`
>
> **Recurring / hosted today**
> New subscriptions: `1`
> Renewals: `0`
> Cancellations: `0`
> Charged gross: `$5.99`
> Recognized recurring revenue: `$5.99`
> New MRR: `+$5.99`
> Total MRR: `$5.99`
> Estimated hosted cost: `$0.27/month` at full included usage
> Estimated recurring contribution: `$4.52/month`
>
> **Cash status**
> Pending seller balance: `{verified_pending_balance}`
> Realized bank payout today: `{verified_realized_payout}`
>
> **Funnel today**
> Instagram views: `{verified_views}`
> Attributed clicks: `{verified_clicks}`
> Attributed one-time buyers: `1`
> Attributed subscription buyers: `1`
>
> Decision: continue the winning Download creative and hold the hosted offer constant until the next measured conversion window. No human action is required.
> Dashboard: https://capafy-skills-daily.netlify.app

## 10. User experience

The owner uses Capafy at three levels:

1. **Telegram:** the daily operating interface. It shows decisions, verified outcomes, links, money, repair closure, and the next autonomous action.
2. **Public web dashboard:** a readable company page showing products, live content, gross/pending/realized revenue, MRR, costs, incidents, experiments, and last update. It is generated from the event ledger and is safe to open source.
3. **Deep evidence:** each Telegram/dashboard item links to the real marketplace listing, public post, campaign URL, or review evidence. Technical logs remain available but are not the normal UX.

The owner does not approve routine choices. Human escalation is reserved for legal consent, unavailable credentials, irreversible financial commitments beyond declared caps, or a platform action that explicitly requires a human.

### 10.1 Ideal post-implementation experience

```text
                         CAPAFY — NO-HUMAN REVENUE LOOP

  External demand signals                 Canonical company ledger
  marketplaces / search / social          products / content / money / costs
              │                                      ▲
              ▼                                      │ verified events only
  ┌──────────────────────┐                 ┌──────────┴───────────┐
  │ BUILDER              │                 │ MARKETER             │
  │ research demand      │──listing URL───▶│ choose offer + angle │
  │ build/test package   │                 │ make original asset  │
  │ price with hard cap  │                 │ publish + link       │
  │ ship or repair       │                 │ measure + attribute  │
  └──────────┬───────────┘                 └──────────┬───────────┘
             │ failure                                  │ failure
             ▼                                          ▼
       diagnose → repair → rerun original observable → verify
                              │
                              ▼
                  ┌────────────────────────┐
                  │ OWNER EXPERIENCE       │
                  │ Telegram: actions now  │
                  │ Web: portfolio truth   │
                  │ Links: listing/content │
                  │ Money: one-time ≠ MRR  │
                  │ Errors: fixed/blocked  │
                  └────────────────────────┘
```

The normal owner journey after implementation is:

```text
08:00  Morning brief
       "Yesterday: $X one-time, $Y recurring revenue, $Z total MRR, cost $C. Today: these two actions."

HH:00  Hourly owner snapshot
       "Capafy server: N orders / $G gross. Builder: state + next action. Marketer: state + URLs.
        Reconciliation age: M minutes. Repair: none, or cause + attempted repair + next retry."

During the day — outcome-triggered only
       Builder shipped       → product/review URL + price + next automatic step
       Marketer published    → public post URL + product URL + campaign/attribution ID
       Sale/renewal/refund   → exact product, source, one-time or recurring lane, contribution
       Failure repaired      → cause + repair + rerun evidence; no stale error left as final truth
       External hard blocker → honest blocker + automatic retry time; no fake success

23:50  Daily close
       products shipped | content published | traffic | orders | one-time gross/contribution
       new MRR | renewed MRR | churn/refunds | total MRR | provider/platform cost | tomorrow

Any time
       Open the web dashboard → same projection as Telegram, with clickable evidence links.
```

There is no per-minute Telegram noise. Telegram sends one readable hourly snapshot, verified business outcomes as they happen, repair closure when state changes, and one daily close. Heartbeats and stack traces stay out of the owner experience; unresolved technical evidence is translated into cause, impact, repair already attempted, verification state, and the next automatic retry.

## 11. Revenue architecture

### 11.1 Product packaging

- Recurring changing input -> subscription.
- Value proportional to records/results/actions -> usage or pay-per-event.
- One completed installation/methodology -> one-time or BYOK download.
- High variable model cost -> BYOK, usage pricing, or hard low cap; never an uncapped flat subscription.
- Default to one-time/BYOK Download when the buyer can receive the complete value without seller-hosted execution. This removes seller-side inference cost and makes contribution easier to bound; platform fees, support, refunds, maintenance, and IP leakage remain real costs.
- Keep or create a hosted subscription only when zero-setup execution or genuinely recurring fresh input creates renewal value and worst-case package economics remain positive under a hard loss cap.
- Use a barbell where evidence supports it: a separately listed Download offer for ownership/low variable cost and a hosted offer for convenience/recurring use. Capafy does not permit mutating an already-online `run_online` Agent into Download, so the Download side must be a distinct product rather than a destructive type conversion.
- Never report one-time sales as MRR. Downloads fund the loop and validate demand; only recurring hosted/update/membership revenue enters MRR.

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

The authoritative execution order from the current `$0 MRR` state to `$10K MRR` is the atomic queue in section 12. Section 11 defines the commercial gates; section 12 alone defines what runs next. No second roadmap, product-name queue, or manually operated product checklist may compete with it.

### 11.3 Path to $10M MRR

$10M MRR cannot credibly come from manually accumulating low-price skills. At $30 ARPU it needs about 333,000 subscribers; at a 20% marketplace take rate it needs $50M monthly GMV; at $10,000/month enterprise ACV it needs 1,000 customers.

The business must change shape:

1. **$10K -> $100K:** productize winning skills into reliable APIs/SaaS and add higher-value business plans.
2. **$100K -> $1M:** sell the proven Skill Selling Agent to other creators and companies; charge subscription plus usage/revenue share.
3. **$1M -> $10M:** become distribution and monetization infrastructure: marketplace adapters, billing, metering, evaluation, security, attribution, and autonomous portfolio management for third parties.

The $10M product is not an individual skill. It is the platform that continuously discovers, builds, distributes, markets, measures, repairs, and improves revenue-producing agent products.

## 12. Remaining implementation backlog

### Execution status

- **Active priority:** restore truthful revenue and owner observability first, then make repair converge, then resume autonomous Builder/Marketer improvement. Codex must repair the reusable system only; it must not operate products or post content in place of the scheduled loops. `YouTube Script Writer` remains only a historical product name, never a YouTube channel plan or hardcoded queue item.
- **Implementation plans:** active Item 9c [`../plans/2026-08-13-capafy-browser-ui-reauthentication.md`](../plans/2026-08-13-capafy-browser-ui-reauthentication.md); completed Item 9b [`../plans/2026-08-13-capafy-incident-notification-convergence.md`](../plans/2026-08-13-capafy-incident-notification-convergence.md); completed browser-boundary Item 9 [`../plans/2026-08-13-capafy-marketing-browser-recovery.md`](../plans/2026-08-13-capafy-marketing-browser-recovery.md); completed Item 8 [`../plans/2026-08-13-capafy-business-watchdog.md`](../plans/2026-08-13-capafy-business-watchdog.md); completed Item 7 [`../plans/2026-08-13-capafy-morning-monitor-restore.md`](../plans/2026-08-13-capafy-morning-monitor-restore.md); completed Item 6 [`../plans/2026-08-13-capafy-report-schedules.md`](../plans/2026-08-13-capafy-report-schedules.md); completed Item 5 [`../plans/2026-08-13-capafy-japanese-owner-reporter.md`](../plans/2026-08-13-capafy-japanese-owner-reporter.md); P0 [`../plans/2026-08-01-capafy-p0-truthful-outcomes.md`](../plans/2026-08-01-capafy-p0-truthful-outcomes.md); P1 [`../plans/2026-08-02-capafy-p1-immediate-publish.md`](../plans/2026-08-02-capafy-p1-immediate-publish.md); verified P2 [`../plans/2026-08-02-capafy-p2-shared-revenue-ledger.md`](../plans/2026-08-02-capafy-p2-shared-revenue-ledger.md); active P3 [`../plans/2026-08-02-capafy-p3-portfolio-quality.md`](../plans/2026-08-02-capafy-p3-portfolio-quality.md), governed by [`2026-08-02-capafy-p3-portfolio-quality-design.md`](2026-08-02-capafy-p3-portfolio-quality-design.md).
- **Execution rule:** complete and verify one numbered system task at a time; after each task, append command evidence and the commit hash here. Product-level operations are emitted and executed by the Builder loop, not expanded into a Codex operating checklist.
- **Current state (observed 2026-08-13 JST):** Capafy server truth, local money ledger, canonical projection, scheduled Japanese reports, and public company dashboard agree at 5 orders / 2 paid / $19.98 gross / $0 refunds / $0 MRR. Inventory is 21 online / 9 review-rejected / 2 draft. Durable launchd jobs schedule hourly `Minute=0`, daily close `23:50`, morning report at `09:30`, and business health every 300 seconds. Builder still exits 0 on `CAP_FULL`. The authenticated `@capafy.skills8m4q2z` session is restored at guarded live port `49938`; exact-owner verification, the sole active registry row, and lifecycle all agree at `publish_probe_ready`, `session_established=true`, `capability=publish_probe`, and `replacement_requested=false`. Live Account Status says removed content currently has no effect, all features are available, and the account is visible to people under 18, so no ban or complete distribution block is observed. The repaired Marketer selected seller-owned listing `7785270416`, generated one validated 27-second 1080×1920 product-education video, then Instagram explicitly rejected the single share attempt with `投稿をシェアできませんでした`; no Reel was published. Profile readback remains exactly two Reels at 190 and 184 views. Resolver incident `536fc25c` is verified; platform incident `332a5e9e` remains one typed unresolved challenge with retry `2026-08-13T15:54:48Z` and Telegram `16331`. The canonical ledger has 428 rows at SHA-256 `8be2151901bf9323b735c2d8351b945f9b9c5b837660922ec90d86a3d60bbb3f`.
- **Item 1 production readback:** the first launchd deployment attempt failed closed before inventory/model execution after four missing sales events were safely appended; root cause was an all-history payout timestamp rewrite conflicting with the immutable legacy `2026-07-18` balance event. Commit `3097b0b58` preserves legacy timestamps, persists new daily payout timestamps at UTC date midnight, and syncs the durable source ledger directly. After deployment at `f18ac7651`, existing launchd runs 6 and 7 both exited 0 with `CAP_FULL`, 5 orders / $19.98 gross, payout `8.0 / 6.4 / 0 / 0`, and no model or `addAgent`. The second run preserved the source-ledger, 398-row event-ledger, and Builder-result SHA-256 values exactly.
- **Historical repair evidence:** the `@capafy.skills5595` provisioning incident was previously verified closed by replacement account `@capafy.skills8m4q2z`, owner-session proof, and Reel `https://www.instagram.com/reel/DbgsvEbo5kd/`. Commit `7e5f2d3bd` and Telegram `5526` proved that earlier recovery once. Current 2026-08-13 logs nevertheless show old Builder/Marketer incident identities conflicting again and a terminal phase attempting `verified -> unresolved`; therefore the old closure is evidence, not current health.
- **Reference-loop audit:** Clipping and Life Manager are useful architectural references, but neither is currently a healthy gold standard. Clipping completed its last business pass on 2026-08-01 18:12 JST, then its scheduled wrapper ended `last exit=1` after Telegram DNS delivery became unknown; no evidence supports calling the whole wrapper healthy. Life Manager has ended `last exit=1` on 2026-07-31, 2026-08-01, and 2026-08-02 before its agent/posting stage because its new state root lacks `daily-render-state.jsonl` while the legacy copy remains under `~/.openclaw/state/lm-video/`. Its last successful agent evidence and heartbeat are 2026-07-30. The pattern worth sharing is artifact → owner-verified publish → public URL → measurement ledger → natural-language Telegram; scheduler presence or code completion is never the business outcome.
- **Next action when implementation resumes:** execute only `10.1`: move Builder's `CAP_FULL` exit after reconciliation and action selection so a full catalog can still choose revenue work. The typed Instagram platform challenge remains observable and retryable; do not create another account or bypass the platform.

### Remaining atomic implementation to-do list (execute in this exact order)

Previous incident closure, company-projection parity, Instagram publication, portfolio snapshot, packaging schemas, and a bounded packaging decision are historical foundations. Current production has regressed in reconciliation, reporting, and incident convergence, so the authoritative queue below begins by restoring those observables. No item means that Codex should operate an individual Capafy product manually.

#### Current atomic queue — authoritative order

Only the first unchecked item is active. Every item below is one state transition with one observable completion gate. Implementation items end with the smallest relevant static/focused check, one real readback, spec status, commit, and push; revenue milestone items end with canonical money evidence. No TDD/RED ceremony, broad review cycle, new abstraction, new service, or unrelated cleanup is part of an item unless its completion gate cannot be reached without it.

1. **Restore authoritative money reconciliation before every report and every Builder early return.** Change `skills/self/capafy-loop/capafy_earn_reconcile.py`, `skills/self/capafy-loop/capafy-loop-daily.sh`, and `skills/self/capafy-loop/tests/test_capafy_earn_reconcile.py`. Move reconciliation ahead of `CAP_FULL`, preserve zero-dollar orders, backfill at most 90 days in ≤7-day chunks, and upsert payout snapshots idempotently. **Done when:** a fixture and live readback both render 5 orders / 2 paid / $19.98 gross / $0 refunds without duplicating rows, and a second run is byte-equivalent.
   - **Closed:** commits `c7677e0ca`, `b100cc861`, `9249e6b69`, `b5ba5bd85`, and `3097b0b58` are deployed through merge `f18ac7651`. TDD covered the 90-day/7-day bound, same-key upsert, reconcile-before-`CAP_FULL`, fail-closed API validation, finite/typed money values, same-day retry identity, and legacy payout-event compatibility. Parent verification is focused `11 passed`, money loop `7 passed`, Builder `26 passed`, plus compile/shell syntax PASS. Authenticated production launchd runs 6 and 7 both exited 0 after fresh reconciliation, rendered 5 orders / 2 paid / `$19.98` gross / `$0` refunds and payout `8.0 / 6.4 / 0 / 0`, retained the three zero-dollar dates without attribution, and returned `CAP_FULL` before model/`addAgent`; the immediate replay left source ledger, 398 canonical events, and Builder result byte-identical.
2. **Repair canonical event ingestion for newly discovered money.** Change `skills/earn/capafy-marketing/scripts/capafy_event_sync.py`, `skills/earn/capafy-marketing/scripts/capafy_event_adapters.py`, and their focused tests. Emit one stable event per Capafy sales date/order aggregate, including zero-dollar orders without inventing product, subscription, or trial attribution. **Done when:** 2026-08-05, 08-08, 08-10, and 08-12 appear once, retries create no duplicate or conflict, and unknown attribution remains visibly unknown.
   - **Closed without additional production code:** the existing canonical adapter plus Item 1 deployment already satisfy the acceptance contract. Production contains exactly one `order.received` event for each of 2026-08-05, 08-08, 08-10, and 08-12; each uses `correlation_id=null`, an `order_batch` entity, and no public listing URL, so product/subscription/trial attribution remains explicitly absent. Existing launchd replay preserved all 398 event rows and the event-ledger SHA-256 exactly. Parent verification is event-sync `12 passed`, event-store `19 passed`, and compile PASS; Ponytail therefore rejects a redundant implementation or review cycle.
3. **Make the company projection fail closed on stale or contradictory data.** Change `skills/earn/capafy-marketing/scripts/capafy_event_projection.py`, `skills/earn/capafy-marketing/scripts/build_company_dashboard.py`, and projection/dashboard tests. Money totals come from reconciled server events; each source carries `observed_at` and freshness. **Done when:** Telegram and `/company/` show the same 5 / 2 / $19.98 truth, while a stale source is labeled stale instead of silently reused.
   - **Execution dependency:** implement and verify the projection, Telegram renderer, and dashboard against the real canonical ledger before Item 4. The existing production goal-monitor cannot activate those outputs yet because its mandatory `sync-all` stops before projection on the Item 4 immutable incident conflicts. Complete Item 4 next, then return immediately to the existing goal-monitor for Item 3 production closure; do not bypass the loop or treat a manual render as delivery.
   - **Implementation GREEN; production activation pending Item 4:** commits `0b0c8c6ca` and `0c548485b` are deployed through merge `844e785cc`. The projection exposes money/inventory/account/marketing/cost `observed_at` plus `fresh|stale|unknown`, rejects future timestamps as current, and keeps identity stable within one freshness state. Goal-monitor parity now derives upsert-aware 5 orders / `$19.98` and payout `8.0 / 0.0` from the reconciled earn ledger instead of stale `STATE.md`; malformed/missing evidence fails closed. Dashboard visibly labels stale/unknown sources. One fresh review found and the same Luna fixed same-date double counting and future-time freshness; parent verification is 23 passed plus syntax/compile/diff PASS. Real-ledger read-only render shows money fresh at 5 / `$19.98`, with inventory/account/marketing/cost visibly stale. Item 3 remains open only for existing-loop Telegram and `/company/` activation after Item 4 removes the pre-projection incident conflict.
   - **Production activation attempt 1 failed closed:** launchd run 5 completed the repaired canonical sync, appended the one missing Marketer retry occurrence, and verified both older company sync/parity incidents. It then exited 3 without Telegram delivery because the independent incident source retained the legacy equivalent retry `2026-08-07T04:50:52.266822Z` while the canonical event projection rendered `2026-08-07T04:50:52Z`; raw string parity treated the same instant as different and created one new `goal-monitor-projection-parity-mismatch` incident. The ledger is now 406 valid rows and still projects 5 orders / `$19.98`, pending `$8.00`, realized `$0.00`, money fresh, and the other four sources stale. Delivery state remains Telegram `6038` from 2026-08-03. Fix semantic timestamp parity before retrying production; do not mutate the legacy incident by hand.
   - **Production activation attempt 2 reached delivery but exposed the final acceptance gap:** commits `50a6f9a04` and `63af3bf42` are deployed through merge `d190b7dd1`. One fresh adversarial review proved that Python's permissive ISO parser and a missing retry key could bypass fail-closed parity; the same Luna correction now accepts only explicit timezone-aware RFC3339 retry values and requires every incident parity field. Parent verification is Python `251 passed`, compile/shell/diff PASS. Launchd run 6 verified the new parity incident, exited 0, generated projection `6eb6e15e1a7b`, and delivered Telegram `15668`; it renders 5 orders / `$19.98`, pending `$8.00`, realized `$0.00`, money fresh, and four stale sources. It does **not** yet render the independently verified count of 2 paid orders in Telegram or `/company/`, so Item 3 remains open. The current five server rows are each one-order batches, making paid count exactly the two positive-gross batches without inventing meaning for the three zero-dollar orders. For future multi-order aggregates, paid count must be unknown unless the batch carries an explicit paid count; never infer every order paid merely because aggregate gross is positive.
   - **Closed:** paid-order commits `39dd2b4f4`, `38bd7f699`, `57a8cd7c0`, `d1a577512`, and `8372f77a5` are deployed through merge `964f512d7`. The one fresh Sol adversarial review reproduced five Important faults: stale same-date selection and immutable-ID conflict, malformed source-row coercion, projection validation bypass, a missing public-schema field, and renderers accepting paid orders above total orders. The same Luna correction enforces one invariant across source, JSON Schema, canonical event, independent fold, projection, Telegram, and dashboard; immutable same-date revisions receive stable digest IDs and logically supersede without double counting. Parent verification is all marketing Python `296 passed`, schema parse, compile/shell/diff PASS. A production-ledger copy replayed with `appended=0`, `conflicts=0`, and identical 409-row SHA-256, then rendered 5 orders / 2 paid / `$19.98`. Existing goal-monitor run 7 exited 0 and delivered Telegram `15774`; run 8 also exited 0 and preserved ledger, delivery, dashboard JSON, and dashboard HTML byte-for-byte, with zero new stderr or duplicate notification. Netlify production deploy `6a7d7b278885ad94c4220520` returned the canonical URL, and independent `crwl` plus HTTP readback confirmed status 200, projection `e12cba45605a…`, 5 lifetime orders, 2 paid, and `$19.98` at the public `/company/` URL. Money is visibly fresh; inventory, account, Marketing, and cost are visibly stale. Item 3 is crossed off; Item 5 is now the first unfinished queue item.
4. **Fix immutable incident convergence.** Change `skills/earn/capafy-marketing/scripts/capafy_outcome.py`, `skills/earn/capafy-marketing/scripts/capafy_event_store.py`, `skills/earn/capafy-marketing/capafy-outcome-monitor.sh`, and focused tests. A terminal `verified` incident cannot regress to `unresolved`; retries reuse compatible identity or emit a new phase event without overwriting an old event ID. **Done when:** the two current stale incidents converge, the 60-second monitor adds no conflict lines on two consecutive wakes, and last exit 0 corresponds to clean business state.
   - **Closed:** commits `8d690b650` and `1daa2946f` are deployed through merge `c13c7ea3e`. The first and only fresh adversarial review reproduced three load-bearing defects in the initial implementation: a legal phase revisit could reuse an immutable ID, equivalent retry timestamp spellings could disagree in the source digest, and legacy backfill could append seven false terminal occurrences then rewind the current incident projection. The same Luna correction canonicalizes retry time in state/source/identity, persists per-phase occurrence identity, preserves exact legacy occurrences without weakening ordinary conflict rejection, and orders incident projection by business chronology rather than append order. Parent verification is Python `236 passed`, outcome monitor `27/27`, compile/shell/diff PASS. A production 398-row ledger copy appended only the missing current Marketer retry event with zero conflicts, preserved the newer company incident projection, then replayed with `appended=0`, zero conflicts, and identical 399-row SHA-256. Existing production outcome-monitor wakes 5656 and 5657 both ended `last exit=0`, added zero stderr/conflict lines, sent no duplicate notification, and preserved the 398-row production ledger byte-for-byte. Builder remains verified; Marketer remains one truthful, already-notified, convergent unresolved incident with a concrete retry contract. Browser recovery remains Item 9 and is not falsely claimed here.
5. **Create the period-keyed natural-language owner reporter.** Reuse `skills/earn/capafy-marketing/capafy-goal-monitor.sh`; add the smallest renderer/helper only if necessary, plus `skills/earn/capafy-marketing/tests/test_capafy_goal_monitor_report.py`. One source renders hourly, morning, daily-close, and event messages in plain Japanese with money, freshness, Builder, Marketer, repair, next action, Capafy skill URL, Reel/content URL, and dashboard URL. **Done when:** golden fixtures cover healthy, unchanged, stale-metrics, sale, published, repair-closed, and unresolved states; no raw enum, stack trace, internal path, or literal template token reaches Telegram.
   - **Closed:** deterministic reporter commits `e8b0265f0`, `2786983ad`, `ffdfdf3ef`, and `90216887c` are deployed through merge `455424e86`. The only fresh adversarial review reproduced concurrent duplicate sends/lost delivery updates, spoofed sender success, unsafe URL/handle leakage, false event reasons, unsafe state modes, and malformed calendar periods; the same Luna correction added one send critical section, locked atomic ledger updates, strict sender output, source allowlists, semantic event validation, and safe state/calendar validation. Parent verification is all Marketing `358 passed`, adversarial counterexamples `7 passed`, compile/shell/diff PASS. Existing launchd runs 9–11 all exited 0: `hourly:2026-08-13T17` sent Japanese Telegram `15899`; its retry sent nothing and preserved delivery SHA-256 `846a6ca42222ac580ddfd76c5239a195beb0a529ef0a0bd3ffc27105b65789fc`; the unchanged next period `hourly:2026-08-13T18` sent exactly one Telegram `15900`, producing two-row delivery SHA-256 `d812ae6a16c9ffc3dd5b2200eac40e173939b54c039ec1cc6cadfafa2918e4dc`. The final body shows 5 lifetime orders, 2 paid, `$19.98`, freshness, Builder, Marketer, repair/next action, listing, Reel/content, and dashboard URLs in natural Japanese with no forbidden token. The revenue ledger remained 409 rows with SHA-256 `2729ed05e5504f9c6c26f684dca27fd35cdd2bc02d670a4971c0ffd5c6dc023e`; inventory, account, Marketing, and cost remain visibly stale. Item 6 is now the first unfinished queue item.
6. **Install real hourly and daily-close schedules.** Add durable source plists under `skills/earn/capafy-marketing/launchd/` for `StartCalendarInterval Minute=0` hourly reporting and `23:50 JST` daily close, or one tested controller with equivalent wall-clock routing. Update `skills/earn/capafy-marketing/tests/test_capafy_p1_launchd.py` and the installer/readback test. **Done when:** launchctl readback matches source, each hourly/day period sends exactly once, identical business content does not suppress the next period, and Telegram returns real message IDs.
   - **Closed:** source plist commit `c3acfabc8` is deployed through merge `8d170e336`. Parent verification is focused launchd `6 passed`, all Marketing `360 passed`, plist syntax and diff PASS. The only fresh Sol adversarial review returned `ship` with zero Critical/Important findings; one non-blocking Minor about future test strictness was recorded without a second review. Source and installed hourly bytes share SHA-256 `032688ce9d30aaac17d203d017e19039848db20e3ced8bea224e1d6b24036301`; daily-close bytes share `528399bf41099360e44c906455e3428fd3589184b89093a572ecf8a43c158aed`. `launchctl` reads hourly `Minute=0`/`kind=hourly` and daily close `Hour=23, Minute=50`/`kind=daily_close`. The real 19:00 trigger sent Telegram `15920`; its same-period replay preserved delivery SHA `0b9f87cb0a7c55f2c0a112507a8e9fbbbc31ae8ad17ceb87e3162f5186851bd0` and sent nothing. Daily-close run 1 sent Telegram `15921`; same-day run 2 preserved delivery SHA `7d12190937e426713202fe243b69395d13cce7670a35494d51fad481b55a19b2` and sent nothing. All four runs ended exit `0`, both new stderr logs remain empty, the Japanese body shows 5 / 2 / `$19.98`, and the 409-row revenue ledger SHA remained `2729ed05e5504f9c6c26f684dca27fd35cdd2bc02d670a4971c0ffd5c6dc023e`. Item 7 is now the first unfinished queue item.
7. **Restore the existing 09:30 goal monitor.** Change `skills/earn/capafy-marketing/capafy-goal-monitor.sh` and its focused projection parity tests; do not create a second competing report implementation. **Done when:** live kickstart exits 0 twice, the second run is idempotent, delivery state advances from 2026-08-03, and the message contains fresh 5-order truth.
   - **Closed without additional production/test code:** Item 5 already supplied the Japanese morning renderer and period-keyed dedupe, so Ponytail rejected a redundant code change. The only fresh Sol adversarial review returned `ship` with zero findings and independently verified the no-code decision. Source and installed 09:30 plist bytes now match at SHA-256 `63d96bc4029817e4daa8b23b7583417a6b31f01d2ec3fa357fd14117f8e205ec`, mode `0644`; launchctl reads the unique label at `Hour=9`, `Minute=30` with no report override. Run 12 exited `0`, delivered natural Japanese `morning:2026-08-13` Telegram `15934`, and rendered 5 orders / 2 paid / `$19.98`. Run 13 exited `0`, sent no duplicate, and preserved the five-row delivery state SHA-256 `0dfbfe83e66472cf36d9b43150f0db6cef27875d82cb7ddc7a5aa22ab27203d1`. Historical stderr SHA stayed `288a462c276a71121542afa10efc0da982f8dc5bd46f4e50736f8db702ab6caf`; the revenue ledger stayed at 409 rows and SHA-256 `2729ed05e5504f9c6c26f684dca27fd35cdd2bc02d670a4971c0ffd5c6dc023e`. Item 8 is now the first unfinished queue item.
8. **Load and prove the business watchdog.** Use `skills/self/capafy-loop/launchd/ai.anicca.capafy-loop-healthcheck.plist`, `skills/self/capafy-loop/capafy-loop-healthcheck.sh`, `skills/self/capafy-loop/capafy_business_health.py`, and their tests. **Done when:** the installed plist is byte-equivalent to source, launchctl shows it loaded at 300 seconds, it treats stale reconciliation/absent reports/non-convergent incidents as unhealthy, and it wakes exactly one correct repair owner.
   - **Closed:** classifier commits `c2247cdf4` and `a52b2423e` are deployed through merge `8d3ee9558`. The first and only fresh Sol adversarial review reproduced missing-report misrouting, fail-open future/naive/non-finite evidence, malformed delivery proofs, and unsafe unknown-owner fallback; the same Terra correction added strict evidence validation, fixed five-label routing, and one-shot integrity fallback without a second review. Parent verification is classifier `29 passed`, focused adversarial cases `15 passed`, shell `5/5`, compile/shell/plist/diff PASS. Source and installed plist bytes match at SHA-256 `44290950b83ce32aed13daaa41853a2ca8c2635a9b56abd0e57ecb8a7de711ba`; launchctl shows the previously disabled job enabled and loaded at `StartInterval=300`. The controlled healthy fixture returned healthy without an owner wake. At 19:55 JST the first real watchdog wake classified current incident `capafy-marketer-20260803T070010Z-99b1374a` as `retry_due`, exited `1` by design, and advanced only `ai.anicca.capafy-ig-marketing-daily` from runs `4→5`; Builder stayed `7`, company stayed `13`, hourly stayed `2`, and daily-close stayed `2`. The production revenue ledger stayed at 409 rows with identical SHA-256. Item 9 is now the first unfinished queue item.
9. **Repair Marketing from live browser truth.** Change only the reusable lifecycle/controller path: `skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh`, `skills/earn/capafy-marketing/scripts/capafy_ig_lifecycle.py`, browser/session adapters, and focused tests. Durable `commercial_ready` cannot override a missing live tab; repair must reacquire or provision through the existing account manager, rerun the original publication observable, and verify the owner/public URL. **Done when:** a controlled loop wake ends in a verified Reel, a commercially valid no-op, or one convergent incident with a concrete retry time—never exit 2 plus a stale unresolved event.
   - **Browser boundary closed; production follow-up active:** commits `a16717e33` and `5adcc5872` are deployed through merge `73855e5c4`. The only fresh adversarial review returned `rethink` after reproducing foreign-origin owner false proof, lease-held manager wake, sender crash duplication, partial-write non-convergence, legacy `-k`, and numeric target acceptance; the same Terra correction made canonical `/accounts/edit/` username proof mandatory, released the lease before handoff, replayed retirement/replacement independently, reserved direct alerts at-most-once, removed manager `-k`, and rejected numeric targets. Parent verification is verifier `13 passed`, controller `71/71`, outcome `37/37`, lifecycle/poster `41 passed`, static/diff and direct evil-origin/wrong-owner/numeric counterexamples PASS. Production Marketer run 20 rejected live `@capafy.skills10491` for target `@capafy.skills8m4q2z`, retired only the target, reused incident `99b1374a`, repaired its retry to a future RFC3339 value, appended one conflict-free occurrence, released the lease, and allowed manager PID 40375 to acquire it. Immediate replay run 21 exited 0 with manager runs unchanged, 412-row ledger hash unchanged, incident delivery ID unchanged, and no result. Production then exposed a separate cross-loop defect: the account model returned success with no row, creating competing incident `ed60fa9e`, while the 60-second monitor overwrote the prior unresolved delivery receipt and sent Telegram `16102`; replacement failure sent `16103`. Item 9b below owns this observed defect. No Marketing recovery, sale, or MRR is claimed.
9b. **Converge replacement failure and unresolved Telegram delivery.** Change only `capafy-ig-account-manager.sh`, `capafy-outcome-monitor.sh`, and their focused tests. When the current lifecycle incident already has exactly one browser-owned `session_failed` row, account manager must persist the bounded recovery result and exit before handoff or another browser/model provisioning pass; an unresolved incident with any persisted delivery reservation must never be notified again when retry/repair text changes. First delivery reserves before send and accepts only a strict numeric receipt. **Done when:** one real manager wake creates no fifth incident/message or account row, two monitor wakes preserve incident/event/message state, and replay adds no external effect. Plan: [`../plans/2026-08-13-capafy-incident-notification-convergence.md`](../plans/2026-08-13-capafy-incident-notification-convergence.md).
   - **Closed:** feature commits `9311e393d`, `d857c5b3f`, and `01516c44f` are deployed through merge `2be3c430d`. The only fresh Sol adversarial review reproduced raw-row ambiguity and a closure stuck after sender failure; the same Luna correction closed both, and parent reran the exact counterexamples. Production account manager runs `1` and `2` and two outcome-monitor wakes preserved the 10-row account registry, 417-row event ledger, four historical incident identities, and all existing Telegram IDs; no browser/model pass, account row, fifth incident, event, message, lock, or lease was added. Item 9c remains active; no Marketing recovery or revenue is claimed.
9c. **Make production recognize the already-restored Instagram account.** The account itself is healthy; only Capafy's proof and state are stale. The older reauthentication plan remains file-level context, but this queue supersedes its assumption that another login is required.

   - [x] **9c.1 Deploy modern exact-owner proof.** Replace the legacy-input-only proof in `capafy_ig_session_verify.py` with canonical `/accounts/edit/` proof that accepts exactly one same-origin top-level self-profile link containing the profile image and matching the expected normalized handle. **Done when:** the shipped verifier returns `verified=true` for live `@capafy.skills8m4q2z` and still rejects the wrong owner.
     - **Closed:** commit `4b595ea9a` preserves the legacy username-input path and adds the modern canonical self-profile proof in one production file. Parent live verification acquired `instagram:capafy-provision` at dynamic port `49938`: exact owner `@capafy.skills8m4q2z` returned `verified=true`, while registered wrong owner `@capafy.skills10491` returned exit `1`; the lease was released. Post-implementation checks are verifier `13 passed`, compile, and diff PASS. No registry, lifecycle, browser login, account, post, incident, Telegram, or money state changed.
   - [x] **9c.2 Reactivate exactly one existing registry row.** Resolve the dedicated browser's live dynamic port, independently run 9c.1, and only then update the existing `8m4q2z` row from `session_failed` to `publish_probe_ready`; preserve historical incident/retirement evidence and append no account. **Done when:** registry readback port equals the guard-resolved live port (currently `49938`) and names the exact handle, browser identity, and one active row.
     - **Closed:** parent reacquired `instagram:capafy-provision`, independently proved exact live owner `@capafy.skills8m4q2z`, and atomically changed only `status` and `port` on its existing row. Readback is 10 rows, one target, one active handle, `publish_probe_ready`, `session_owner=browser`, `browser_identity=instagram:capafy-provision`, port `49938`, mode `0600`; incident `99b1374a`, retirement reason, and retirement timestamp remain unchanged. Registry SHA-256 changed from `3a1dbb9dc338bd1b26d745a162a4a0fef5ba5be42c2e11ed964bfbc6f4ea4f92` to `1802d2afe846bf0d3226b524c3385e133cd657527e0ccdbf173f59abbe8e23e5`. The browser lease was released, and no lifecycle, event, result, incident, Telegram, account, post, or money state changed.
   - [x] **9c.3 Restore lifecycle capability.** Run the existing lifecycle snapshot from the reactivated row. **Done when:** readback is `session_established=true`, `capability=publish_probe`, `replacement_requested=false`, and no unrelated account changes.
     - **Closed:** the existing lifecycle `snapshot` command persisted `handle=capafy.skills8m4q2z`, `session_owner=browser`, `status=publish_probe_ready`, `session_established=true`, `capability=publish_probe`, and `replacement_requested=false`. Lifecycle SHA-256 changed from `197d90aa2bc04ddaeda2e1e1a10a708da5fd9c5f1151505c2b6ac34f6b5c6720` to `c1950cefdce6405f8bd3d869329d33629ff102a6dd08e05643c4c118f8193de9`; the account registry remained byte-identical at `1802d2afe846bf0d3226b524c3385e133cd657527e0ccdbf173f59abbe8e23e5`. No browser, event, result, incident, Telegram, account, post, or money state changed.
   - [x] **9c.4 Close only the browser-loss incident.** Advance incident `99b1374a` through its legal terminal path using exact-owner evidence; do not rewrite the other historical incidents or delivery IDs. **Done when:** one canonical verified occurrence exists and immediate replay changes no event byte.
     - **Closed:** incident `capafy-marketer-20260803T070010Z-99b1374a` advanced legally from `unresolved` through `repair_started` and `repaired` to `verified` with concrete verification `{owner_session_verified:true, handle:capafy.skills8m4q2z, browser_identity:instagram:capafy-provision, port:49938, proof:canonical_same_origin_self_profile}`. Canonical `attempt-1` repair-started, repaired, and verified events each exist exactly once; the ledger advanced `417→420` rows to SHA-256 `bfe7e22c98403689c02e14e44468d033992a73db7146cd1f20c939a481a96aa3`, and identical verified replay left that hash unchanged. The first readback assertion expected suffix-free event IDs and failed only because the existing adapter correctly appends `:attempt-1`; the corrected semantic count passed. Other incidents, the registry, lifecycle, and Telegram message ID `16102` remained unchanged; no external message or post was sent.
   - [x] **9c.5 Wake the existing Marketer once.** Reserve the wake before `launchctl kickstart`, release the browser lease, then wake only `ai.anicca.capafy-ig-marketing-daily`. **Done when:** run count advances once and replay adds no wake, incident, Telegram, or account row.
     - **Closed:** the existing `8m4q2z` row atomically reserved `reauth_marketer_wake_reserved_at=2026-08-13T14:36:01Z` before `launchctl kickstart`; browser guard readback had no holder. Only `ai.anicca.capafy-ig-marketing-daily` advanced `36→37`. Replaying the reservation returned `already_reserved` and left runs, all 10 account rows, active-handle set, incident list/message IDs, 422-row ledger, and ledger SHA-256 `2f25786e061baf06caf5c2657597f0aaede209df5ccf7f9590eade7486afc674` unchanged. The real first wake exited `1` and honestly created incident `536fc25c` plus Telegram `16314` because the shared resolver excludes `publish_probe_ready`; Item 9c.6 owns that observed system defect and outcome retry. No browser login, account append, model, or post occurred.
   - [x] **9c.6 Verify the Marketing business outcome.** Let the loop—not Codex—return one verified Reel, a valid no-op with current public evidence, or one typed platform challenge. **Done when:** the outcome has the exact account, Capafy listing URL, public content URL when applicable, current view measurement, and no duplicate external effect.
     - **Closed:** commits `7fab69591` and `277448ce9` make the shared resolver recognize lifecycle-active `publish_probe_ready` while preserving legacy `ready*`/`warming*`, and classify Instagram's explicit share-rejection dialog immediately as the existing typed `challenge` without leaking its internal upload stack. Live resolver readback is exact handle `capafy.skills8m4q2z`, browser identity `instagram:capafy-provision`, port `49938`, usable count `1`; shared account-state regression is `40/40`, poster regression `24 passed`, compile/shell/diff PASS. The loop selected `https://capafy.ai/agent/7785270416`, generated a validated 27-second H.264 1080×1920 MP4, and attempted one live share. The screenshot proves `投稿をシェアできませんでした`; direct profile readback proves no new Reel and preserves the two existing URLs at 190 and 184 views. System incident `536fc25c` is verified; platform incident `332a5e9e` remains typed unresolved with retry `2026-08-13T15:54:48Z`, the same Telegram `16331`, and no retry/bypass/account creation. The ledger is 428 rows at SHA-256 `8be2151901bf9323b735c2d8351b945f9b9c5b837660922ec90d86a3d60bbb3f`.

10. **Make Builder operate the five-slot first-version review queue.** The gate concerns never-online Agents, not total products or every rejected update. A full queue blocks only new `addAgent`; it must not terminate review repair, learning, or revenue work.

   - [x] **10.1 Replace total-rejected `CAP_FULL` with the first-version queue count.** Read authenticated inventory once and derive `never_online = hasOnlineVersion=false`; do not count rejected updates or version drafts as new-Agent capacity. Continue to action selection at five and fail closed on unreadable inventory. **Done when:** the current readback reports five never-online rejected Agents, six existing-version draft/rejected rows outside that count, refreshes money and inventory, and cannot call new `addAgent` while `never_online >= 5`.
     - **Closed:** publisher commit `4ffb9503` makes the shared capacity predicate count only `hasOnlineVersion=false`, fails closed when that field is absent or malformed, and blocks the official `addAgent` boundary through `CAPAFY_BLOCK_NEW_AGENT` while leaving `addAgentVersion` available. Life Manager commit `e8e17543c` reconciles money first, reads authenticated `publish-list` once, exports that guard only at five or more never-online Agents, and continues into bounded action selection instead of returning early. The live readback is exactly 32 total = 21 online + 5 never-online `review_rejected` + 4 existing-version `review_rejected` + 2 existing-version `draft`; the latter six are outside the first-version queue. Post-change evidence is 13 focused checks passed, shell/compile/diff checks passed, full-queue `addAgent` rejected before HTTP, `addAgentVersion` allowed, and four-slot `addAgent` allowed. No remote listing, review, payment, browser, Telegram, or revenue state changed; Item 10.2 is next.
   - [x] **10.2 Define the finite full-inventory action set.** Reuse existing commands only: `poll_review`, `measure`, `repair_rejected`, `reposition`, `retire_candidate`, `optimize_packaging`, `handoff_marketing`, or `no_op`. **Done when:** every result is exactly one listed action with one target or an explicit no-op reason.
     - **Closed:** commit `9bc2387cd` adds no executor, command, service, or remote mutation. When 10.1 marks the first-version queue full, the trailing runtime contract accepts exactly the eight named actions. Every non-`no_op` artifact must contain exactly one numeric Agent ID or canonical `https://capafy.ai/agent/<id>` target plus a non-empty reason; `no_op` must omit target and explain why none of the seven actions is safe. The deterministic handoff rejects unknown actions, multiple/invalid/missing targets, unsupported fields, target-bearing `no_op`, and empty reasons before a success report. `repair_rejected` additionally requires `target == agent_id` and the existing remote submission readback; the exact-ID success and mismatched-ID rejection both passed. Existing Builder checks are `39 passed`, daily/reconcile checks are `13 passed`, shell/diff checks pass, and source inspection returns eight unique actions in the specified order. Production `launchctl` reads the same source script, remains idle with last exit `0`, and no Builder wake, listing, review, payment, browser, Telegram, or revenue state changed. Item 10.3 is next.
   - [ ] **10.3 Remove hardcoded product and purchase policy.** Delete mandatory new-listing, subscription-only, Download prohibition, fixed product name, and fixed `$9.99/week` instructions. **Done when:** the runtime prompt contains none of them.
   - [ ] **10.4 Require evidence-backed packaging.** Reuse `capafy_packaging_decision.py` to choose `subscription`, `usage`, `one_time`, or `hybrid` from buyer value shape and exact unit economics. **Done when:** absent economics fails closed instead of injecting a model or price.
   - [ ] **10.5 Prove one real bounded Builder outcome.** Kickstart the existing Builder once. **Done when:** it reconciles/reports and starts with one never-online rejection repair or an explicit evidence-backed no-op; it never creates a sixth never-online Agent.

11. **Make the existing 32-product portfolio converge without duplicate remote work.**

   - [ ] **11.1 Refresh all remote listing statuses and queue roles.** Persist `agentStatus`, `hasOnlineVersion`, and latest version identity for every row. **Done when:** all 32 rows map losslessly and partition into 21 online, 5 never-online rejected, 4 rejected updates, and 2 version drafts.
   - [ ] **11.2 Read the exact rejection reason for one never-online Agent.** Do not infer from its title or category. **Done when:** one target, platform clause, rejected surface, and safe minimal correction are recorded.
   - [ ] **11.3 Repair and resubmit that same Agent once.** Change only the 11.2 rejected surface and reuse the existing Agent identity. **Done when:** the same Agent reaches `under_review` with one receipt and immediate replay produces no duplicate submission.
   - [ ] **11.3a Refill the review queue sequentially.** Repeat 11.2–11.3 one Agent at a time until five first-version Agents are under review or no eligible safe repair remains; never use parallel remote submission. **Done when:** queue count is five with distinct receipts, or one explicit blocker names why fewer than five can safely be submitted.
   - [ ] **11.4 Select one eligible loser.** Rank only products with sufficient exposure and no attributed sales by net revenue per impression; unknown exposure is ineligible. **Done when:** one target and cited evidence are recorded, or a no-op explains why none qualifies.
   - [ ] **11.5 Free at most one slot.** Reposition or retire only the 11.4 target. **Done when:** remote and local states agree and capacity changes by at most one.
   - [ ] **11.6 Make every remote action resumable.** Persist one action key before mutation and its receipt after mutation. **Done when:** a forced replay resumes or no-ops and never repeats the remote mutation.
   - [ ] **11.7 Hand one newly online or materially updated listing to Marketing once.** **Done when:** the handoff contains its public Capafy URL and replay produces no second handoff.

12. **Make every decision learn from money rather than activity.**

   - [ ] **12.1 Attribute every attributable order.** Join product, offer, source, campaign, and content where platform evidence permits; keep unavailable fields explicitly unknown. **Done when:** no order is silently assigned to a product or channel.
   - [ ] **12.2 Separate recurring and one-time revenue.** **Done when:** one-time gross never enters MRR, and subscription start, renewal, cancellation, refund, and recognized MRR have distinct canonical events.
   - [ ] **12.3 Calculate product contribution.** Record gross, platform fee, hosted/model cost, refund, and contribution per product; unknown cost prevents scale. **Done when:** every scale-eligible product has positive worst-case contribution and a hard loss cap.
   - [ ] **12.4 Register one experiment before acting.** Store hypothesis, target, one changed variable, metric, minimum evidence, stop rule, and expiry. **Done when:** the action cannot run without that record.
   - [ ] **12.5 Measure and decide one experiment.** Retain, revert, or extend using the declared rule. **Done when:** the result changes the next Builder or Marketer decision and activity alone cannot win.
   - [ ] **12.6 Refresh content metrics.** Replace stale Instagram measurements with current public views and link/campaign evidence where available. **Done when:** the 190/184 live observations are represented without overwriting history and future hourly reports show metric freshness.

13. **Prove the complete no-human operating loop once.**

   - [ ] **13.1 Trigger the existing Builder and Marketer launchd jobs.** Do not create a replacement executor. **Done when:** each produces one bounded terminal outcome.
   - [ ] **13.2 Verify business evidence.** **Done when:** fresh money, inventory, account, listing, content, attribution, cost, and canonical-event evidence agree.
   - [ ] **13.3 Verify owner reporting.** **Done when:** the next hourly Japanese Telegram and 23:50 daily close report the same money and exact next action with real links.
   - [ ] **13.4 Verify automatic repair.** Inject no production failure; use the next naturally observed failure or an isolated fixture. **Done when:** the correct existing owner wakes within five minutes and closes or schedules one bounded retry.
   - [ ] **13.5 Replay immediately.** **Done when:** no remote mutation, post, event, wake, or Telegram duplicates.

14. **Reach the first recurring revenue gates on one measured offer/channel pair.**

   - [ ] **14.1 Record the first attributed active subscription.** **Done when:** canonical evidence shows product, offer, source, gross, fee, contribution, and renewal terms; projected revenue does not count.
   - [ ] **14.2 Reach `$100 MRR`.** Repeat only the proven offer/channel experiment until recognized active MRR is at least `$100`, with positive contribution and no hidden subsidy. **Done when:** the canonical projection and payout evidence agree for two consecutive reports.
   - [ ] **14.3 Name one winner.** **Done when:** one offer/channel pair has enough exposure to report conversion, positive contribution, and at least one observed renewal or an explicit renewal-observation window still open; no other product is scaled by intuition.

15. **Scale the winner to `$1K MRR` without changing the business model.**

   - [ ] **15.1 Increase qualified exposure on the winning channel.** Change one distribution variable per registered experiment. **Done when:** exposure and attributed conversions rise without breaching channel payback or support limits.
   - [ ] **15.2 Improve the winning offer.** Change one of onboarding, proof, packaging, or price per experiment. **Done when:** conversion or contribution improves by the declared rule; otherwise revert.
   - [ ] **15.3 Reach `$1K MRR`.** **Done when:** recognized active MRR is at least `$1,000`, contribution is positive, churn and renewal are observable, and the level persists across two consecutive reporting periods.

16. **Scale the proven engine to `$10K MRR`.**

   - [ ] **16.1 Add one compatible distribution surface.** Repackage the same proven capability for one of Capafy, Apify, RapidAPI, or direct billing; do not invent a new core product. **Done when:** the second surface has one attributed paid recurring customer and independent unit economics.
   - [ ] **16.2 Allocate by net revenue per impression.** Shift the next bounded experiment toward the highest positive-contribution surface while retaining a control. **Done when:** allocation is reproducible from canonical metrics.
   - [ ] **16.3 Repeat winner expansion one surface or segment at a time.** **Done when:** each addition passes attribution, contribution, renewal, churn, support-cost, and channel-payback gates before the next begins.
   - [ ] **16.4 Reach `$10K MRR`.** At the current approximate `$32.9` net monthly equivalent per active weekly Capafy subscriber, the reference requirement is about 304 active equivalents; a mixed portfolio may reach the same recognized recurring total with fewer higher-ARPU customers. **Done when:** canonical recognized active MRR is at least `$10,000`, positive total contribution is independently reconciled against the payment source, no one-time revenue is counted as MRR, and an immediate second reconciliation is identical.

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
| 14. Cold Email packaging decision contract | Production verified | A separate `capafy_packaging_decision` contract updates purchase model, value metric, renewal reason, and package economics without activating an experiment or manufacturing demand. Candidate 1 was rejected because the prompt omitted Capafy's real `cycleMaxMessageCount`; RED added the remote field and the sanitized prompt exposed `60`. Candidate 2 was rejected because it used `platform_fee_rate=0.2037` while citing 20%; RED/GREEN now require the exact official `0.2000` rate in both prompt and deterministic validation. Candidate 3 selected the configured monthly `$5.99 / 60` subscription, assumed 2,500 input plus 1,500 output tokens per cadence on Google `gemini-3.5-flash-lite`, and passed exact package arithmetic: `$1.20` fee, `$0.27` assumed cost, `$4.52` projected contribution. Dry apply changed only `5051239796`; production apply kept `experiment=null`, retained demand/sales/actual cost as unknown, validated the 32-row portfolio, and wrote mode `0600`. Portfolio SHA-256 is `a3d2156366d006062a0b7cc5afdb0aa8b332cdb7bd7126421fe0132a1ae3f4c5`; candidate SHA-256 is `1a54b9a798a9843f70620655f5d2ec8baa3c12d98f719e120255fd5cc1020446`. Fresh focused tests `14 passed`; full Capafy suite `215 passed`; compile, schema parse, and diff check passed. No sale, realized revenue, approval, or observed cost is claimed. | `446c4837a` |
| 15. Verified-incident terminal guard | Production verified | Runtime diagnosis proved `@capafy.skills5595` was already terminal `verified`, while the stale `.self-fix-capafy-loop.incident.json` still referenced a code-only `SUCCESS` marker. The monitor rendered and sent a false unresolved message before its state machine rejected `verified -> unresolved`, leaving launchd at exit `2` and allowing the same report to repeat. RED added the exact production shape: a verified incident with concrete Reel/session verification, a terminal Telegram key, a stale sidecar, and no attached legacy `outcome`; the integration ended `25 passed / 2 failed` because it sent once and exited nonzero. GREEN makes persisted `verified` business state authoritative before envelope construction: the stale retry exits zero, sends nothing, and preserves the incident byte-for-byte. Fresh offline verification: monitor integration `27 passed / 0 failed`; outcome contract `24 passed`; shell syntax and diff check passed. Production run against the real stale sidecar returned `0`; incident and ledger hashes were unchanged; error lines stayed `277`; launchd reached `runs=699 / last exit=0`. | `7e5f2d3bd` |
| 16. Experiment/listing projection parity | Production verified | Root-cause tracing found that the ledger itself already contained Listful's newer `listing.observed:draft` event, but experiment projection ignored it and treated the older experiment evidence URL as a current public URL. RED appended an experiment activation, stop, and newer draft listing event; projection incorrectly returned `https://capafy.ai/agent/3947077924`. GREEN makes the latest listing event authoritative when the experiment's product has current listing evidence: only an `online` listing with a matching Capafy URL remains public; draft/review/rejected states yield null. Older ledgers without a listing event retain the experiment-event fallback. Offline verification: projection/dashboard/goal-monitor suites `18 passed`; compile and diff check passed. Production goal monitor then returned `0`, emitted projection `a6b4c9a70d4c…`, and showed the stopped experiment with `public_url=null`; fresh inventory, money, account, marketing, incident, and experiment parity all passed. Telegram delivery `5525` records that projection. | `100ef4565` |
| 17. Autonomous parity-incident closure | Production verified | Passing parity previously left the detected company incident open, so recovery still needed manual phase transitions. RED extended the end-to-end goal-monitor fixture through clean → contradictory gross → detected incident → corrected source; the recovered report still exposed `phase=detected`. GREEN stops before publishing the recovered pre-closure projection, advances the exact matching parity incident through `repair_started → repaired → verified` with concrete projection verification, then reruns the deterministic projection once. The only delivered recovery report is ledger-backed, contains no active incident, begins `Capafy incident resolved — no action needed`, and dashboard state equals Telegram's projection. A subsequent retry emits no Telegram and preserves exactly one event for each incident phase. Offline verification: Python `42 passed`; monitor integration `27 passed`; shell syntax and diff check passed. Production incident `capafy-company-20260802T003010Z-80045c5e` reached all four phases once; Telegram `5526` and dashboard share projection `8ccf1d8b1d41…`; immediate retry returned `0` with identical ledger and delivery hashes. | `da25cb7a8` |
| 18. Provider-bound packaging preflight | Verified | The first residual readback exposed a correctness gap: packaging could price every hosted product as Google even when the current remote version still used OpenRouter. RED bound the decision to a sanitized remote digest, exact provider/model, configured billing package, online hosted status, and malformed-remote fail-closed behavior. GREEN requires one `publisher_google_official / gemini-3.5-flash-lite / google-generative-ai` provider, zero generic credentials, exact `$0.30/M` input and `$2.50/M` output rates, and an exact remote plan match before any portfolio write. Secrets/placeholders never enter the prompt. Fresh Performance Review Writer `4886968609` readback is online with monthly `$5.99 / 60` and weekly `$1.99 / 30`, but uses OpenRouter plus one generic credential, so the new gate correctly requires provider migration and applies no packaging decision. Focused tests `17 passed`; full Capafy suite `219 passed`; compile, schema parse, and diff check passed. | `5e505d59b` |
| 19. Performance Review isolated provider migration | Submitted and remotely verified; manual review in progress | Root-cause observation found the current green validation color `rgb(38,147,107)`, Skill/Plugin at `0 / 1`, and a stale non-empty `Anthropic (via OpenRouter)` disclosure. TDD added current-color recognition, forced provider replacement, and exact skill selection/verification; publisher tests are `18 passed` at source commit `7c4fe733`. Whole-browser Playwright attachment then timed out while synchronizing 109 shared targets, but the exact Capafy target remained reachable, so the recovery used target-scoped CDP without touching other tabs. CP1 reached `card-done`; the platform read back skills confirmed, Google disclosure, and preserved plans. The first CP2 attempt correctly stopped because only `OPENCLAW_CONFIG_PATH` was bound and main `.env` would have produced 181 unrelated generic credentials; binding `OPENCLAW_STATE_DIR` to the same isolated profile reduced the real contract to one Google `url_proxy` and zero generic credentials. CP2, package upload, and final submission then completed. Fresh platform truth is version `2083732042685501440`, `status=1`, `auditStatus=2`, skills/config confirmed, exact Google-official provider/model/API format, zero generic credentials, package present, and unchanged pricing. Main Capafy regression suite is `219 passed`; browser lease is clear. Packaging remains unapplied because the provider-bound contract requires the latest version to be online (`status=4`). No approval, sale, realized revenue, or packaging completion is claimed. | `7c4fe733` |
| 20. Fail-closed OpenClaw profile binding | Production patched and verified | The first Performance Review configure attempt proved that setting only `OPENCLAW_CONFIG_PATH` still sourced optional state files from main `~/.openclaw`, exposing 181 unrelated generic credentials to the scan. RED expected the configured file's parent to become the implicit state root and instead received `/Users/anicca/.openclaw`; the explicit-state precedence case already passed. GREEN now resolves state root in this order: explicit `OPENCLAW_STATE_DIR`, parent of explicit `OPENCLAW_CONFIG_PATH`, default OpenClaw root. A third integration-level unit test builds the real OpenClaw stage plan and confirms `.openclaw/.env` comes from the isolated profile. Installed publisher tests are `3 passed`; compatibility documentation records the contract. No remote configure or credential mutation was used for this verification. The installed vendor is an existing large uncommitted upstream snapshot, so this narrow production patch is not falsely attributed to a clean vendor commit. | plan `c95e6743c`; production patch uncommitted |
| 21. Exact-target CDP recovery | Production patched and verified | RED proved the helper was absent, then required exact query-token matching, refusal of missing or ambiguous page targets, same-token Capafy navigation, and password redaction. GREEN adds `capafy_target_cdp.py`: it reads `/json/list`, selects exactly one `type=page` whose parsed `token` equals the requested token, and connects directly to `/devtools/page/<target-id>` without whole-browser Playwright synchronization. State is bounded and secret-redacted; trusted click/fill use CDP Input events; secret-looking fields require an environment-variable name. CP1/CP2 runbooks now name this fallback after `ws connected` attachment timeouts. Installed publisher suite is `8 passed`; compile and diff checks pass. Read-only live integration under a leased `interactive:dais` selected only target `7CBFD4349AB513793A9B5A24220E4A29` for review token `2083746648181993472`, returned the exact review URL with no fields or credentials, performed no navigation/click/fill, and released the lease to an empty holder. | plan `c95e6743c`; production patch uncommitted |
| 22. Deterministic recovery handoff | Production verified | RED executed the real daily wrapper in its safe probe mode and received only the legacy reporting owner line, proving the known browser/profile recovery was absent from runtime instructions. GREEN adds a side-effect-free recovery probe plus the same contract to the production agent prompt: a whole-browser `ws connected` timeout must use exact-token `capafy_target_cdp.py` under the existing lease, never last-tab selection or unrelated tab closure; an isolated profile must bind config, state, and runtime workspace to one root and require zero generic credentials before CP2. Known cases no longer need generic self-fix or human memory. Focused prompt-contract pytest and shell syntax pass; full main Capafy suite is `219 passed`, installed publisher suite is `8 passed`. Fresh remote polling advanced Performance Review Writer from `auditStatus=1` to `auditStatus=2` while keeping `status=1` and both confirmations at `1`, so packaging remains correctly pending with no browser lease and no human action. | `922026d37` |
| 23. Next residual selection | Verified read-only | Fresh governed portfolio order contains ten undecided promoted products after excluding the already-migrating Performance Review row. The first residual in stable portfolio order is Interview Coach `4014388606`, so selection did not cherry-pick an easier product. Fresh platform truth is online `status=4 / auditStatus=4`, exact selected skill `.openclaw/skills/interview-coach`, package present, and three subscription plans: day `$2.99 / 40`, week `$6.99 / 150`, month `$14.99 / 400`. Its hosted contract remains `publisher_openai_official`, vendor `OpenRouter`, model `anthropic/claude-sonnet-4.6`, API format `openai-responses`, with one generic credential. Therefore no packaging decision is eligible yet. The next mutation is one isolated provider migration on the existing Agent; the separate one-time/BYOK sibling is a later evidence-based packaging option, not an invented current decision. No remote mutation, approval, sale, or revenue is claimed at this checkpoint. | `d8231b312` |
| 24. Interview Coach isolated provider migration | Submitted and remotely verified; automatic review in progress | A dedicated publisher state root was created for existing Agent `4014388606`; its confirmed selection names only `.openclaw/skills/interview-coach`, producing candidate version `2083752650570756096` rather than a duplicate Agent. CP1 selected exactly `interview-coach`, replaced the stale OpenRouter disclosure with `Google Gemini`, and preserved day `$2.99 / 40` with no trial, week `$6.99 / 150` with 24-hour trial and count `3`, and month `$14.99 / 400` with 24-hour trial and count `10`. Isolated CP2 generated one URL proxy and zero generic credentials; after whole-browser synchronization stalled, exact-token CDP selected only token `2083754294691786752`, filled the Google key from the isolated profile with redacted output, and reached config confirmation. `publish-ship` uploaded the package with that same credential digest. Exact-token CP3 selected only token `2083756495287906304`, preserved automatic publishing, recorded accurate migration notes, and submitted for review. Fresh server truth is `status=1 / auditStatus=1`, skills/config `1 / 1`, exact `publisher_google_official / gemini-3.5-flash-lite / google-generative-ai`, generic `0`, package present, and unchanged plans/trials. The browser lease was released. No approval, sale, revenue, or packaging decision is claimed. | binding `659050193`; CP1 `94035c9e5`; CP2 `608f90e48`; final `003ca7fb6` |
| 25. Next residual selection after Interview Coach | Verified read-only | Stable governed portfolio order, excluding the two already-submitted migrations, selects Meeting Notes `3947077924` before every other undecided promoted product. Fresh platform truth is online `status=4 / auditStatus=4`, skills/config confirmed, exact selected skill `.openclaw/skills/meeting-action-items`, package present, monthly `$5.99 / 60` and weekly `$1.99 / 30`, with no free trial on either plan. Its hosted contract is still `publisher_openai_official / OpenRouter / anthropic/claude-sonnet-4.6 / openai-responses` with one generic credential. The local skill exists and explicitly forbids inventing attendees, decisions, owners, dates, or tasks. Performance Review remains `status=1 / auditStatus=2`; Interview Coach remains `status=1 / auditStatus=1`; both preserve their Google-official contracts. No mutation, approval, sale, revenue, or packaging decision is claimed at this checkpoint. | `28e67f128` |
| 26. Context-discovery self-heal and Meeting Notes isolated provider migration | Submitted and remotely verified; automatic review in progress | The first two `publish-init` attempts were interrupted before API mutation after stack traces proved context discovery was reading every file beneath all installed skill trees. RED regressions forced failure for oversized context reads and installed-skill rescans; GREEN caps context documents at 4 MiB and excludes skill/plugin tree sources from workspace-document discovery. The same command completed in 8.8 seconds and created candidate `2083762290352222208` on existing Agent `3947077924` with exactly `.openclaw/skills/meeting-action-items`. Whole-browser CP1 attachment stalled before mutation; exact-token CDP selected only `2083762291048476672`, confirmed the skill, replaced the provider disclosure with Google Gemini, preserved monthly `$5.99 / 60`, weekly `$1.99 / 30`, and no trials, then reached card completion. Isolated configure produced one URL proxy and zero generic credentials. Exact-token CP2 selected only `2083765755171459072`, filled the Google key from the isolated profile with redacted output, saved, and confirmed. `publish-ship` uploaded that exact package. Exact-token CP3 selected only `2083767000246407168`, verified automatic publishing, recorded accurate migration notes, and submitted for review. Fresh server truth is `status=1 / auditStatus=1`, skills/config `1 / 1`, exact Google-official provider/model/API format, generic `0`, package present, and unchanged billing/trials. Installed recovery suite is `10 passed`; source publisher suite is `20 passed` at durable fix commit `b85a18d3`; the lease is released. No approval, sale, revenue, or packaging decision is claimed. | self-heal `b85a18d3`; binding `bd001bbbe`; CP1 `84f355004`; CP2 `532c5d7c6`; final `1fc209516` |
| 27. Next residual selection after Meeting Notes | Verified read-only | Stable governed portfolio order, excluding the three submitted migrations, selects YouTube Script Writer `7686597754` before every other undecided promoted product. Fresh platform truth is online `status=4 / auditStatus=4`, skills/config confirmed, exact selected skill `.openclaw/skills/youtube-script-writer`, package present, day `$1.99 / 10` with no trial, week `$4.99 / 25` with no trial, and month `$9.99 / 60` with a 72-hour trial and count `10`. Its hosted contract is still `publisher_openai_official / OpenRouter / anthropic/claude-sonnet-4.6 / openai-responses` with one generic credential. The local skill exists and explicitly forbids invented facts, statistics, quotes, sources, or view/subscriber guarantees. No mutation, approval, sale, revenue, or packaging decision is claimed at this checkpoint. | `6971432b8` |
| 28. YouTube Script Writer exact candidate binding, CP1, and CP2 | Historical bootstrap evidence; CP2 remotely verified | `YouTube Script Writer` is the name of an existing Capafy skill product; this row does not describe or authorize posting to YouTube. A dedicated publisher state root was created for existing Agent `7686597754`; its confirmed selection names only `.openclaw/skills/youtube-script-writer`. The durable context-discovery fix reduced `publish-init` to 4.7 seconds. Explicit `--agent-id 7686597754` created candidate version `2083769384334938112` on the existing Agent rather than a duplicate. Exact-token CP1 selected only `2083769384817283072`, confirmed `youtube-script-writer`, replaced the OpenRouter disclosure with `Google Gemini`, preserved day `$1.99 / 10` without trial, week `$4.99 / 25` without trial, and month `$9.99 / 60` with 72-hour trial and count `10`, then reached `card-done`. Isolated configure generated one Google-official URL proxy and zero generic credentials. The final CP2 verification click was interrupted client-side, so no success was assumed; fresh server reconciliation proved `isConfirmedSkills=1`, `isConfirmedConfigKeys=1`, exact `publisher_google_official / gemini-3.5-flash-lite / google-generative-ai`, generic `0`, unchanged billing/trials, and package still absent. The stale lease was released. Continuing this row manually would take over the Builder's routine responsibility, so the incomplete state is now an autonomous-resume test fixture for the Builder. Package upload, CP3, approval, sale, revenue, and packaging decision are not claimed. | binding `67b9da859`; CP1 `37d35a9d6`; CP2 reconciliation `4c95f2f32`; ownership correction `b2851f452` |

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
6. Telegram reports are natural language, contain real links, and keep one-time gross/contribution separate from recurring recognized revenue/new MRR/total MRR; pending payout, realized payout, fees, hosted cost, and contribution remain explicitly labeled.
7. Dashboard and Telegram agree because both use the same event ledger.
8. Account health distinguishes session readiness, public live state, account-status signals, and reach health; calendar age and synthetic activity are not health evidence.
9. Every hosted product has a hard loss cap and measurable contribution margin.
10. The next product and marketing action are chosen from fresh evidence and prior experiment outcomes.
11. Routine operation, account replacement, retries, and repair require no babysitting.
12. One complete Builder/Marketer cycle and its immediate replay finish without a silent failure, duplicate external effect, or contradictory report.
