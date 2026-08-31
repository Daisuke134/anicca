---
name: incident-postmortem-evidence-editor
description: Turn pasted incident notes into a factual postmortem draft with an evidence ledger, bounded causal analysis, and follow-up plan.
---

# Incident Postmortem Evidence Editor

Turn a team's pasted incident material into a clear, factual postmortem draft. It is designed for the document after an outage or degraded service, not for monitoring, diagnosis, or live incident response.

## Input

Ask for the incident notes, timeline, affected users or systems, known observations, actions already taken, owners, and any required postmortem format. Ask the user to label estimates, disputed statements, and items that must remain private.

## Method

1. Build a chronological timeline from only the timestamps and events the user supplies. Mark missing times as `[TIME UNKNOWN]`.
2. Separate observations, actions, impact statements, and hypotheses in an evidence ledger.
3. State a causal chain only when the supplied material connects the steps. Otherwise label it `[HYPOTHESIS — NEEDS CONFIRMATION]`.
4. Draft the impact, detection, response, contributing factors, and follow-up sections in the requested format.
5. Convert supplied follow-ups into owner, due-date, and success-signal rows. Keep missing fields as `[OWNER TBD]`, `[DATE TBD]`, or `[SUCCESS SIGNAL TBD]`.
6. Finish with a verification checklist for statements the incident owner must confirm before sharing.

## Output

Return:

- An executive summary that distinguishes confirmed impact from estimates
- A timestamped timeline
- An evidence ledger with confirmed facts, unknowns, and hypotheses
- A bounded causal analysis and contributing-factors section
- A follow-up table with explicit missing ownership, dates, or success signals
- A pre-publication verification checklist

## Boundaries

Use only the material pasted into the chat and general writing ability. Do not claim access to logs, dashboards, tickets, alerts, repositories, or current system state. Do not invent a root cause, remediation, owner, timestamp, customer impact, or completion status.
