# Dais handover: Life Manager business loop under CEO（2026-07-10 08:36 JST）

## Correction

Do not merge CEO and Life Manager in the current implementation.

Correct current architecture:

```text
CEO loop
  = portfolio manager for all profitable-claude businesses

Life Manager loop
  = one product business loop under CEO
  = product manager for the Life Manager cloud product
```

The CEO's job does not change. CEO watches each business loop at the company level:

- local Claude token/subscription runway,
- per-loop cost events,
- revenue / MRR / realized profit,
- cadence health,
- evidence quality,
- weekly evaluation score.

CEO decides:

- double down,
- reduce frequency,
- pause,
- spawn,
- conserve compute.

The Life Manager loop owns product-internal details:

- phone API cost,
- Google/Gmail API cost,
- Claude API cost for the cloud product,
- cloud infra cost,
- user outcome evidence,
- product dev,
- product self-heal,
- product marketing,
- feedback-to-GitHub-issue,
- product MRR.

Life Manager loop reports a summary upward to CEO. CEO does not directly manage every phone/Gmail row.

## Full To-Be ASCII

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
          |             |              |             |          |
          v             v              v             v          v
      gig loop     bounty loop    affiliate loop   video   life-manager
                                                     loop       loop
                                                                |
                                                                v
        =========================================================
        |                 LIFE MANAGER LOOP                     |
        |        product business manager for Life Manager       |
        =========================================================
        | owns:                                                  |
        |   - Life Manager cloud product improvement             |
        |   - product self-heal                                  |
        |   - Telegram/user feedback -> GitHub issues            |
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

## Full Profitable-Claude To-Be

This is the immediate architecture to build in `github.com/Daisuke134/profitable-claude`.
Life Manager is only one managed business. The important work is to build the loops that keep
creating, improving, verifying, and allocating all businesses.

```text
github.com/Daisuke134/profitable-claude
        |
        v
===============================================================
|                    STARTABLE LOOP REPO                      |
|  clone -> configure env -> start-all -> status -> evidence   |
===============================================================
        |
        +-- bin/start-all.sh
        +-- bin/status.sh
        +-- config/loop-registry.json
        +-- config/ceo-budget-config.json
        +-- ledgers/cost-events.jsonl
        +-- ledgers/loop-evaluations.jsonl
        +-- ledgers/ceo-decisions.jsonl
        +-- ledgers/lessons.jsonl
        |
        v
===============================================================
|                         CEO LOOP                            |
| company portfolio manager                                   |
===============================================================
| input:                                                       |
|   - each loop cadence/evidence                              |
|   - each loop real revenue / MRR / realized profit           |
|   - each loop token/cost ledger                              |
|   - Claude weekly/subscription runway                        |
|   - disk and process health                                  |
|                                                              |
| output:                                                      |
|   - pause / reduce / normal / double_down / spawn            |
|   - pass_frequency_multiplier                                |
|   - capital_cap_usd                                          |
|   - fleet/account count                                      |
|   - loop-specific next objective                             |
===============================================================
        |
        |
        v
===============================================================
|                  MANAGER BUSINESS LOOPS                     |
===============================================================
| gig                                                          |
| bounty                                                       |
| affiliate                                                    |
| video                                                        |
| article                                                      |
| pm/hl trade                                                  |
| capafy                                                       |
| explorer                                                     |
|   - X/Reddit/pain points                                     |
|   - same-day validation                                      |
|   - evidence URL/artifact                                    |
|   - proposes new business to CEO                             |
| life-manager                                                 |
===============================================================
        |
        v
Each manager loop owns:
  - domain-specific action
  - search + metrics self-improve
  - self-heal
  - deterministic ledgers
  - evidence mail
  - lessons.jsonl
  - business summary to CEO
```

Current `profitable-claude` reality checked on 2026-07-10:

```text
present:
  README.md
  bin/start-all.sh
  bin/status.sh
  skills/human-funded/README.md

documented loops:
  bounty
  affiliate
  gig

gap:
  CEO loop is not fully present in this repo yet.
  Life Manager business loop is not present yet.
  capafy/article/pm/hl/explorer manager loops are not fully present here yet.
  start-all/status only cover bounty/affiliate/gig.
```

Therefore the next Claude must not treat the repo as complete. It must build the missing
profitable-claude harness and manager-loop structure.

## Agent Economy Context Read

This handover is for the profitable-claude CEO/Life Manager work, but the broader agent-economy
goal matters because MAIN / Agent Economy is separate work handled elsewhere.

Read status from 2026-07-10:

```text
anicca-agent-spawn:
  state: currentPhase=3
  status: contract approved, round 14 PASS; FIND-003/004 fixed in ~/anicca commit a8c3dc4
  open: Phase 3 round 3 implementation re-review still needs dispatch

anicca-spawn-identity-resolution-fix:
  state: currentPhase=init
  reality: bug was fixed and adversary-verified in ~/anicca commit f89f37c
  open: reconcile VCSDD ledger/state with shipped reality

anicca-harness-tooluse-health:
  state: currentPhase=1c
  open: requested iteration-4 verdict path was not found:
    .vcsdd/features/anicca-harness-tooluse-health/reviews/spec/iteration-4/output/verdict.json

anicca-agent-lending:
  state: complete
```

Runtime checks from 2026-07-10:

```text
Franklin LaunchAgent:
  running
  ANICCA_SPAWN_SAFETY_MARGIN=1.5
  FRANKLIN_ANALYZER_MODEL=free/glm-4.7
  FRANKLIN_ROUTER_MODEL=free/glm-4.7
  FRANKLIN_EVALUATOR_MODEL=free/glm-4.7
  FRANKLIN_MEDIA_ROUTER_MODEL=free/glm-4.7

citizens.json:
  ~/.hermes/state/citizens.json currently equals seed Franklin only
  no new cloud child observed yet

ledger:
  wake rows exist
  sampled rows do not show verified profitable:true Done evidence

citizens.json diff monitor:
  initially not found running in process list
  restarted 2026-07-10 as PID recorded in ~/.hermes/state/citizens-diff-monitor.pid
  log: ~/.hermes/logs/citizens-diff-monitor.log
  note: this is a lightweight observer, not Done evidence by itself
```

Do not claim the agent economy goal Done until both are independently verified:

1. `~/.hermes/state/citizens.json` gains a genuinely new cloud child distinct from seed.
2. `~/.blockrun/state/ledger.jsonl` or `~/.anicca/state/ledger.jsonl` has `profitable:true` backed by
   real on-chain/exchange-settled transaction evidence.

## Life Manager Product Internals

```text
                         PAID USER / DAIS DOGFOOD TENANT
                                      |
                                      v
        =========================================================
        |                 LIFE MANAGER CLOUD PRODUCT             |
        =========================================================
        | onboarding:                                            |
        |   - ask minimum questions                              |
        |   - ask what user wants out of life                    |
        |   - connect Calendar/Gmail/Telegram/phone/billing      |
        |   - infer missing context from connected data          |
        =========================================================
             |             |              |             |
             v             v              v             v
      calendar module  phone module  environment   connector/media
      travel time      wake/leave     pull          podcast/articles
      prep blocks      lateness       Luma/         intros/outreach
                                     connpass
             |             |              |             |
             +-------------+--------------+-------------+
                                      |
                                      v
        =========================================================
        |          PRODUCT LEDGERS OWNED BY LIFE MANAGER LOOP    |
        =========================================================
        | feedback.jsonl                                         |
        | issues.jsonl                                           |
        | calendar-actions.jsonl                                 |
        | phone-calls.jsonl                                      |
        | event-applications.jsonl                               |
        | marketing-actions.jsonl                                |
        | product-api-costs.jsonl                                |
        | stripe-mrr.jsonl                                       |
        | lessons.jsonl                                          |
        =========================================================
                                      |
                                      v
        feedback / metrics / failures / API cost
          -> opportunity tree
          -> GitHub issue in Daisuke134/life-manager
          -> VCSDD implementation
          -> deploy
          -> verify real evidence
          -> report business summary to CEO
```

## Repository Boundary

```text
github.com/Daisuke134/life-manager
  - Life Manager product code
  - Life Manager product issues
  - Life Manager product PRs
  - cloud Telegram/Calendar/Gmail/phone/Stripe runtime

github.com/Daisuke134/profitable-claude
  - CEO loop
  - company portfolio harness
  - cadence/evidence/verifier
  - life-manager business-loop runner
  - feedback-to-issue automation wrapper
  - local Claude token/cost accounting
```

Do not merge repos now.

Design for later migration:

```text
phase 0 now:
  profitable-claude CEO manages many loops
  life-manager is one business loop
  life-manager repo is product code

phase 1:
  life-manager loop proves product dev + self-heal + marketing + MRR

phase 2:
  user-benefit loops become Life Manager product modules
  examples: calendar, phone, environment pull, connector, media, money/career

phase 3:
  stable user-benefit modules move from profitable-claude into life-manager repo

phase 4:
  Life Manager repo becomes the single cloud product for the user-facing side
```

## Future Full To-Be ASCII

This is future and out of current implementation scope. It is correct as a destination, but do not
implement it now.

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
        | receives direct reports from cloud product modules      |
        | allocates API tokens / calls / outreach / work          |
        | optimizes for the user's ideal self                     |
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
        "Your life starts moving on autopilot."
```

Future merge rule:

```text
Only move a loop into Life Manager when:
  - it has a cloud product module boundary,
  - per-tenant permissions exist,
  - per-tenant API/capital cost is ledgered,
  - user outcome evidence is machine-checkable,
  - cancellation/undo path exists where applicable.
```

## Implementation Goal For Next Claude

/goal Build the profitable-claude CEO/manager-loop harness, then add Life Manager as one business loop under that CEO, without changing CEO's role.

Seed product issues already created in `github.com/Daisuke134/life-manager`:

1. https://github.com/Daisuke134/life-manager/issues/1
   - `[life-manager] Minimum-question onboarding with inferred context`
2. https://github.com/Daisuke134/life-manager/issues/2
   - `[life-manager] Travel-time calendar wedge for physical events`
3. https://github.com/Daisuke134/life-manager/issues/3
   - `[life-manager] Phone wake, leave, sleep, and lateness guard`
4. https://github.com/Daisuke134/life-manager/issues/4
   - `[life-manager] Environment pull via Luma and connpass events`
5. https://github.com/Daisuke134/life-manager/issues/5
   - `[life-manager] Connector and podcast guest outreach loop`
6. https://github.com/Daisuke134/life-manager/issues/6
   - `[life-manager] Feedback-to-GitHub issue self-improvement loop`
7. https://github.com/Daisuke134/life-manager/issues/7
   - `[life-manager] Product marketing loop for Life Manager itself`
8. https://github.com/Daisuke134/life-manager/issues/8
   - `[life-manager] Product API cost and user-outcome ledgers`
9. https://github.com/Daisuke134/life-manager/issues/9
   - `[life-manager] Future design: cloud personal CEO inside Life Manager`

Done:

1. Read:
   - `docs/superpowers/specs/2026-07-10-life-manager-autopilot-product-loop-design.md`
   - `docs/superpowers/specs/2026-07-08-claude-p-loop-verification-evidence-design.md`
2. Inspect:
   - `/Users/anicca/Projects/life-manager`
   - `/Users/anicca/profitable-claude`
3. In `profitable-claude`, add the missing CEO/portfolio harness:
   - `config/loop-registry.json`
   - `config/ceo-budget-config.json`
   - `ledgers/cost-events.jsonl`
   - `ledgers/loop-evaluations.jsonl`
   - `ledgers/ceo-decisions.jsonl`
   - `bin/ceo-status.sh`
   - CEO loop runner
   - deterministic pause/reduce/double-down registry enforcement
4. Update `bin/start-all.sh` and `bin/status.sh` so all current managed loops are visible, not just
   bounty/affiliate/gig.
5. In profitable-claude, add or fix Life Manager business-loop runner:
   - `skills/human-funded/life-manager/`
   - `life-manager-cli.sh`
   - healthcheck
   - README
   - cadence/evidence/report wiring
6. Life Manager loop creates/updates product issues in `github.com/Daisuke134/life-manager`.
7. Seed product issues in `github.com/Daisuke134/life-manager` for Dais-requested capabilities:
   - minimum-question onboarding and inferred context,
   - travel-time calendar wedge,
   - phone/lateness guard,
   - Luma/connpass environment pull,
   - connector/podcast guest outreach,
   - feedback-to-issue self-improvement,
   - product marketing loop,
   - product API cost/outcome ledgers,
   - future cloud personal CEO architecture as out-of-scope design issue.
8. Life Manager loop has product ledgers:
   - feedback
   - issues
   - calendar actions
   - phone calls
   - event applications
   - marketing actions
   - product API costs
   - Stripe MRR
   - lessons
9. Life Manager cloud wedge works:
   - Telegram onboarding
   - Google Calendar physical event detection
   - travel/prep/leave-time block
   - Telegram after-action report
   - evidence ledger
10. Life Manager loop self-improves:
   - feedback/metrics/cost/failures -> issue
   - issue -> VCSDD implementation
   - deploy -> real evidence verification
   - lessons.jsonl
11. Life Manager loop markets itself:
   - marketing action URL
   - views/clicks/signups if available
   - no fake metrics
12. CEO sees Life Manager as one business:
   - MRR
   - product cost summary
   - cadence
   - evidence
   - evaluation score
   - can pause/reduce/double-down via registry
13. Explorer loop exists or is explicitly stubbed with a VCSDD feature:
    - pain-point intake
    - same-day validation
    - CEO proposal artifact
    - no fake opportunities
14. Do not implement MAIN / Agent Economy loop in this session.

Constraints:

- Answer/docs in Japanese unless code structure requires English.
- Use Firecrawl CLI for web search.
- Use Context7 CLI for library/doc lookup.
- No human-in-loop request to Dais.
- Do not ask which option to choose; decide and explain.
- No fake revenue, fake calendar events, fake applications, fake public URLs.
- If revenue is zero, report zero.
- Submodule禁止。polyrepo + vendor/copy.
- Machine verification before claiming LIVE.
