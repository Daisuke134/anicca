# Capafy P3 Portfolio Quality Design

**Date:** 2026-08-02  
**Status:** Runtime path verified; portfolio-wide completion gate active
**Parent:** [`2026-08-01-capafy-self-improving-revenue-loop-design.md`](2026-08-01-capafy-self-improving-revenue-loop-design.md)

## Objective

Turn the current 31-listing catalog into a measured portfolio in which every promoted product has a defensible recurring-value mechanism or an explicit one-time purchase model, known unit economics, one experiment owner, and a verified handoff to Marketing. P3 optimizes existing supply before adding another listing.

## Verified starting state

- Inventory: 27 online, 2 under review, 1 draft, 1 review-rejected.
- Revenue: 1 lifetime order, `$9.99` gross, `$8.00` pending, `$0.00` realized, `$0.00` MRR, `$4.78` recorded cost, `-$4.78` contribution.
- Distribution: one verified Reel for seller-owned listing `4866150011`, 121 current views, one organic attributed click after verification-click exclusion, no attributed order.
- All 31 current platform rows expose `sales=null`; product-level paid demand is therefore unknown, not zero.
- Duplicate/overlapping categories exist, including two Academic Humanizers and two Japanese Humanizers. Draft/rejected/review items are not eligible for promotion merely because they exist.

## External evidence and pricing implications

Retrieved 2026-08-02 from official sources:

1. [Apify Actor monetization](https://docs.apify.com/actors/publishing/monetize) supports pay-per-event and pay-per-usage for automation, scraping, and agent projects. [Apify's publisher guidance](https://help.apify.com/en/articles/8684010-make-money-publishing-your-actors-on-apify-store) also documents pay-per-result and flat monthly rental, platform-cost deductions, and a 20% commission. This is the strongest external fit for repeatedly executed automation with measurable output.
2. [Gumroad products](https://gumroad.com/help/article/149-adding-a-product) support both one-time digital products and recurring memberships. [Memberships](https://gumroad.com/help/article/82-membership-products) support tiers, trials, recurring updates, and software access levels. [Current pricing](https://gumroad.com/pricing) is `10% + $0.50` on direct/profile sales and `30%` on marketplace-discovered sales. This fits downloadable skill bundles or recurring update memberships, but its fee floor makes very low one-off prices unattractive.
3. [Lemon Squeezy subscriptions](https://docs.lemonsqueezy.com/help/products/subscriptions) support recurring intervals and API-managed lifecycle. [Usage-based billing](https://docs.lemonsqueezy.com/help/products/usage-based-billing) supports sum, latest, or maximum usage aggregation and bills in arrears. This fits a hosted skill/API only after usage and entitlement metering exist.
4. Current GitHub discovery shows active install/discovery ecosystems such as [`cline/mcp-marketplace`](https://github.com/cline/mcp-marketplace) and monetization implementations such as [`xpack-ai/XPack-MCP-Marketplace`](https://github.com/xpack-ai/XPack-MCP-Marketplace). Discovery alone is not proof of willingness to pay; external placement remains an experiment with attributable links and net revenue measurement.

The portfolio therefore must not force one billing model on every product:

- **Recurring:** repeated monitoring, scheduled refresh, ongoing workflow, collaboration/seat value, or metered execution.
- **Usage-based:** value scales with runs, results, records, pages, or other auditable consumption.
- **One-time:** a static artifact, setup kit, template, or bounded transformation whose buyer receives the full value once.
- **Hybrid:** setup/download fee plus recurring updates or metered execution only when both value components are real.

Price points are experiments, not deterministic constants. The agent proposes them from current platform constraints, next-best alternatives, value metric, cost floor, and observed conversion; deterministic code validates arithmetic and experiment boundaries only.

## Portfolio record

The canonical P3 registry is `~/.openclaw/state/capafy-portfolio.json`. Each product record contains:

```json
{
  "agent_id": "4866150011",
  "observed_status": "online",
  "product_type": "run_online",
  "recurring_mechanism": "repeated_workflow|scheduled_refresh|ongoing_monitoring|collaboration|metered_execution|none",
  "purchase_model": "subscription|usage|one_time|hybrid|undecided",
  "value_metric": "validated natural-language description or null",
  "target_customer": "validated natural-language description or null",
  "next_best_alternative": "validated natural-language description or null",
  "renewal_reason": "validated natural-language description or null",
  "evidence": [{"url": "https://...", "observed_at": "RFC3339", "claim": "...", "confidence": "high|medium|low"}],
  "unit_economics": {"gross_usd": null, "cost_usd": null, "contribution_usd": null},
  "decision": "unaudited|promote|repair|reposition|pause|retire_candidate",
  "decision_reason": "...",
  "experiment": {"experiment_id": "...", "owner": "builder|marketer", "status": "proposed|active|measured|stopped", "success_metric": "...", "stop_condition": "..."}
}
```

Creative/business fields are agent-authored and evidence-cited. The deterministic validator checks schema, public URLs, timestamps, money precision, supported enums, single active experiment ownership, and presence of a concrete stop condition. It never invents the niche, customer, recurring mechanism, price, hook, or decision.

## Autonomous decision policy

1. Refresh platform inventory and the P2 projection immediately; no elapsed-day gate.
2. Audit all 31 records. Unknown evidence remains unknown; `sales=null` cannot become zero.
3. Products with `recurring_mechanism=none` must be explicitly packaged as `one_time` or `hybrid`; they cannot claim MRR.
4. A subscription proposal requires a renewal reason and value metric. Usage pricing requires a measurable unit. A one-time proposal requires a complete bounded deliverable.
5. At most one active experiment may own a product. A portfolio pass may activate only the highest-evidence eligible experiment; it must measure the previous experiment before replacing it.
6. Stop conditions use observable exposure, click, order, contribution, error, or platform state thresholds—not calendar waiting. While one experiment is accumulating exposure, Builder can audit/repair another product without duplicating the active experiment.
7. Draft/rejected items receive one evidence-backed repair/reposition attempt if differentiated. Otherwise they become `retire_candidate` and are excluded from selection and marketing. P3 does not destructively delete a remote listing.
8. Overlapping products compete for one portfolio role. The agent keeps or combines the stronger evidence-backed offer and pauses promotion of the weaker duplicate.
9. A new listing is allowed only when the registry proves a differentiated target/value mechanism and no existing product can run the same experiment.
10. A successful Builder change must be remotely verified and handed to Marketing with the real public listing URL. Marketing publishes only through the P1 owner-verified path.

## User experience

Telegram remains projection-backed and gains a concise portfolio-decision section only after P3 registry parity is implemented:

```text
Capafy portfolio decision — experiment started
Product: Social Post Writer (2672128973)
Model under test: usage — value scales with verified content packs produced
Why now: [evidence-backed agent reason]
Changed: previous state → active experiment exp-...
Evidence: https://...
Success: [observable metric]
Stop: [observable stop condition]
Owner: Marketer
Company projection: 4d97257a0bcb
```

An error report is emitted only with the attempted repair, current unresolved blocker, and automatic next action. The public dashboard will later show portfolio counts and active experiments from the same registry projection; it will not expose private research or local paths.

## P3 completion gate

P3 is complete only when:

- all 31 current listings have validated registry records;
- every promoted product has a purchase model, value metric, renewal/deliverable reason, unit economics, and experiment owner;
- draft/rejected and overlapping products have evidence-backed repair/reposition/pause decisions;
- selection refuses unaudited or paused products;
- one bounded experiment is remotely verified and handed to Marketing with a real URL;
- Telegram and the public company state identify the same terminal experiment truth—active, measured, or stopped—and projection;
- retry and seeded-failure tests prove no duplicate listing, post, or report.
