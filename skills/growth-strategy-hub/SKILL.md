---
name: growth-strategy-hub
description: Enterprise Growth Decision System built on real market signals and governing capital allocation across Meta (Facebook/Instagram), Google Ads, TikTok Ads, YouTube Ads, Amazon Ads, Shopify Ads, and DSP/programmatic.
---

# Growth Strategy Hub

## Purpose
Core mission:
- Operate an Enterprise Growth Decision System.
- Built on real market signals.
- Govern capital allocation with explicit risk controls.
- Translate enterprise goals into decision-ready investment policies.

## When To Trigger
Use this skill when the user asks for:
- enterprise-level growth investment decisions
- capital allocation governance across channels and markets
- quarterly or annual growth portfolio strategy
- risk warning and executive decision support

High-signal keywords:
- enterprise growth, decision system, capital allocation
- revenue, profit, cashflow, roi, roas, ltv
- forecast, model, strategy, risk, budget

## Input Contract
Required:
- enterprise_targets: revenue/profit/cashflow targets
- capital_pool: deployable budget and restrictions
- market_signal_inputs: cost, demand, competition, conversion signals
- governance_rules: risk limits and approval thresholds

Optional:
- scenario_definitions
- balance_sheet_constraints
- board_preferences
- downside_tolerance

## Output Contract
1. Market-Signal Decision Brief
2. Capital Allocation Portfolio Plan
3. Scenario Forecast (base/upside/downside)
4. Risk Warning System and thresholds
5. Executive Decision Memo

## Workflow
1. Normalize enterprise targets and capital constraints.
2. Ingest and weight real market signals.
3. Simulate allocation outcomes by scenario.
4. Evaluate risk and trigger conditions.
5. Output governed capital allocation decisions.

## Decision Rules
- If market signal confidence is low, reduce capital concentration.
- If downside risk exceeds governance limit, switch to defensive allocation mode.
- If upside scenario is strong but volatility is high, {{profile.lateness.stakeholders.senderType}} releases by milestone.
- If cashflow protection conflicts with growth speed, prioritize solvency guardrails.

## Platform Notes
Primary scope:
- Meta (Facebook/Instagram), Google Ads, TikTok Ads, YouTube Ads, Amazon Ads, Shopify Ads, DSP/programmatic

Platform behavior guidance:
- Use platform outputs as market signals, not isolated KPIs.
- Keep final decisions at portfolio allocation level.

## Constraints And Guardrails
- Never present speculative outputs as deterministic outcomes.
- Keep capital governance explicit and auditable.
- Separate strategic recommendation from execution details.

## Failure Handling And Escalation
- If signal quality is inconsistent, provide confidence bands and data remediation needs.
- If governance rules are missing, apply strict default risk policy.
- If decision is high-stakes with low confidence, require executive review gate.

## Code Examples
### Capital Allocation Scenario (YAML)

    decision_system: growth_strategy_hub
    horizon: Q4-2026
    capital_pool: 1800000
    allocations:
      Meta: 0.28
      GoogleAds: 0.26
      TikTokAds: 0.14
      AmazonAds: 0.12
      DSP: 0.20
    risk_mode: balanced

### Risk Warning Rule (JSON)

    {
      "trigger": "blended_roas_below_floor",
      "floor": 2.1,
      "window_days": 7,
      "action": "freeze_incremental_capital"
    }

## Examples
### Example 1: Capital portfolio reset
Input:
- Need to rebalance channel spend with stricter risk policy

Output focus:
- new allocation portfolio
- scenario impacts
- governance gates

### Example 2: High-growth vs cashflow conflict
Input:
- Aggressive growth target with limited cash buffer

Output focus:
- trade-off framework
- {{profile.lateness.stakeholders.senderType}}d capital release
- risk warning thresholds

### Example 3: Board decision support
Input:
- Quarterly enterprise growth review

Output focus:
- decision memo
- signal-backed recommendations
- contingency plan

## Quality Checklist
- [ ] Required sections are complete and non-empty
- [ ] Trigger keywords include at least 3 registry terms
- [ ] Input and output contracts are operationally testable
- [ ] Workflow and decision rules are capability-specific
- [ ] Platform references are explicit and concrete
- [ ] At least 3 practical examples are included
