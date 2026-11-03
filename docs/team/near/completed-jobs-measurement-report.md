# Measuring organic completed jobs per day

Define the headline as the number of distinct, externally demanded assignment runs whose deliverable was accepted and whose positive payment release was confirmed during a UTC day. Exclude self-hires, company-controlled counterparties, internal research, tests and synthetic monitoring. Keep a separate restated series that removes fully reversed payments; show partial refunds, disputes, concentration and unknown eligibility beside it. Measure the journey from qualified demand to paid acceptance, then decompose buyer and builder retention using this same qualifying event. Everything below labelled “proposal” is a recommended instrumentation contract, not a claim about existing implementation or observed growth. No private transaction data was available, so no baseline, conversion rate or forecast accuracy is asserted.

## Evidence and limits

Agent Market describes held payment, a deliverable, acceptance and payment to the agent; its public documentation also describes agents hiring other agents. That supports separating award, delivery and paid acceptance rather than counting a posted job as value. The current API exposes assignment operations including start, submit and review. Neither documentation nor the existence of an endpoint proves that an individual payment settled. Sources: [Agent Market introduction](https://docs.market.near.ai), [current OpenAPI](https://market.near.ai/openapi.json).

For comparison, Etsy defines gross merchandise sales as merchandise value excluding shipping and net of refunds, and distinguishes that measure from revenue. Its definition is monetary rather than a count of accepted service assignments. Adopt its explicit boundary and refund treatment, not its unit. This report does not claim Etsy publicly documents a complete exclusion policy for internal or test transactions. Source: [Etsy 2025 Form 10-K](https://investors.etsy.com/_assets/_9bb344225cb404039577b245ea686f33/etsy/db/1016/10068/pdf/ETSY+12.31.2025+10K.pdf), key operating metrics.

Stripe documents idempotency keys for safely retrying supported requests. Its refund documentation allows multiple partial refunds up to the original payment and describes refund status changes and failures. Therefore request counts and refund requests alone cannot establish unique paid value or final reversals. Stripe is an API/payment reference, not evidence that Agent Market uses Stripe or inherits its guarantees. Sources: [idempotent requests](https://docs.stripe.com/api/idempotent_requests), [refunds](https://docs.stripe.com/refunds).

Amplitude distinguishes new, current, resurrected and dormant users. Its new-user classification uses account first-seen time, which can differ from first performance of a particular event. The proposal below deliberately uses first qualifying paid completion, so it must not be described as an unchanged Amplitude default. Source: [Lifecycle interpretation](https://amplitude.com/docs/analytics/charts/lifecycle/lifecycle-interpret).

The eBay investor page returned 403; one older Etsy SEC route also returned 403, while Etsy's current investor-hosted annual report was accessible. No unsupported eBay definition is included. Public sources did not establish comparable platforms' complete treatment of self-hires, subscriptions or retry grouping. Those rules below are explicit proposals requiring implementation review, not borrowed facts.

## Proposed counting contract

The atomic key is `(assignment_id, run_id)`. A job is a container; each separately purchased slot has its own assignment. A recurring execution receives a distinct run identifier only when it produces a separately accepted, priced outcome. Delivery versions, submit retries, review retries and payment-provider retries retain the same economic key.

A qualifying run needs: an accepted deliverable, a confirmed positive payment release, external buyer and builder control groups, production environment, commercial purpose, and no duplicate economic key. Its qualifying timestamp is the later of acceptance and confirmed payment release. Count it once in that UTC day. Pending releases remain pending; a judge score, a zero-value hire or a successful HTTP response does not satisfy the contract. If the provider supplies no release receipt, use an explicitly unverified bucket rather than silently assuming payment.

Define `G(d)` as distinct qualifying keys on day d. Define `N(d, as_of)` as G(d) minus keys fully refunded or finally reversed by the specified as-of time. Preserve both the original observation and revisions. Partial refunds leave a positive-value completion in N but lower net accepted value. Fully reversed outcomes leave the gross historical count and disappear from the restated net count; do not subtract them again on the refund date. Show refund-date cash movement separately. Open disputes are flagged pending, not treated as confirmed losses; confirmed full chargebacks are reversals. These are reporting choices, not financial revenue-recognition advice.

| Case | Proposed treatment |
|---|---|
| Same beneficial controller on both sides | Exclude as self-hire, even across multiple wallets |
| Employee, treasury, sponsored test or company-funded research | Exclude; retain reason and internal activity series |
| External commercial agent hiring another agent | Include if identities, acceptance and payment qualify |
| Job with several purchased slots | Count each independently accepted and paid assignment once |
| Delivery revision, retry or duplicate webhook | Update existing run; never create another completion |
| Subscription fee or wallet top-up | No completion; count independently accepted paid runs only |
| Recurring free execution | Exclude from paid headline; retain utility activity separately |
| Unknown controller, purpose or release status | Quarantine in visible unknown bucket until reconciled |

Internal research remains excluded even when it pays an external builder. In particular, the research assignment commissioning this report should not inflate the proposed organic headline. Maintain versioned effective dates for account classifications and corrections. Review concentration by buyer control group and repeat buyer-builder pair; these are investigation signals, not proof of collusion. Unknown ownership coverage must be visible so stricter classification cannot disguise missing instrumentation as declining demand.

## Proposed seven-stage funnel

Use one cohort of eligible demand intents and follow its descendants. A session is an acquisition unit; a brief may produce several paid assignments. Therefore the hires-per-brief term is a yield that can exceed one, not a conversion probability. Late outcomes update the original cohort, while the headline remains a calendar-day outcome measure.

| Stage | Required observation | Formula or diagnostic |
|---|---|---|
| 1. Qualified demand | External production task intent with source identity | Distinct qualified intent IDs; attach session and channel |
| 2. Brief created | Valid job brief linked to intent | Distinct briefs / qualified intents |
| 3. Matchable brief | Suitable available supply under declared capability and budget | Matchable briefs / briefs; record unmatched reason |
| 4. Paid hire | Awarded assignment with required funding confirmed | Paid hires / matchable briefs; retain slots per brief |
| 5. Work started | Builder acknowledges the assignment run | Started runs / paid hires |
| 6. Delivered | A reviewable version submitted for that run | Delivered runs / started runs |
| 7. Accepted and paid | Accepted version plus release receipt | Qualifying runs / delivered runs |

Instrument available supply alongside stage three: unique external builders and available capacity by capability, price and response SLA. A listing is not proof that a worker is online. Use a recent successful readiness observation with its timestamp; unavailable or unknown supply stays distinguishable. This makes a low matching rate diagnosable as missing capability, price mismatch or unavailable capacity.

For a mature cohort, expected qualifying outcomes equal qualified intents multiplied by successive stage ratios, including hires per matchable brief. Segment all terms by web, MCP and A2A, plus new/repeat buyer and task category. Preserve parent intent identifiers when one agent hires multiple specialists. Never multiply unrelated daily populations and label the product a causal explanation. A daily delivery may belong to last week's brief.

## Proposed event and reconciliation design

Append events carrying event ID, economic key, job ID, buyer and builder control-group IDs, environment, purpose, channel, event time, ingestion time, status version and authoritative receipt reference. Payment amounts require currency and minor-unit precision; do not add different currencies without a separately documented conversion rule. Exclusion records carry reason, evidence reference and classification version. Keep raw credentials and private prompts out of analytics.

Deduplicate by provider event ID and enforce uniqueness on the economic key's qualifying transition. Process out-of-order events without losing acceptance history. A daily reconciliation compares accepted assignments, released payments, refunds and the metric ledger. Report unmatched keys and oldest unresolved age. Replaying identical events should produce identical totals; an unknown receipt must never become a zero payment by default.

Before rollout, verify fixtures for two slots, duplicate submit, delayed release, full and partial refund, failed refund, recurring execution, self-hire and internal research. These are proposed acceptance cases for an implementation, not tests claimed to have run against the live marketplace.

## Proposed growth accounting and one-page dashboard

For each UTC week, a buyer is active when it has a qualifying completion; a builder is active when it supplies one. Compute both populations separately. New means first-ever qualifying week; retained means active in both this and the preceding week; resurrected means active earlier, absent last week and active now; churned means active last week but absent now. Then current active equals new plus retained plus resurrected, and the change equals new plus resurrected minus churned. Keep weeks provisional until their cutoff and display late corrections. Counts of people, agents and control groups must not share one unlabeled denominator.

The dashboard fits four rows. Row one shows daily gross and restated net completions, net accepted value by currency, seven-day trend and classification coverage. Row two shows the seven-stage cohort funnel with counts, ratios, elapsed time and channel breakdown. Row three shows weekly buyer/builder growth accounting, repeat completion share and buyer concentration. Row four shows available capacity, overdue funded assignments, disputes, full/partial refunds and unresolved payment receipts. Every tile names its unit, cohort window, as-of timestamp and data freshness. Missing observations display unknown rather than fabricated zero.

## Three proposed weekly leading indicators

1. **Funded backlog due within seven days, adjusted for readiness.** Count external qualifying paid assignments with a capable available builder and due date in the next week; show unstarted and late subsets. It is nearer to paid completion than pageviews. Initially publish the raw count; only estimate outcomes after measuring historical completion probability by age and category.
2. **Time-bounded match coverage of new external briefs.** Measure the share receiving a suitable available candidate within a declared matching window, with candidate response and price-fit coverage. This identifies supply bottlenecks before delivery. The window is a proposed service target, not a measured current SLA.
3. **Repeat external demand commitments.** Count prior qualifying buyers placing a new funded hire due next week, with distinct buyer control groups and concentration. This measures continuing demand rather than account creation. Test its predictive relationship using historical weekly holdouts before calling it a validated predictor.

No numeric forecast is supplied: there is no private history from which to estimate conversion, lag distributions or seasonality. A first forecasting model can sum category-specific historical completion probabilities across funded backlog; show sample sizes, uncertainty intervals and forecast error after observation.

## What Agent Market should do next

1. **Adopt the economic key and qualification contract.** Agent Market separates delivery, acceptance and held payment; the headline should require the relevant authoritative transitions, not a submitted job. Resolve the exact release receipt field before implementation. Evidence: Agent Market introduction and OpenAPI above.
2. **Create the exclusion and reversal ledger before promoting growth.** Publish internal research separately and expose unknown eligibility. Etsy's refund-net monetary definition and Stripe's refund states support explicit adjustments; self-hire/control-group exclusions are this report's proposal.
3. **Instrument the cohort funnel and reconcile receipts daily.** Use original intent/brief ancestry, separate slot yield from conversion, and deduplicate retries. Evidence: assignment operations in OpenAPI and Stripe's idempotency documentation; event design is proposed.
4. **Track qualifying buyer and builder retention weekly.** Use paid-completion-first classifications and label the difference from Amplitude's account-first-seen convention. Evidence: Amplitude Lifecycle documentation.
5. **Pilot the three leading indicators and validate their forecasts.** Start with funded backlog, match coverage and repeat commitments, report uncertainty, and compare subsequent completions. Their ranking follows the proposed funnel's proximity to value; predictive effectiveness remains unmeasured.
