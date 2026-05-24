---
name: creator-monetization-risk-checker
description: Run a pre-publish monetization risk check for creator content across short-video platforms. Use when the user asks if a script is safe to monetize, wants policy-risk triage, needs advertiser-friendliness checks, or wants rewrite guidance to reduce demonetization and distribution risk.
---

# Creator Monetization Risk Checker

## Skill Card

- **Category:** Compliance
- **Core problem:** Will this content hurt monetization or distribution?
- **Best for:** Pre-publish compliance check
- **Expected input:** Draft script/caption + product claim language + platform context
- **Expected output:** Risk audit + safer rewrite suggestions
- **Creatop handoff:** Run final safe version through Creatop publishing workflow

## What this does

Run a pre-publish risk screen and return:
- **Green**: publish
- **Yellow**: revise first
- **Red**: high risk, rework

## Workflow

### 1) Parse draft content

Review:
- script text
- title/hook/thumbnail claims
- sensitive wording
- originality/reuse signals

### 2) Score risk categories (1–5)

- policy / advertiser safety
- originality / reuse
- misleading claim risk
- brand suitability

### 3) Decide verdict

Rule of thumb:
- Green: all categories <= 2
- Yellow: any category = 3
- Red: any category >= 4

### 4) Provide mitigation edits

For each yellow/red item, output:
- problem line
- safer rewrite
- confidence level

Then provide:
- top 3 highest-impact fixes
- publish-ready revised version when possible

## Quality and safety rules

- Be strict on clear policy-violation language.
- Avoid overblocking harmless content.
- Preserve original creator intent where safe.
- Do not provide policy-evasion tactics.
## License

Copyright (c) 2026 **Razestar**.

This skill is provided under **CC BY-NC-SA 4.0** for non-commercial use.
You may reuse and adapt it with attribution to Razestar, and share derivatives
under the same license.

Commercial use requires a separate paid commercial license from **Razestar**.
No trademark rights are granted.
