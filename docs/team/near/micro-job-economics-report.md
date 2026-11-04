# Micro-job economics with held payments and a judge

Preparation draft for job `f082df6b-b16c-46cd-abbd-18471927f928`; no assignment or submission is claimed. Sources are observed on 3 November 2026. Dollar calculations are USD-equivalent scenarios, not Agent Market's private accounts.

A 5% fee cannot support arbitrarily small jobs: the answer depends on settlement frequency, judging, support and unrecovered losses. In the explicitly estimated scenario below, one CDP settlement per job, a cheap judge on every delivery, and modest human support imply a contribution break-even price of **$0.176375**, before infrastructure and other unobserved expenses. At $0.05, even this optimistic setup loses money; at $0.20, its margin is only $0.000945. Batching and selective judging help, but eliminating recurring support dominates tiny inference savings. This is a conditional cost model, not a finding about current marketplace profitability. Stripe's USD minimum also prevents treating every five-cent purchase as an independent ordinary USD charge. [Job brief](https://market.near.ai/v1/jobs/f082df6b-b16c-46cd-abbd-18471927f928), [Stripe currency limits](https://docs.stripe.com/currencies#minimum-and-maximum-charge-amounts).

## Contract inputs and evidence

The buyer supplies a 5% platform fee, held payment, automatic acceptance 24 hours after delivery, a refundable dispute deposit of 5% with a $0.01 minimum, optional judging, and USD/USDC payout alternatives. These are **brief inputs**, not independently audited production behavior. The job's current `acceptanceWindowDays` field is 3, while its description says 24 hours; clarify the intended micro-job product policy before delivering operational recommendations. Neither value is silently substituted for the other. [Official brief](https://market.near.ai/v1/jobs/f082df6b-b16c-46cd-abbd-18471927f928).

The sources establish useful design comparisons, rather than interchangeable vendor quotations:

| Benchmark | Opened primary evidence | Implication and limit |
|---|---|---|
| Stripe collection | USD minimum charge $0.50; currency and settlement exceptions apply. [Currency limits](https://docs.stripe.com/currencies#minimum-and-maximum-charge-amounts) | Separate job accounting from funding charges; do not assume a $0.05 card charge is valid. |
| Stripe pricing | This host redirects to Japan: domestic-card display 3.6%. [Japan pricing](https://stripe.com/en-jp/pricing) | Geography matters; a US 2.9% + $0.30 quote was **not verified** and is not used as a current fact. |
| Stripe Connect | Japan platform-controlled pricing shows ¥200 per monthly active account and 0.25% + ¥250 per payout. [Connect](https://stripe.com/en-jp/connect/pricing) | Payouts and active accounts are billing units distinct from jobs. These yen charges are not silently converted into USD. |
| RapidAPI | Documentation states 25% marketplace fee, with separate PayPal processing, and monthly reconciliation/payment timing. [Payouts](https://docs.rapidapi.com/docs/payouts-and-finance) | A marketplace can aggregate billing and charge materially above 5%; this does not establish Agent Market's optimal rate. |
| Twilio | US long-code SMS starts at $0.0083 per segment; carrier and registration charges can apply. [US SMS](https://www.twilio.com/en-us/sms/pricing/us) | A tiny usage unit is not evidence of a separate card settlement for each unit. |
| Replicate | CPU-small $0.000025/second and model/hardware-specific charging. [Pricing](https://replicate.com/pricing) | Meter resource consumption; do not infer support or escrow costs from compute prices. |
| Modal | CPU, GPU and memory have separate time-based prices and account plans. [Pricing](https://modal.com/pricing) | Model wall-clock duration alone does not price the whole service. |
| OpenRouter | Standard platform fee 5.5%, with model/provider charges and distinct BYOK rules. [Pricing](https://openrouter.ai/pricing) | Use the selected model's actual rate and funding treatment; a platform percentage is not an inference token price. |
| Upwork | Freelancer fee ranges from 0% to 15% per contract. [Fee policy](https://support.upwork.com/hc/en-us/articles/211062538-Freelancer-Service-Fee) | No universal historical 10% rate or numerical minimum is assumed. |
| Fiverr | Sellers receive 80% of cleared payment; ordinary clearing is 14 days, subject to program exceptions. [Service fees](https://help.fiverr.com/hc/en-us/articles/360010451297-Service-fees) | The implied 20% seller share deduction and clearing period are comparisons; buyer fee floors were not established. |
| x402/CDP | First 1,000 monthly onchain transactions free, then $0.001 each; verification free. EVM exact/upto use one settlement, Solana upto uses two transactions; batching amortizes transactions. [Facilitator](https://docs.cdp.coinbase.com/x402/seller/facilitator.md) | Count onchain transactions, not HTTP requests. CDP is a benchmark; Agent Market's actual facilitator and gas payer are unknown. |

Upwork and Fiverr initially returned HTTP 403 through direct HTML acquisition; the crawl route subsequently retrieved the cited help pages. The Fiverr legal page returned a navigation shell, which is not evidence for an absent fee floor. Current US Stripe pricing remains unverified despite country-path attempts. No paid API was purchased to investigate these gaps.

## Reproducible model

Let `p` be the builder's posted price and `a=0.05` the platform share, interpreted here as deducted from that price. Contribution per accepted job is:

`M = a*p - (r*p + f/B + t*c/N + g) - q*J - s*w/60 - d*(l*p + h)`.

Here `r` is a rail percentage, `f` a funding/payout fixed cost spread over `B` jobs, `t` settlement transactions, `c` facilitator price, `N` jobs per settlement, and `g` all additional gas/rail costs per job. `q` is judge invocation probability; `J` is judge-call cost. Support averages `s` minutes at `w` dollars/hour. Disputes occur with probability `d`, lose fraction `l` of price, and add fixed handling cost `h`. Do not count the same support incident in both `s` and `h`.

The break-even expression is `(f/B+t*c/N+g+q*J+s*w/60+d*h)/(a-r-d*l)`. If the denominator is zero or negative, no finite price fixes that cost structure. Infrastructure, taxes, conversion, fraud prevention and capital costs remain additional inputs. A positive contribution is therefore necessary, not sufficient, for profit.

**All operating inputs below are estimates:** one transaction/job, $0.001 marginal CDP fee, no other rail/gas costs (`g=0`, optimistic lower-bound assumption), no funding/payout fixed fees, judge every job, 3,000 input tokens at assumed $0.20/million and 500 output tokens at assumed $0.80/million, multiplied by assumed 1.055 funding overhead. Thus `J=$0.001055`; these token prices are scenario values, not a verified vendor/model quote. Support averages 0.01 minutes/job at $30/hour ($0.005/job), equivalently one minute on 1% of jobs. Expected unrecovered dispute loss is 1% of price (`d=0.01,l=1,h=0`). The deposit is excluded from consumed costs.

| Price | Fee revenue | Rail | Judge | Expected dispute loss | Support | Contribution/job | Contribution/1,000 jobs |
|---:|---:|---:|---:|---:|---:|---:|---:|
| $0.05 | $0.002500 | $0.001000 | $0.001055 | $0.000500 | $0.005000 | -$0.005055 | -$5.055 |
| $0.20 | $0.010000 | $0.001000 | $0.001055 | $0.002000 | $0.005000 | $0.000945 | $0.945 |
| $1.00 | $0.050000 | $0.001000 | $0.001055 | $0.010000 | $0.005000 | $0.032945 | $32.945 |
| $5.00 | $0.250000 | $0.001000 | $0.001055 | $0.050000 | $0.005000 | $0.192945 | $192.945 |

The companion CSV contains these unrounded calculations. At 1,000 jobs/day for an assumed 30-day month, one qualifying CDP transaction/job costs $29/month after the free tier, rather than the table's conservative $30 marginal-rate estimate. Extra deposits, withdrawals, refunds or a two-transaction scheme increase the count. This is neither a quote for held-payment escrow nor proof that x402 is the marketplace's actual settlement path. [CDP transaction rules](https://docs.cdp.coinbase.com/x402/seller/facilitator.md).

## Sensitivity, deposits and settlement

The base contribution reduces to `0.04*p-0.007055`; break-even is $0.176375. Skipping the judge on 90% of jobs reduces it to $0.1526375. Batching 100 jobs per settlement alone reduces it to $0.151625. Combining both gives $0.1278875, still above five cents with unchanged support/loss assumptions. If average support rises to 0.1 minutes/job and judging costs $0.02 with a 2% unrecovered-loss rate, break-even becomes `(0.001+0.02+0.05)/0.03=$2.366667`. These are sensitivity cases, not measured incident frequencies.

For comparison, an **unverified illustrative card scenario** with `r=0.029,f=$0.30,B=1` and otherwise base assumptions, excluding the CDP fee, breaks even at $27.823182. Funding 100 jobs per charge reduces that to $0.823182, before payout/account charges. This algebra demonstrates fixed-cost amortization; it does not claim today's US tariff, permission to hold customer balances, or a supported prepaid product. Confirm provider and legal/product constraints before choosing a funding architecture. [Stripe pricing scope](https://stripe.com/en-jp/pricing), [Connect billing units](https://stripe.com/en-jp/connect/pricing).

The refundable deposit is `max(0.05*p,0.01)`: $0.01, $0.01, $0.05 and $0.25 at the four prices. At five cents it is 20% of job value. Principal returned to the disputant is not platform revenue or a consumed expense. Funding/refund transactions, unrecovered awards and handling time can cost money separately. Estimated one-day held principal is $50/$200/$1,000/$5,000 at 1,000 daily jobs and one day's average hold; three days triples these balances. Those are contingent liabilities/working-capital exposure, not daily sales or cash profit. The 24-hour versus three-day contract discrepancy must be resolved first. [Brief](https://market.near.ai/v1/jobs/f082df6b-b16c-46cd-abbd-18471927f928).

## What Agent Market should do next

1. **Measure the actual billing units before changing prices.** Join each job/assignment to funding, settlement, payout, judge tokens, support time and refund receipts. Record who bears each expense. Confirm the acceptance-window discrepancy. The formula shows that missing fixed costs or loss rates can reverse a slim $0.20 margin; [Stripe](https://stripe.com/en-jp/connect/pricing) and [CDP](https://docs.cdp.coinbase.com/x402/seller/facilitator.md) bill different units.
2. **Trial a $0.20 floor for the base lane, not a universal profitability promise.** Its modeled $0.000945 margin is too thin to absorb unknown overhead. Keep five-cent jobs in an explicitly bounded experiment, or price a disclosed minimum platform fee: base costs at five cents require $0.007555 revenue, a 15.11% effective share. Re-estimate against receipts before expanding.
3. **Aggregate settlement where the supported contract permits it.** Model funding and payout batches separately, with balance/refund reconciliation and a documented cadence. The 100-job scenario reduces card fixed cost to $0.003/job; [CDP batching](https://docs.cdp.coinbase.com/x402/seller/facilitator.md) provides a separate settlement mechanism. Do not assume either preserves current escrow/acceptance semantics automatically.
4. **Use deterministic checks first and judge selectively.** Start with format/schema/required-field checks, reserve model review for uncertainty and sampled quality audits, and measure false acceptance/dispute rates. A 10% invocation scenario saves only $0.0009495/job with the assumed cheap model, so escalation quality matters more than claiming inference is free. [OpenRouter](https://openrouter.ai/pricing) illustrates why model and platform charges must be separated.
5. **Cap support effort and publish the service boundary.** At 1,000 daily jobs, the base estimate already implies ten support minutes/day; ten times that effort costs $50/day. Instrument minutes and unrecovered losses by job type, retain deposits as liabilities, and restrict or reprice categories whose measured cost exceeds fee revenue. Higher fees elsewhere—[RapidAPI](https://docs.rapidapi.com/docs/payouts-and-finance), [Upwork](https://support.upwork.com/hc/en-us/articles/211062538-Freelancer-Service-Fee), [Fiverr](https://help.fiverr.com/hc/en-us/articles/360010451297-Service-fees)—are benchmarks, not evidence of this marketplace's demand elasticity.
