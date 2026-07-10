# Life Manager Autopilot Product Loop Design（2026-07-10）

## Status

- Owner repo for this spec: `anicca-project`
- Target product surface: `aniccaai.com/life-manager` + Telegram onboarding/chat + phone calls
- Target loop home: `profitable-claude/skills/human-funded/life-manager/`
- Existing local harness: `~/anicca/skills/self/life-manager-loop/`
- Existing related OpenClaw skills to vendor/migrate:
  - `~/.openclaw/skills/calendar-with-travel-time/`
  - `~/.openclaw/skills/opportunity-calendar/`
  - `~/.openclaw/skills/anicca-meetup-talk-applier/`
  - `~/.openclaw/skills/anicca-life-manager/`
- Design relation:
  - Life Manager is one **product business loop** under the profitable-claude CEO portfolio.
  - CEO loop keeps its existing job: portfolio allocation across businesses such as gig, bounty,
    affiliate, video, and life-manager.
  - Life Manager loop owns the Life Manager product itself: product dev, self-heal, feedback triage,
    product marketing, product revenue, and product-internal API cost/outcome ledgers.
  - MAIN / Agent Economy loop remains a separate mission loop for building the self-funded agent
    economy.
  - Long-term direction: Life Manager may absorb user-benefit loops from profitable-claude, and the
    user-facing product may become one cloud repo/product named `life-manager`. That is a migration
    path, not the current architecture.

## Product Thesis

Life Manager is the proactive AI that moves a person's life toward their ideal self without the user
being in the loop. It asks the minimum number of questions needed, then infers and acts from connected
context, telemetry, public search, calendar/Gmail signals, and user feedback.

Initial wedge:

> Are you tired of searching travel time for every physical calendar event?
> Life Manager connects to Google Calendar, fills travel/prep time for every physical event, calls
> before you need to leave, and handles lateness communication.

Core phrase:

> Your life starts moving on autopilot.

Secondary phrase:

> Your ideal life, without you in the loop.

The first paid product must stay narrow enough to sell:

1. Calendar travel-time autofill for physical events.
2. Phone call before departure / wake / sleep / important event.
3. Lateness guard: if the user will not make it, notify stakeholders and update calendar.
4. Telegram-first onboarding and reporting.

The to-be product is broader:

1. Understand user ideals from Telegram onboarding plus Gmail/Calendar/Slack/X context.
2. Find environments that make the user become that ideal self.
3. Apply/register for events, retreats, meetups, podcast guests, job/networking opportunities.
4. Add accepted events/meetings to Google Calendar with travel time.
5. Report completed actions after the fact, and let the user cancel/undo by replying.
6. Learn from feedback and metrics, turn them into GitHub issues, implement/merge/deploy fixes.
7. Market itself with social/content loops until Life Manager reaches real MRR.

Onboarding principle:

```text
Ask less.
Infer more.
Act first when safe.
Report after action.
Let the user cancel or correct.
```

MUST:

1. Telegram onboarding asks only the irreducible questions:
   - "What do you want out of life?"
   - permission/connectors needed for action: Calendar, Gmail, phone, billing.
2. If the user gives a long answer, parse it into goals/ideals without asking follow-up questions
   unless execution is blocked.
3. If the user gives a short answer or no clear ideal, assume the default human goals:
   - physically healthy,
   - mentally healthy,
   - financially healthy,
   - trusted by other people,
   - connected to useful environments.
4. Missing information is acquired by:
   - reading connected Calendar/Gmail/context,
   - searching public sources,
   - observing behavior and feedback,
   - trying reversible low-risk actions.
5. The product reports completed actions and keeps an undo/cancel path. It does not turn every action
   into a permission request.

## Decision: Hybrid, Not Two Forked Products

Do **not** build a private local-only Life Manager and a separate cloud Life Manager that diverge.
The product runtime is cloud-first. Local claude-p/profitable-claude may still orchestrate, verify,
and improve it until the cloud self-improvement runtime is mature, but users use the cloud product.

Use a hybrid:

```text
ONE canonical cloud product
  |
  +-- Dais dogfood tenant
  |     - deepest context
  |     - fastest feedback
  |     - local claude-p can operate credentials/tools before SaaS hardening
  |
  +-- paid user tenants
        - same product code
        - stricter permission boundaries
        - subscription billing
        - generalized workflows
```

Reasoning:

- Dogfooding is required, but dogfooding alone is not enough. The product must also ingest external
  user feedback and paid-user metrics.
- A local-only branch creates features that work for Dais but never become SaaS. That does not build
  MRR.
- A cloud-only branch loses the speed and depth of Dais's daily use. That slows product discovery.
- Therefore: Dais is the first and deepest tenant of the same cloud product, while local claude-p loops
  may incubate unsafe/credential-heavy actions until they are hardened into multi-tenant cloud flows.

Repo ownership:

```text
github.com/Daisuke134/life-manager
  - product code
  - product issues
  - product PRs
  - Telegram/Calendar/Gmail/phone/Stripe cloud runtime

github.com/Daisuke134/profitable-claude
  - loop harness
  - CEO allocator
  - cadence/evidence/verifier
  - life-manager business-manager runner
  - feedback-to-issue automation

github.com/Daisuke134/anicca-project
  - specs and handover docs
```

Routing rule:

```text
User-facing product bug/feature/growth/retention issue
  -> life-manager repo

Loop/runtime/cadence/evidence/CEO allocation bug
  -> profitable-claude repo
```

## External BP Used

Collected via Firecrawl CLI on 2026-07-10.

- DEV Community, "Dogfooding Your Own Product Isn't Enough":
  - Key point: dogfooding is useful, but developers have blind spots from familiarity with code/design.
  - Key point: dogfooding should be paired with early feedback from people who may pay.
  - URL: https://dev.to/polluterofminds/dogfooding-your-own-product-isn-t-enough-2gb9
- Bubble, "What Is Dogfooding?":
  - Key point: internal usage catches bugs and builds product empathy, but works best paired with
    external user testing.
  - Key point: Bubble's Ideaboard is a concrete product-feedback intake that helps prioritize roadmap.
  - URL: https://bubble.io/blog/dogfooding-startup-tech/
- Product Talk, "Opportunity Solution Trees":
  - Key point: start from a desired business outcome, map customer needs/pain/desires, solutions, and
    assumption tests.
  - Key point: opportunities should emerge from customer stories, not made-up internal assumptions.
  - URL: https://www.producttalk.org/opportunity-solution-trees/

Spec implication:

```text
Dais dogfood feedback + paid-user feedback + production metrics
  -> opportunity tree
  -> GitHub issues
  -> VCSDD implementation
  -> deploy
  -> metric verification
  -> lessons
```

## As-Is

```text
launchd / tmux
  |
  v
~/anicca/skills/self/life-manager-loop/life-manager-loop-cli.sh
  |
  v
Claude Sonnet session
  |
  v
CronCreate daily 09:30
  |
  v
ONE PASS
  |
  +-- STEP0 SELF-HEAL
  |     - read ~/.openclaw/state/life-manager-loop-selfheal-request.json
  |     - check Railway /health
  |     - check STRIPE_SECRET_KEY
  |     - spawn self-fix.sh life-manager on blocker
  |
  +-- STEP1 MEASURE
  |     - run loop.sh
  |     - read Stripe active subscriptions
  |     - write state/STATE.md with lm_mrr_usd
  |
  +-- STEP2 ACT
  |     - fix one Telegram onboarding funnel weakness
  |       OR
  |     - drive demand via Reddit loop
  |
  +-- STEP3 VERIFY
  |     - only real new paid Stripe subscription counts
  |
  +-- STEP4 REPORT
        - loop-report.sh life-manager
        - touch heartbeat
```

As-is gaps:

- No canonical `profitable-claude/skills/human-funded/life-manager/` business loop yet.
- Feedback from Telegram/user chat is not normalized into GitHub issues.
- Product development and marketing are not represented as two first-class subloops.
- Event application skills exist, but are not integrated into Life Manager's product loop.
- Calendar travel-time skill exists, but is not the explicit paid wedge and cadence artifact.
- CEO can observe/score Life Manager but cannot yet enforce budget/frequency for this loop.

## To-Be

```text
Life Manager Cloud Product
  |
  +-- Telegram bot/chat
  +-- Google Calendar connector
  +-- Gmail connector
  +-- Phone/call service
  +-- Stripe billing
  +-- per-user memory/context/ideals
  +-- event/action executor
  |
  v
Product Telemetry + Feedback Ledger
  |
  +-- telegram_feedback.jsonl
  +-- onboarding_funnel.jsonl
  +-- calendar_actions.jsonl
  +-- phone_calls.jsonl
  +-- event_applications.jsonl
  +-- stripe_mrr.jsonl
  +-- marketing_metrics.jsonl
  |
  v
Life Manager Business Manager Loop
  |
  +-- INTAKE
  |     - read user feedback from Telegram
  |     - read Dais dogfood feedback
  |     - read paid-user feedback
  |     - read production metrics
  |
  +-- TRIAGE
  |     - group into opportunity tree:
  |       outcome -> opportunity -> solution -> assumption test
  |     - create/update GitHub issues with labels:
  |       product:life-manager
  |       lm:type:{bug,feature,growth,retention,self-heal}
  |       lm:source:{telegram,metric,dogfood,paid-user,competitor}
  |
  +-- PICK
  |     - choose highest EV issue toward activation/MRR/retention/trust
  |
  +-- BUILD
  |     - VCSDD spec -> tests -> implementation
  |     - deploy cloud product
  |
  +-- MARKET
  |     - create daily social content from pain points
  |     - Reddit/X/IG/TikTok/YouTube funnel
  |     - use existing money-printer/video/article skills where verified
  |
  +-- VERIFY
  |     - feature works for Dais tenant and at least one generalized tenant path
  |     - metric changed or evidence says no-change
  |
  +-- LEARN
        - close/update issue
        - append lessons.jsonl
        - report to CEO cost/revenue ledger
```

## Full To-Be: CEO Portfolio vs Life Manager Product Loop

The current system keeps CEO and Life Manager separate. CEO is the portfolio allocator. Life Manager
is one product business inside that portfolio.

Explorer is not a peer of CEO and is not a separate top-level system. Explorer is one manager
business loop under CEO, alongside gig, bounty, affiliate, video, article, pm/hl, capafy, and
life-manager. Explorer's business output is new validated business opportunities and CEO proposals.

```text
                         DAIS / CLAUDE-P LOCAL RUNTIME
                                      |
                                      v
        =========================================================
        |                    CEO LOOP                           |
        |       company / portfolio allocator for businesses     |
        =========================================================
        | reads per-business:                                   |
        |   - Claude local token / subscription runway           |
        |   - cost from record-cost-event.sh                     |
        |   - revenue / MRR / realized profit                    |
        |   - cadence health                                     |
        |   - evidence quality                                   |
        |   - weekly evaluation score                            |
        |                                                       |
        | decides:                                               |
        |   - double down                                        |
        |   - reduce frequency                                   |
        |   - pause                                              |
        |   - spawn                                              |
        |   - keep alive / conserve compute                      |
        =========================================================
          |
          v
        =========================================================
        |              MANAGER BUSINESS LOOPS                   |
        =========================================================
        | gig loop                                               |
        | bounty loop                                            |
        | affiliate loop                                         |
        | video loop                                             |
        | article loop                                           |
        | pm / hl trade loop                                     |
        | capafy loop                                            |
        | explorer loop                                          |
        |   - pain-point intake                                  |
        |   - same-day validation                                |
        |   - evidence artifact                                  |
        |   - CEO proposal                                       |
        | life-manager loop                                      |
        =========================================================
          |
          v
        =========================================================
        |                 LIFE MANAGER LOOP                     |
        |        product business manager for Life Manager       |
        =========================================================
        | owns:                                                  |
        |   - Life Manager cloud product improvement             |
        |   - product self-heal                                  |
        |   - user feedback -> GitHub issues                     |
        |   - product marketing                                  |
        |   - product revenue / MRR                              |
        |   - product-internal API cost/outcome ledgers          |
        |   - product evidence reports to CEO                    |
        =========================================================
                         |                         |
                         v                         v
        +--------------------------------+  +------------------------------+
        | github.com/Daisuke134/         |  | github.com/Daisuke134/       |
        | life-manager                   |  | profitable-claude            |
        |                                |  |                              |
        | product code                   |  | CEO + harness + runner       |
        | product issues                 |  | cadence/evidence/verifier    |
        | cloud app                      |  | life-manager loop wrapper    |
        +--------------------------------+  +------------------------------+
                         |
                         v
        =========================================================
        |              LIFE MANAGER CLOUD PRODUCT               |
        |      Telegram + Calendar + Gmail + Phone + Stripe      |
        =========================================================
                         |
                         v
        "Your life starts moving on autopilot."
```

Decision:

- CEO loop does not become Life Manager now.
- CEO loop treats Life Manager as one business/product among other businesses.
- Life Manager loop tracks product-internal API costs and user outcome evidence because that is part
  of operating the Life Manager product.
- CEO receives Life Manager's summarized product health: MRR, product cost, cadence, evidence, and
  evaluation score.
- Long-term, Life Manager can absorb other user-benefit loops when those loops become product
  features. Until absorption, those loops remain separate CEO-managed businesses.
- MAIN / Agent Economy remains separate from both CEO portfolio and Life Manager product.

Long-term merge path:

```text
phase 0 current:
  profitable-claude CEO manages many loops
  life-manager is one loop/business
  life-manager repo is product code

phase 1:
  life-manager loop proves product dev + self-heal + marketing + MRR
  product-internal ledgers become reliable

phase 2:
  user-benefit loops are converted into Life Manager product modules
  examples: calendar, phone, environment pull, connector, media, money/career

phase 3:
  stable user-benefit modules move from profitable-claude into life-manager repo
  CEO still exists as allocator during migration

phase 4:
  Life Manager repo becomes the single cloud product for the user-facing side
  profitable-claude remains only for non-product / agent-economy / founder-runtime needs
```

## Future Full To-Be: Cloud Personal CEO Inside Life Manager

This section is explicitly **future / out of current implementation scope**. The previous section is
the current architecture. Do not implement this until Life Manager has proven product dev, self-heal,
marketing, MRR, tenant isolation, API cost ledgers, and real user outcome evidence.

Future target:

```text
                         HUMAN / PAID USER
                                |
                                v
        =========================================================
        |                    LIFE MANAGER                       |
        |  "A Claude that takes care of you financially,         |
        |   physically, and mentally."                           |
        =========================================================
                                |
                                v
        ---------------------------------------------------------
        | MINIMUM-QUESTION ONBOARDING                           |
        | - What do you want out of life?                        |
        | - Connect Telegram / Calendar / Gmail / phone / Stripe |
        | - Infer missing context instead of asking repeatedly   |
        ---------------------------------------------------------
                                |
                                v
        =========================================================
        |              PERSONAL CEO INSIDE LIFE MANAGER          |
        |     CEO of this user's life, running in the cloud       |
        =========================================================
        | reads direct reports from product modules:              |
        |   - user goals / ideals                                |
        |   - module outcome evidence                            |
        |   - per-tenant API/token spend                         |
        |   - subscription margin                                |
        |   - safety/consent boundaries                          |
        |                                                        |
        | allocates:                                              |
        |   - Claude API tokens                                  |
        |   - phone calls                                        |
        |   - outreach effort                                    |
        |   - marketing/media work for the user                  |
        |   - money/career work                                  |
        =========================================================
          |             |             |             |           |
          v             v             v             v           v
      calendar       phone       environment    connector     money
      module         module      pull module    module        module
      travel/prep    calls       events         intros        career
      lateness       wake/sleep  retreats       podcast      trading*
          |             |             |             |           |
          v             v             v             v           v
      media        personal       product       meta-        self-heal
      module       marketing      dev loop      marketing    loop
      podcast      user's brand   improves      markets      repairs
      articles     audience       product       product      product
          |             |             |             |           |
          +-------------+-------------+-------------+-----------+
                                |
                                v
        ---------------------------------------------------------
        | AFTER-ACTION REPORTING                                |
        | - "I registered you for this event."                   |
        | - "I added travel time."                              |
        | - "I emailed this guest."                             |
        | - "I shipped this product improvement."                |
        | User can cancel/correct after the fact.                |
        ---------------------------------------------------------
                                |
                                v
        "Your life starts moving on autopilot."
```

`trading*` remains future and requires strict permission, wallet isolation, legal/risk boundaries,
and real loss limits. Do not include trading in the initial Life Manager SaaS promise.

Future merge rule:

```text
Only move a loop into Life Manager when:
  - it has a cloud product module boundary,
  - per-tenant permissions exist,
  - per-tenant API/capital cost is ledgered,
  - user outcome evidence is machine-checkable,
  - cancellation/undo path exists where applicable,
  - CEO can still receive a summarized business report during migration.
```

## Product Subloops

### 1. Travel-Time Autopilot Loop

Goal:

```text
Every physical calendar event has realistic leave/prep/travel time.
```

MVP:

- Import/vendor `calendar-with-travel-time`.
- Generalize hard-coded Dais home address into per-user home/work locations.
- Detect physical events from Google Calendar.
- Add or update travel/prep blocks.
- Send Telegram report after action.

Cadence artifact:

```text
life-manager/state/calendar-actions.jsonl
{ts,user_id,event_id,action:"travel_time_added",origin,destination,travel_min,calendar_url}
```

Verification:

- Google Calendar event exists.
- Travel/prep event starts before target event.
- Description contains route/travel evidence.

### 2. Phone Lateness Guard Loop

Goal:

```text
The user is called before they must leave, wake, sleep, or act.
```

MVP:

- Call 10/5 minutes before leave time.
- If live location or user response indicates late risk, notify stakeholder if allowed.
- Write call/result ledger.

Cadence artifact:

```text
life-manager/state/calls.jsonl
{ts,user_id,event_id,call_sid,result,late_risk,stakeholder_notified}
```

### 3. Environment Pull Loop

Goal:

```text
Move the user into environments where their ideal identity is normal.
```

Sources:

- Existing `opportunity-calendar` skill for Tokyo AI/LT/comedy/mokumoku events.
- Existing `anicca-meetup-talk-applier` for Luma/connpass/meetup talk slots.
- Future generalized source adapters: Luma, connpass, Meetup, local retreat centers, running clubs,
  Buddhist temples/retreats, podcast guests, job/networking events.

MVP for Dais/Japan:

- Search Luma/connpass Tokyo events relevant to:
  - AI/AGI/crypto
  - Buddhism/meditation
  - comedy
  - founder/startup/networking
- Apply/register when compatible with calendar constraints.
- Add event to Google Calendar with travel time.
- Report after registration on Telegram.

Cadence artifact:

```text
life-manager/state/event-applications.jsonl
{ts,user_id,source,event_url,title,start,city,status,gcal_event_id,ideal_matched}
```

### 4. Connector / Intro Loop

Goal:

```text
Help the user meet people who pull them toward their stated ideals.
```

MVP:

- For Dais: podcast guest outreach in AI/AGI/crypto/Buddhism/comedy.
- Search target people/events.
- Draft and send cold email only when sender identity/permission is configured.
- Book accepted calls into calendar.

Guardrail:

- For paid users, outbound email/reply requires explicit onboarding consent and per-user sending
  identity. The product reports actions after completion, but the user can cancel/undo future items.

### 5. Product Development Loop

Goal:

```text
User feedback and metrics become GitHub issues; issues become merged product changes.
```

Issue schema:

```yaml
title: "[life-manager] <short outcome/problem>"
labels:
  - product:life-manager
  - lm:type:feature|bug|growth|retention|self-heal
  - lm:source:telegram|metric|dogfood|paid-user|competitor
body:
  source_event_id: "<telegram_message_id|metric_row|feedback_id>"
  user_segment: "dogfood|paid|trial|anonymous"
  opportunity: "<customer need/pain/desire>"
  desired_outcome: "activation|mrr|retention|trust|call_success|calendar_success"
  evidence: "<url/log/path/id>"
  proposed_assumption_test: "<how to verify this is worth building>"
  success_metric: "<machine-measurable metric>"
```

### 6. Marketing Loop

Goal:

```text
Life Manager gets users while product improves.
```

Primary market message:

- "No more Google Maps for every event."
- "Your calendar now includes when to leave."
- "If you are about to be late, Life Manager handles it."
- "Your life starts moving on autopilot."

Channels:

- Reddit: honest builder participation, not covert promotion.
- X: pain-point posts, demo clips, build-in-public.
- IG/TikTok/YouTube Shorts: short pain/wedge videos.
- Lab Slack / school channels: targeted dogfood distribution.

Cadence artifact:

```text
life-manager/state/marketing-actions.jsonl
{ts,channel,post_url,creative_id,pain_point,cta,views,clicks,signups}
```

## Internal vs External Feedback Policy

Use both from day one:

```text
Dais dogfood
  = deepest context, fastest iteration, catches daily-life bugs

External users
  = paid reality, onboarding friction, edge cases that Dais cannot see
```

Rules:

- Dais feedback is never automatically treated as universal.
- Paid-user feedback and production metrics can override Dais preference.
- If Dais asks for a feature, Life Manager loop creates an issue with `lm:source:dogfood`.
- If multiple users ask similar things, merge into one opportunity and raise priority.
- If a metric drops without explicit feedback, create `lm:source:metric` issue.

## Seed Product Issues Created

The following product issues were created in `github.com/Daisuke134/life-manager` on 2026-07-10 from
Dais dogfood/strategy feedback. The Life Manager loop must treat these as the initial product backlog.

| # | URL | Capability |
|---|---|---|
| 1 | https://github.com/Daisuke134/life-manager/issues/1 | Minimum-question onboarding with inferred context |
| 2 | https://github.com/Daisuke134/life-manager/issues/2 | Travel-time calendar wedge for physical events |
| 3 | https://github.com/Daisuke134/life-manager/issues/3 | Phone wake, leave, sleep, and lateness guard |
| 4 | https://github.com/Daisuke134/life-manager/issues/4 | Environment pull via Luma and connpass events |
| 5 | https://github.com/Daisuke134/life-manager/issues/5 | Connector and podcast guest outreach loop |
| 6 | https://github.com/Daisuke134/life-manager/issues/6 | Feedback-to-GitHub issue self-improvement loop |
| 7 | https://github.com/Daisuke134/life-manager/issues/7 | Product marketing loop for Life Manager itself |
| 8 | https://github.com/Daisuke134/life-manager/issues/8 | Product API cost and user-outcome ledgers |
| 9 | https://github.com/Daisuke134/life-manager/issues/9 | Future design: cloud personal CEO inside Life Manager |

## CEO / MAIN Relationship

```text
MAIN loop
  - builds/repairs the loop system itself
  - terminal architect
  - outside CEO
  - CEO observes MAIN cost but cannot halt it

CEO loop
  - manages business portfolio
  - Life Manager is one business arm
  - can reduce/pause/double-down Life Manager like other businesses

Life Manager loop
  - business manager for one product
  - owns product dev + marketing + support feedback triage
```

ASCII:

```text
                         MAIN LOOP
                builds/repairs/hands off system
                              |
                              v
        ------------------------------------------------
        |                   CEO LOOP                   |
        |  revenue/cost/runway/health/portfolio alloc  |
        ------------------------------------------------
                              |
                              v
        ------------------------------------------------
        |            MANAGER BUSINESS LOOPS            |
        ------------------------------------------------
        | gig / bounty / affiliate / video / article   |
        | pm-hl trade / capafy / explorer              |
        | life-manager                                 |
        ------------------------------------------------
             |                         |
             v                         v
   explorer validates             life-manager improves
   new opportunities              product + marketing + user life ops
```

## CEO Requirements Added By Life Manager

CEO keeps the existing portfolio-manager job. Life Manager adds one more business arm that CEO can
score, pause, reduce, or double down. Product-internal API cost/outcome accounting is owned by the
Life Manager loop, then summarized upward to CEO.

MUST:

1. `ceo-budget-config.json` exists with per-loop monthly/weekly soft/hard limits.
2. Each loop appends cost via `record-cost-event.sh`.
3. Launchers/healthchecks read `loop-registry.json` and honor:
   - `allocation.status = paused`
   - `pass_frequency_multiplier`
   - `capital_cap_usd`
4. Claude subscription/rate-limit errors are parsed into a `compute_runway` ledger:
   ```json
   { "ts": "...", "provider": "claude", "status": "weekly_limit", "reset_at": "...", "affected_loops": [...] }
   ```
5. When compute runway is low, CEO must:
   - keep only highest-EV loops alive,
   - pause non-revenue loops,
   - defer marketing generation if no conversion evidence,
   - keep self-heal/verification minimal,
   - report "company alive but conserving compute."

## Life Manager Loop Requirements

MUST:

1. Cloud Life Manager appends per-tenant cost/outcome rows:
   ```json
   {
     "ts": "...",
     "tenant_id": "...",
     "loop": "calendar|phone|events|media|money",
     "provider": "claude_api|twilio|google|gmail|search|cloud",
     "cost_usd": 0.0,
     "input_tokens": 0,
     "output_tokens": 0,
     "outcome": "travel_time_added|call_completed|event_registered|intro_sent|revenue_created",
     "evidence": "url-or-ledger-id"
   }
   ```
2. Life Manager loop computes product-internal outcome ROI:
   ```text
   life_manager_outcome_roi = verified_user_outcome_score / product_api_cost_usd
   ```
3. Life Manager loop uses this ROI to improve product behavior, reduce wasteful product actions, and
   decide what product feature/marketing issue to pick next.
4. Life Manager loop reports summarized business health to CEO:
   ```json
   {
     "loop": "life-manager",
     "mrr_usd": 0.0,
     "product_api_cost_usd": 0.0,
     "product_marketing_cost_usd": 0.0,
     "verified_user_outcomes": 0,
     "cadence_ok": true,
     "evidence_url_or_path": "..."
   }
   ```
5. CEO uses the summary like any other business loop. CEO does not inspect every phone/Gmail/Google
   row unless Life Manager reports a blocker or evidence audit requires it.

## VCSDD Implementation Plan

### Phase A: Spec + intake

- Create `profitable-claude/skills/human-funded/life-manager/`.
- Vendor `calendar-with-travel-time`, `opportunity-calendar`, `anicca-meetup-talk-applier` as local copies.
- Add `life-manager-cli.sh`, `life-manager-healthcheck.sh`, `README.md`.
- Seed `github.com/Daisuke134/life-manager` product issues for the capabilities Dais requested:
  - minimum-question onboarding and inferred context,
  - travel-time calendar wedge,
  - phone/lateness guard,
  - Luma/connpass environment pull,
  - connector/podcast guest outreach,
  - feedback-to-issue self-improvement,
  - product marketing loop,
  - product API cost/outcome ledgers,
  - future cloud personal CEO architecture as out-of-scope design issue.
- Add ledgers:
  - `state/feedback.jsonl`
  - `state/issues.jsonl`
  - `state/calendar-actions.jsonl`
  - `state/event-applications.jsonl`
  - `state/marketing-actions.jsonl`
  - `state/lessons.jsonl`

### Phase B: Feedback-to-issue

- Telegram feedback ingestion creates or updates GitHub issues.
- Issue creation is deterministic enough to verify:
  - source id present
  - evidence present
  - success metric present
  - label set present
- Agent judgment is only for grouping/priority.

### Phase C: Travel-time wedge

- Generalize `calendar-with-travel-time`.
- Run for Dais tenant first.
- Verify Google Calendar changes.
- Market wedge with one daily creative.

### Phase D: Event/environment pull

- Generalize `opportunity-calendar` and `anicca-meetup-talk-applier`.
- For Dais/Japan: Luma + connpass Tokyo.
- Add Buddhism/running/founder/AI/crypto source adapters.
- Register to Calendar with travel time.
- Telegram after-action report.

### Phase E: Product + marketing EDD

- Weekly evaluator:
  - activation rate
  - paid MRR
  - retention
  - travel-time events added
  - call success
  - event applications accepted
  - marketing signups
- Search + metrics self-improve always both:
  - cold-start: search heavier
  - traction: metrics heavier
- Lessons feed next pass.

### Phase F: CEO enforcement

- Add Life Manager to `cadence-contracts.json`.
- Add Life Manager to `verify-loops.sh`, `verify-loops-audit.sh`, `cadence-deadline-check.sh`.
- Add Life Manager cost events.
- Add CEO budget config.
- Make healthchecks/launchers honor CEO registry pause/frequency.

## Done Conditions

1. Life Manager exists as a `profitable-claude` business loop.
2. Initial requested capabilities are present as product issues in `github.com/Daisuke134/life-manager`
   with source/evidence/success metric.
3. Telegram feedback can create a GitHub issue with source/evidence/success metric.
4. Calendar travel-time action writes a ledger row and is verified against Google Calendar.
5. Luma/connpass event application writes a ledger row and creates Google Calendar event.
6. Marketing action writes URL/views/clicks/signups if available.
7. `loop-report.sh life-manager` sends evidence mail with non-empty evidence or `none: <reason>`.
8. CEO reads Life Manager cost/revenue/health and can pause/reduce frequency.
9. Fresh adversary review passes with:
   - no orphan wiring,
   - no fake metric,
   - non-dict JSONL rows do not crash,
   - same disease checked across all ledgers,
   - no AI-use disclosure copy in user-facing marketing spec.

## Non-Goals

- Do not market the initial wedge as "AGI does everything."
- Do not build a Dais-only fork that cannot become SaaS.
- Do not auto-send third-party emails for paid users without explicit configured sending consent.
- Do not fabricate event applications, calendar actions, views, or MRR.
- Do not rely on notifications alone as behavior change. The product changes environment: calendar,
  phone, events, meetings, intros.
