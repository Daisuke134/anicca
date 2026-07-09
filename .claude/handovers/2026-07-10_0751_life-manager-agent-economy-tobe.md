# SUPERSEDED

Use `.claude/handovers/2026-07-10_0836_life-manager-ceo-loop-corrected.md` instead.

This file mixed CEO and Life Manager too much. Corrected architecture:

```text
CEO loop = portfolio manager for all profitable-claude businesses.
Life Manager loop = one product business loop under CEO.
Life Manager loop owns product dev / self-heal / marketing / product API cost / user outcome.
CEO receives Life Manager summary and allocates company-level resources.
```

# Dais handover: Life Manager / Agent Economy To-Be split（2026-07-10 07:51 JST）

## Context

User decision:

- Life Manager is not a local-only product. The canonical product is cloud-first.
- Users use `aniccaai.com/life-manager` + Telegram + Calendar/Gmail/phone/Stripe.
- Local claude-p / profitable-claude may orchestrate, verify, and improve the cloud product until the
  cloud self-improvement runtime is mature.
- Do not create a Dais-only fork.

Repo routing:

```text
github.com/Daisuke134/life-manager
  - product code
  - user-facing product issues
  - product PRs

github.com/Daisuke134/profitable-claude
  - loop runtime
  - CEO allocator
  - evidence/cadence/verifier
  - feedback-to-issue automation

github.com/Daisuke134/anicca-project
  - specs and handovers
```

Current local facts:

- Product repo exists at `/Users/anicca/Projects/life-manager`
  - remote: `https://github.com/Daisuke134/life-manager.git`
  - branch: `main`
- Specs updated:
  - `docs/superpowers/specs/2026-07-10-life-manager-autopilot-product-loop-design.md`
  - `docs/superpowers/specs/2026-07-08-claude-p-loop-verification-evidence-design.md`

## Core Architecture Decision

There are two top-level purposes:

```text
                         USER / DAIS / PAID TENANT
                                  |
                                  v
        =====================================================
        |         LIFE MANAGER / PERSONAL CEO SIDE          |
        | purpose: serve this one human / paid tenant       |
        =====================================================
                                  |
                                  v
        -----------------------------------------------------
        | PERSONAL CEO                                      |
        | - watches API token spend and outcome ROI          |
        | - allocates user-benefit loops                     |
        | - pauses waste                                     |
        | - doubles down on proven helpful/revenue loops     |
        -----------------------------------------------------
          |            |            |            |          |
          v            v            v            v          v
      calendar       phone       events       media      money
      travel         calls       Luma/        podcast   user financial
      autofill       lateness    connpass     articles  health loops
                                  |
                                  v
                 "Your life starts moving on autopilot."


        =====================================================
        |          MAIN / AGENT ECONOMY LOOP SIDE           |
        | purpose: create and fund the agent economy        |
        =====================================================
                                  |
                                  v
        -----------------------------------------------------
        | AGENT ECONOMY MAIN                                |
        | - builds Anicca / Blockrun / agent economy infra   |
        | - runs self-funded earn/crypto/trading loops       |
        | - funds agent economy from earned capital          |
        | - graduates from human-funded Anthropic to crypto  |
        |   funded ClawRouter/self-funded runtime            |
        | - becomes unnecessary when agent economy sustains  |
        |   itself without outside vendor/human funding      |
        -----------------------------------------------------
                                  |
                                  v
                    self-sustaining agent economy
```

Boundary rule:

- A loop that earns money for one user/person belongs to Life Manager / Personal CEO.
- A loop that earns money to fund the agent economy itself belongs to MAIN / Agent Economy.
- The same algorithm may exist on both sides, but wallets, ledgers, budgets, and success metrics are
  separate.
- While local claude-p loops consume the same physical Claude subscription/token runway, every cost
  must be written to a global budget ledger and protected by a `global-budget-guardian`.
- Cloud to-be uses API spend ledgers instead:
  - Claude API tokens,
  - phone API,
  - Google/Gmail API,
  - search/scrape,
  - cloud infra.
- Personal CEO allocation target is:
  ```text
  minimum API spend that moves the user toward the ideal self
  ```

## Life Manager Product Principle

```text
Ask less.
Infer more.
Act first when safe.
Report after action.
Let the user cancel/correct.
```

MUST:

1. Onboarding asks only:
   - what the user wants out of life,
   - connector/permission/billing requirements.
2. If the user is vague, default goals are:
   - physically healthy,
   - mentally healthy,
   - financially healthy,
   - trusted by other people,
   - connected to useful environments.
3. Missing context is obtained from Calendar/Gmail/public search/action history/feedback.
4. Most actions are after-action report, not permission request.
5. Third-party sending, payments, legal/high-risk actions require explicit consent/config.

## Product Wedge

Initial paid wedge:

```text
Google Calendarを接続すると、物理予定ごとに移動時間・出発時刻・準備時間を自動で埋める。
出発前に電話し、遅刻しそうなら関係者連絡まで処理する。
```

Core phrases:

- Your life starts moving on autopilot.
- Your ideal life, without you in the loop.

## Required Implementation Goal

/goal Life Manager cloud product + profitable-claude Life Manager loop + Agent Economy MAIN split を VCSDD で実装する。

Done:

1. `github.com/Daisuke134/life-manager` is the product issue/PR destination.
2. `github.com/Daisuke134/profitable-claude` contains the Life Manager business-manager runner:
   - cadence
   - evidence
   - feedback-to-issue
   - loop-report
   - CEO cost/revenue wiring
3. Telegram/Dais/paid-user feedback becomes GitHub issues in `life-manager` with:
   - `product:life-manager`
   - `lm:type:bug|feature|growth|retention|self-heal`
   - `lm:source:telegram|metric|dogfood|paid-user|competitor`
   - source_event_id
   - evidence
   - success_metric
4. Travel-time wedge works on the cloud product:
   - physical Google Calendar event detected
   - travel/prep/leave-time block created
   - ledger row written
   - Telegram after-action report sent
5. Phone/lateness guard works:
   - call before departure/wake/sleep/important event
   - lateness risk written to ledger
   - stakeholder notification only when consent/config exists
6. Environment pull works for Dais/Japan first:
   - Luma/connpass Tokyo events
   - AI/AGI/crypto/Buddhism/comedy/founder/startup interests
   - registration/application evidence
   - Google Calendar event with travel time
   - Telegram after-action report
7. Life Manager self-improvement loop works:
   - feedback/metrics -> issue
   - issue -> VCSDD implementation
   - deploy -> metric verification
   - lessons.jsonl
8. CEO / Personal Life Manager side can pause/reduce/double-down user-benefit loops by registry.
   Allocation is based on per-tenant API cost and verified outcome ROI, not merely whether the user
   is subscribed.
9. MAIN / Agent Economy side is separated from Personal CEO:
   - separate wallet/ledger/purpose/success metrics
   - crypto/trading loops that fund agent economy live under MAIN
   - crypto/trading loops for one user's financial health live under Personal CEO
10. `global-budget-guardian` exists or is specified:
    - subscription weekly limit detection
    - per-loop cost ledger
    - disk guard
    - wallet drain guard
    - pause lower-EV loops when runway is low
11. Evidence is real:
    - no fake MRR
    - no fake applications
    - no fake calendar events
    - no fake public URLs
    - if revenue is zero, report zero.

Constraints:

- Answer and docs in Japanese unless code/spec structure requires English.
- Use Firecrawl CLI for web search.
- Use Context7 CLI for document/library lookup.
- No human-in-loop execution requests to Dais.
- Do not ask "which option do you prefer"; decide and explain.
- No AI-use disclosure copy in marketing specs where prohibited.
- Submodule禁止。polyrepo + vendor/copy.
- Machine verification before claiming LIVE.

Order:

1. Read both updated specs.
2. Inspect `/Users/anicca/Projects/life-manager`.
3. Inspect `/Users/anicca/profitable-claude`.
4. Add Life Manager loop runner/harness to profitable-claude.
5. Add feedback-to-issue path targeting life-manager repo.
6. Implement cloud product wedge in life-manager repo.
7. Wire CEO allocation and global budget guard.
8. Verify with real calendar/Telegram/evidence ledgers.
9. Commit/push each repo separately.
10. Send evidence mail to `keiodaisuke@gmail.com`.

Spec source of truth:

- `docs/superpowers/specs/2026-07-10-life-manager-autopilot-product-loop-design.md`
- `docs/superpowers/specs/2026-07-08-claude-p-loop-verification-evidence-design.md`
