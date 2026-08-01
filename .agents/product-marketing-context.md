# Life Manager Product Marketing Context

This document is the semantic source of truth for product and fundraising copy. Exact URLs, dates,
metrics, and evidence live in `startup-context.json` and must not be copied here as independent facts.

## Product Overview

Life Manager is a personal manager for a person's body, mind, and money. It is built to turn goals into
completed real-world actions, then explain the outcome in plain language with evidence in Telegram.
The local self-hosted runtime and the cloud product are two delivery modes for the same Life Manager core.

## Target Audience

The first user is a busy founder or professional whose calendar, applications, health routines, money,
and follow-ups are fragmented across services. The broader audience is anyone who knows what would improve
their life but repeatedly loses momentum between intention and execution.

## Core Pain / Job to Be Done

People do not need another dashboard that only describes their problems. They need a trusted system that
keeps their life moving: find the next worthwhile action, execute it within delegated boundaries, preserve
receipts, and report what actually happened. The job is to reduce the agency gap without hiding uncertainty.

## Physical / Mental / Financial Organs

- Daily Organ coordinates schedules, applications, priorities, and completed actions.
- Physical / Mental Organ supports routines, wellbeing, and continuity of care.
- Financial Organ builds a complete view of assets, liabilities, cash flow, spending, income opportunities,
  and risk-managed investing.

The organs share one user, memory, calendar, evidence ledger, and Telegram experience. A lead agent
coordinates specialist agents; deterministic code handles money arithmetic, state transitions, and receipts.

## Differentiation

Life Manager is positioned as a manager, not a chat assistant. It does not stop at suggestions: where the
user has delegated authority, it performs the action, verifies the result, records the evidence, and reports
it in language a non-technical person can understand. Where action is unsafe or unauthorized, it fails closed
and creates a concrete recovery task instead of inventing success.

## Alternatives / Competition

Alternatives include personal-finance dashboards, budgeting apps, calendar assistants, health trackers,
human executive assistants, robo-advisors, and isolated autonomous-agent demos. Each solves one surface.
Life Manager's approach is to connect those surfaces through one action ledger and one manager experience,
while reusing proven rails and open-source components instead of rebuilding every integration.

## Objections

- **Can it be trusted with sensitive data?** Start locally, request the least privilege, separate read and
  trade permissions, keep an auditable ledger, and never expose credentials in reports or public artifacts.
- **Will it claim actions it did not complete?** No. A successful action requires a receipt or an independently
  verifiable result. Attempts without evidence are reported as incomplete.
- **Will it guarantee wealth or investment returns?** No. It can measure spending, surface opportunities,
  enforce risk limits, and execute an approved strategy, but it cannot guarantee returns.
- **Is this several unrelated products?** No. Connector, Job Hunter, CFO, and investment loops are specialist
  capabilities inside one Life Manager product and one ordered execution plan.

## Customer Language

Customers describe the core pain as: “My life is not moving forward,” “I know what I should do but I do not
do it consistently,” and “I cannot see where my money goes.” External copy should preserve that urgency while
remaining respectful, concrete, and free of exaggerated promises.

## Brand Voice

Direct, calm, accountable, and specific. Lead with the real-world outcome. Prefer “registered for this event
and added it to your calendar” over internal terms such as “runner succeeded.” Every action report should say
what happened, where, when, what evidence exists, and what comes next, with tappable links when available.

## Current Proof and Unknowns

The repository and Telegram entry point are public. Local and cloud components exist, and several specialist
loops have implementation evidence in the repository. User count, revenue, retention, complete personal-bank
coverage, production investing performance, a public demo, and the founder video must be treated as unknown
until the current evidence source verifies each claim. Old Anicca product traction is not Life Manager traction.

## Fundraising Goals

Use accelerators and aligned investors to improve distribution, integrations, security, and the peer network
around Life Manager. Applications must describe the current product truthfully, adapt to each program's actual
thesis, and track submission, confirmation, reply, meeting, and outcome as one evidence-backed funnel.
