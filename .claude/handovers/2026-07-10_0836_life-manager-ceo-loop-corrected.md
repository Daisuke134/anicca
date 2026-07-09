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

## Implementation Goal For Next Claude

/goal Build the Life Manager business loop under profitable-claude CEO, without changing CEO's role.

Done:

1. Read:
   - `docs/superpowers/specs/2026-07-10-life-manager-autopilot-product-loop-design.md`
   - `docs/superpowers/specs/2026-07-08-claude-p-loop-verification-evidence-design.md`
2. Inspect:
   - `/Users/anicca/Projects/life-manager`
   - `/Users/anicca/profitable-claude`
3. In profitable-claude, add or fix Life Manager business-loop runner:
   - `skills/human-funded/life-manager/`
   - `life-manager-cli.sh`
   - healthcheck
   - README
   - cadence/evidence/report wiring
4. Life Manager loop creates/updates product issues in `github.com/Daisuke134/life-manager`.
5. Life Manager loop has product ledgers:
   - feedback
   - issues
   - calendar actions
   - phone calls
   - event applications
   - marketing actions
   - product API costs
   - Stripe MRR
   - lessons
6. Life Manager cloud wedge works:
   - Telegram onboarding
   - Google Calendar physical event detection
   - travel/prep/leave-time block
   - Telegram after-action report
   - evidence ledger
7. Life Manager loop self-improves:
   - feedback/metrics/cost/failures -> issue
   - issue -> VCSDD implementation
   - deploy -> real evidence verification
   - lessons.jsonl
8. Life Manager loop markets itself:
   - marketing action URL
   - views/clicks/signups if available
   - no fake metrics
9. CEO sees Life Manager as one business:
   - MRR
   - product cost summary
   - cadence
   - evidence
   - evaluation score
   - can pause/reduce/double-down via registry
10. Do not implement MAIN / Agent Economy loop in this session.

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

