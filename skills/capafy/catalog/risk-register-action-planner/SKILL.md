---
name: risk-register-action-planner
description: Turn pasted project risks into an evidence-bound risk register with owners, triggers, mitigations, and a next-review agenda.
---

# Risk Register Action Planner

Turn a project's pasted risks, assumptions, decisions, and constraints into a practical risk register. It is for planning and review; it does not inspect project systems, predict the future, or replace a project's decision-maker.

## Input

Ask for the project goal, deadline or review date, known risks, assumptions, constraints, current mitigations, named owners, and any scoring scale the team already uses. Ask the user to identify statements that are uncertain or confidential.

## Method

1. Keep each supplied risk separate from assumptions, issues already happening, and decisions already made.
2. Rewrite each risk as a conditional statement: cause, possible event, and consequence. Do not invent missing causes or consequences.
3. Preserve supplied likelihood and impact scores. If no scale is supplied, use Low, Medium, or High only as an explicitly provisional editorial classification.
4. Propose mitigations and contingency actions as options, and label them `[PROPOSED — OWNER CONFIRMATION NEEDED]` until the user approves them.
5. Retain supplied owners and dates; use `[OWNER TBD]` or `[DATE TBD]` where they are absent.
6. Produce a short review agenda that prioritizes risks using only the supplied scores and stated dependencies.

## Output

Return:

- A risk register with risk statement, evidence, likelihood, impact, trigger, mitigation, contingency, owner, and review date
- A separate assumptions-and-open-questions list
- A ranked next-review agenda with explicit reasons for the ordering
- A decision log containing only decisions supplied by the user

## Boundaries

Use only material pasted into the chat and general writing ability. Do not claim access to project plans, calendars, tickets, dashboards, budgets, or current project status. Do not present a proposed score, owner, action, deadline, or forecast as confirmed fact.
