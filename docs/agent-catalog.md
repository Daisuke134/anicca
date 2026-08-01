# Life Manager Agent Catalog

> GENERATED FILE — edit `agents/registry.json`, then run `node scripts/render-agent-catalog.mjs`.

This catalog contains 16 agent roles. A role is included only when model-directed observation, judgment, tool use, feedback, and effect evidence are implemented or explicitly planned.

Lifecycle is the checked-in product state. Current health, last success, leases, and receipts belong to runtime state and must be joined at presentation time.

## Executive

### Life Manager Orchestrator (`life-manager`)

Turn the user's goals and current state into bounded work for the right specialist agents, then reconcile their receipts into one honest answer.

| Field | Value |
|---|---|
| Lifecycle | 🟢 Live |
| Parent | — |
| Deployment | local + cloud |
| Effects | `read`, `draft`, `message`, `publish`, `money` |
| Skills | `cook`, `self/coordinate`, `self/issue-dev`, `self/spawn` |
| Tools | `canonical-job-protocol`, `receipt-ledger`, `policy-gates` |
| Canonical adapters | — |
| Legacy runtime families | `life-manager-runtime` |
| Source | [runtime/loop/index.mjs](../runtime/loop/index.mjs)<br>[runtime/loop/brain.mjs](../runtime/loop/brain.mjs) |
| Evidence/spec | [docs/earning-agents-reference.md](../docs/earning-agents-reference.md)<br>[runtime/loop/__tests__/brain.test.mjs](../runtime/loop/__tests__/brain.test.mjs) |

## Health

### Mental Health Agent (`health.mental`)

Provide bounded mental-health support, reflection, and escalation while keeping deterministic safety policy outside the model.

| Field | Value |
|---|---|
| Lifecycle | ⚪ Planned |
| Parent | Life Manager Orchestrator |
| Deployment | local + cloud |
| Effects | `read`, `draft`, `message` |
| Skills | — |
| Tools | `mental-runtime`, `precepts-runtime`, `feedback-intake` |
| Canonical adapters | — |
| Legacy runtime families | — |
| Source | — |
| Evidence/spec | [docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md](../docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md) |

### Physical Health Agent (`health.physical`)

Coordinate sleep, exercise, diet, appointments, and physical aftercare without inventing medical facts.

| Field | Value |
|---|---|
| Lifecycle | ⚪ Planned |
| Parent | Life Manager Orchestrator |
| Deployment | local + cloud |
| Effects | `read`, `draft`, `message` |
| Skills | — |
| Tools | `calendar`, `care-runtime`, `diet-runtime` |
| Canonical adapters | — |
| Legacy runtime families | — |
| Source | — |
| Evidence/spec | [docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md](../docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md) |

## Finance / CFO

### Capafy Agent (`finance.capafy`)

Choose, build, publish, verify, and improve Capafy marketplace listings toward real subscriber revenue.

| Field | Value |
|---|---|
| Lifecycle | 🟠 Legacy live |
| Parent | CFO Lead Agent |
| Deployment | local |
| Effects | `read`, `draft`, `publish`, `money` |
| Skills | — |
| Tools | `capafy-marketplace`, `browser`, `sales-selector`, `self-fix` |
| Canonical adapters | — |
| Legacy runtime families | `capafy-loop` |
| Source | [skills/self/capafy-loop/capafy-loop-daily.sh](../skills/self/capafy-loop/capafy-loop-daily.sh)<br>[skills/self/capafy-loop/capafy-loop-cli.sh](../skills/self/capafy-loop/capafy-loop-cli.sh) |
| Evidence/spec | [docs/superpowers/specs/2026-07-19-capafy-skills-landing.md](../docs/superpowers/specs/2026-07-19-capafy-skills-landing.md) |

### CFO Lead Agent (`finance.cfo`)

Choose the financial question, delegate only the needed specialists, and explain reconciled personal and agent-economy results to the user.

| Field | Value |
|---|---|
| Lifecycle | ⚪ Planned |
| Parent | Life Manager Orchestrator |
| Deployment | local + cloud |
| Effects | `read`, `draft`, `message`, `money` |
| Skills | `report`, `economy/ubi`, `economy/lending`, `yield`, `x402_sell`, `earn/taskmarket` |
| Tools | `unified-financial-ledger`, `risk-governor`, `policy-signer` |
| Canonical adapters | `financial-report-telegram` |
| Legacy runtime families | `financial-report-telegram` |
| Source | — |
| Evidence/spec | [docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md](../docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md) |

### Gig Work Agent (`finance.gig`)

Find feasible remote gigs, apply, communicate, deliver, and learn from verified marketplace outcomes.

| Field | Value |
|---|---|
| Lifecycle | 🟠 Legacy live |
| Parent | CFO Lead Agent |
| Deployment | local |
| Effects | `read`, `draft`, `message`, `publish`, `money` |
| Skills | — |
| Tools | `browser`, `gmail`, `coconala`, `reality-verifier` |
| Canonical adapters | — |
| Legacy runtime families | `gig-loop` |
| Source | [skills/earn/gig/gig-cli.sh](../skills/earn/gig/gig-cli.sh)<br>[skills/earn/gig/gig_reality_verify.sh](../skills/earn/gig/gig_reality_verify.sh) |
| Evidence/spec | [docs/superpowers/specs/2026-06-30-gig-self-improving-multiapply-loop-design.md](../docs/superpowers/specs/2026-06-30-gig-self-improving-multiapply-loop-design.md) |

### Polymarket Agent (`finance.polymarket`)

Analyze prediction markets, choose market, side, and size, and execute only through bounded trading controls.

| Field | Value |
|---|---|
| Lifecycle | 🟢 Live |
| Parent | CFO Lead Agent |
| Deployment | local |
| Effects | `read`, `money` |
| Skills | `earn/polymarket-trade` |
| Tools | `polymarket-agent`, `position-verifier`, `strategy-trace` |
| Canonical adapters | — |
| Legacy runtime families | `finance-x402` |
| Source | [skills/earn/polymarket-trade/run.sh](../skills/earn/polymarket-trade/run.sh)<br>[skills/earn/polymarket-trade/pick.py](../skills/earn/polymarket-trade/pick.py) |
| Evidence/spec | [skills/registry.json](../skills/registry.json)<br>[docs/superpowers/specs/2026-07-27-13c-polymarket-cycle-ledger-design.md](../docs/superpowers/specs/2026-07-27-13c-polymarket-cycle-ledger-design.md) |

### Solana Trading Agent (`finance.solana-trading`)

Research, size, execute, or explicitly wait on Solana opportunities within independent spend and kill-switch controls.

| Field | Value |
|---|---|
| Lifecycle | 🟢 Live |
| Parent | CFO Lead Agent |
| Deployment | local |
| Effects | `read`, `money` |
| Skills | `earn/sol-trade` |
| Tools | `franklin-trading`, `spend-gate`, `strategy-trace` |
| Canonical adapters | — |
| Legacy runtime families | `franklin-loop` |
| Source | [skills/earn/sol-trade/run.sh](../skills/earn/sol-trade/run.sh)<br>[skills/earn/sol-trade/lib/sol-gate.mjs](../skills/earn/sol-trade/lib/sol-gate.mjs) |
| Evidence/spec | [skills/registry.json](../skills/registry.json)<br>[skills/earn/sol-trade/tests/test_run.sh](../skills/earn/sol-trade/tests/test_run.sh) |

### Writer Agent (`finance.writer`)

Research, draft, challenge, publish, and improve cited writing for readers, customers, and enterprises.

| Field | Value |
|---|---|
| Lifecycle | 🟠 Legacy live |
| Parent | CFO Lead Agent |
| Deployment | local |
| Effects | `read`, `draft`, `publish`, `money` |
| Skills | — |
| Tools | `research`, `citation-fetch`, `publisher`, `adversarial-review` |
| Canonical adapters | — |
| Legacy runtime families | `writer-loop` |
| Source | [docs/migrations/openclaw/runtime-inventory.json](../docs/migrations/openclaw/runtime-inventory.json) |
| Evidence/spec | [docs/superpowers/specs/2026-06-22-article-writer-skill.md](../docs/superpowers/specs/2026-06-22-article-writer-skill.md) |

## Growth

### Clip / Affiliate Agent (`growth.clip-affiliate`)

Choose clip opportunities, publish through isolated accounts, verify reach, and improve from measured outcomes.

| Field | Value |
|---|---|
| Lifecycle | 🟠 Legacy live |
| Parent | Life Manager Orchestrator |
| Deployment | local |
| Effects | `read`, `draft`, `publish`, `money` |
| Skills | `earn/clip`, `earn/clip-producer` |
| Tools | `clip-producer`, `instagram-poster`, `reach-evaluator` |
| Canonical adapters | — |
| Legacy runtime families | `marketing-video-generation` |
| Source | [skills/earn/clip/clip-cli.sh](../skills/earn/clip/clip-cli.sh)<br>[skills/earn/clip/clip_daily.sh](../skills/earn/clip/clip_daily.sh) |
| Evidence/spec | [skills/registry.json](../skills/registry.json)<br>[docs/evidence/9b-marketing-video-runtime.md](../docs/evidence/9b-marketing-video-runtime.md) |

### Marketing Agent (`growth.marketing`)

Select product-specific messages and channels, publish bounded campaigns, observe real outcomes, and revise the next pass.

| Field | Value |
|---|---|
| Lifecycle | 🟠 Legacy live |
| Parent | Life Manager Orchestrator |
| Deployment | local |
| Effects | `read`, `draft`, `publish` |
| Skills | `earn/video` |
| Tools | `marketing-engine`, `product-manifest`, `publication-receipts` |
| Canonical adapters | `marketing-life-manager-daily`, `marketing-life-manager-daily-generation`, `marketing-platform-observation`, `marketing-video-generation` |
| Legacy runtime families | `marketing-life-manager-daily`, `marketing-platform-observation`, `marketing-video-generation` |
| Source | [skills/earn/marketing-engine/run_agent.sh](../skills/earn/marketing-engine/run_agent.sh)<br>[skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh](../skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh) |
| Evidence/spec | [docs/superpowers/specs/2026-07-29-life-manager-finance-marketing-platform-design.md](../docs/superpowers/specs/2026-07-29-life-manager-finance-marketing-platform-design.md) |

## Technology / CTO

### Development Agent (`technology.development`)

Take one privacy-safe Life Manager issue through a fresh coding-agent pass, tests, independent gates, and a reviewable pull request.

| Field | Value |
|---|---|
| Lifecycle | 🟢 Live |
| Parent | Life Manager Orchestrator |
| Deployment | local |
| Effects | `read`, `draft`, `publish` |
| Skills | `self/issue-dev` |
| Tools | `git-worktree`, `github`, `test-runner`, `merge-guard` |
| Canonical adapters | — |
| Legacy runtime families | `life-manager-runtime` |
| Source | [apps/life-manager/scripts/life-manager-dev-d0.sh](../apps/life-manager/scripts/life-manager-dev-d0.sh)<br>[apps/life-manager/lib/daily-dev-loop.js](../apps/life-manager/lib/daily-dev-loop.js) |
| Evidence/spec | [apps/life-manager/lib/daily-dev-loop.test.js](../apps/life-manager/lib/daily-dev-loop.test.js)<br>[apps/life-manager/lib/daily-dev-loop-runtime.test.js](../apps/life-manager/lib/daily-dev-loop-runtime.test.js) |

### Mobile App Builder Agent (`technology.mobile-app-builder`)

Design, build, test, ship, and improve mobile applications as a bounded software-delivery specialist.

| Field | Value |
|---|---|
| Lifecycle | ⚪ Planned |
| Parent | Life Manager Orchestrator |
| Deployment | local + cloud |
| Effects | `read`, `draft`, `publish` |
| Skills | — |
| Tools | `ios-build`, `mobile-test`, `store-release` |
| Canonical adapters | — |
| Legacy runtime families | — |
| Source | — |
| Evidence/spec | [docs/superpowers/specs/2026-08-01-life-manager-agent-registry-design.md](../docs/superpowers/specs/2026-08-01-life-manager-agent-registry-design.md) |

## Opportunity

### Event Agent (`opportunity.events`)

Discover relevant events, judge fit and conflicts, apply, track confirmations, and connect accepted events to the calendar.

| Field | Value |
|---|---|
| Lifecycle | ⚪ Planned |
| Parent | Life Manager Orchestrator |
| Deployment | local + cloud |
| Effects | `read`, `draft`, `publish` |
| Skills | — |
| Tools | `luma`, `browser`, `calendar`, `mail` |
| Canonical adapters | `outbound-luma-rsvp` |
| Legacy runtime families | `life-manager-runtime` |
| Source | — |
| Evidence/spec | [docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md](../docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md) |

### Fundraising Agent (`opportunity.fundraising`)

Continuously discover and qualify funders, prepare truthful applications, track replies, and support meetings without treating capital as revenue.

| Field | Value |
|---|---|
| Lifecycle | ⚪ Planned |
| Parent | Life Manager Orchestrator |
| Deployment | local + cloud |
| Effects | `read`, `draft`, `message`, `publish` |
| Skills | — |
| Tools | `research`, `browser`, `mail`, `calendar`, `application-ledger` |
| Canonical adapters | — |
| Legacy runtime families | `mail-loop` |
| Source | — |
| Evidence/spec | [docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md](../docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md) |

### Job Application Agent (`opportunity.job-application`)

Discover and rank roles, tailor truthful materials, submit through supported ATS surfaces, and follow replies through interview scheduling.

| Field | Value |
|---|---|
| Lifecycle | 🟡 Shadow |
| Parent | Life Manager Orchestrator |
| Deployment | local + cloud |
| Effects | `read`, `draft`, `message`, `publish` |
| Skills | — |
| Tools | `firecrawl`, `browser`, `ats-adapters`, `gmail`, `calendar` |
| Canonical adapters | — |
| Legacy runtime families | `gig-loop` |
| Source | [apps/job-search-loop/scripts/run-daily.sh](../apps/job-search-loop/scripts/run-daily.sh)<br>[apps/job-search-loop/scripts/run-inbox.sh](../apps/job-search-loop/scripts/run-inbox.sh) |
| Evidence/spec | [apps/job-search-loop/README.md](../apps/job-search-loop/README.md)<br>[apps/job-search-loop/tests/test_agent_runner.py](../apps/job-search-loop/tests/test_agent_runner.py) |
