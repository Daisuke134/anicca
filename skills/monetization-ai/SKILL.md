---
name: monetization-pipeline
description: Designs and runs safe monetization workflows (lead research, outreach drafts, content-to-offer loops, reporting) using OpenClaw + n8n + communication channels. Use for earning-focused automation while requiring confirmation for money movement.
---

# Monetization Pipeline

## Goal

Turn agent activity into measurable revenue using controlled workflows.

## Core Pipelines

1. **Lead Discovery**
   - Find niche leads (web, communities, directories)
   - Normalize into a structured table (name, channel, need, priority)
2. **Offer Packaging**
   - Generate tailored offer text and pricing options
   - Prepare concise outreach drafts
3. **Outreach Execution**
   - Send only approved messages ({{profile.lateness.stakeholders.channel}}/chat/social)
   - Track replies and follow-ups
4. **Conversion Tracking**
   - Move responses into CRM/Notion/Sheet
   - Weekly conversion report

## Recommended Stack

- OpenClaw for reasoning/orchestration
- n8n for integrations and scheduled jobs
- Telegram for command/control
- Docs/Sheets/Notion for pipeline visibility

## Safety Policy (Critical)

Never execute financial actions without explicit confirmation:
- No transfers
- No exchange orders
- No card/payments
- No irreversible account actions

Before any money-impacting action, require:
1. Clear action summary
2. Amount + destination
3. User confirmation phrase: `CONFIRM MONEY ACTION`

## Daily Command Set

- `run lead scan <niche>`
- `draft 10 outreach messages for <offer>`
- `show conversion report`
- `prepare follow-ups for stale leads`

## Output Format

```markdown
## Revenue Ops Snapshot
- Leads found: <n>
- Qualified: <n>
- Outreach sent: <n>
- Replies: <n>
- Estimated pipeline value: <amount>

## Highest-Leverage Action
- <single next action>
```

## n8n Handoff Spec

For each workflow, define:
- trigger
- inputs schema
- steps
- output schema
- retry policy
- alert channel

Keep all workflows idempotent where possible.

## Guardrails

- No cold spam bursts; rate-limit outreach.
- Respect platform rules and {{profile.lateness.stakeholders.senderType}} constraints.
- Keep an audit trail for every outbound action.
