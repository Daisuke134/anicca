# Proven Writer Money Playbook

Use this reference when the Writer chooses a topic, designs an article, sets a paywall, or learns from a
successful publication. The objective is received writing revenue, not output volume.

## Copy the mechanism, never the expression

The Writer may reproduce a proven creator's audience, offer, cadence, distribution, conversion, and retention
mechanisms. It must not copy prose, titles, images, anecdotes, brand identity, private data, or unverifiable
income claims. Every borrowed mechanism keeps its source URL, observation time, evidence excerpt, and a plain
explanation of why it could transfer to the current reader and market.

A winner is not a template until the Writer can name all of these:

1. Reader job: the concrete progress the reader pays to make.
2. Promise: the specific recurring or one-off outcome sold.
3. Proof: public metrics, customer behavior, or an official payment/program record.
4. Product boundary: what stays free, what is paid, and why.
5. Acquisition: where qualified readers came from.
6. Conversion: the ask, price, preview, timing, and trust signal.
7. Retention: the sustainable cadence or recurring utility.
8. Economics: gross price, platform fees, delivery cost, refunds, and received payout.

If one of these is unknown, record `unknown`; do not fill it with a plausible story.

## Evidence-backed patterns to test

These are hypotheses, not universal rules.

- Observed at `2026-08-28T02:10:59Z`; evidence excerpt: `5-10% of free subscribers convert`; Substack reports a typical free-to-paid conversion range of 5-10% and
  recommends measuring reach and engagement before scaling. Transfer hypothesis: use the range to size the
  required free list, never as proof of our conversion. Source: https://substack.com/going-paid-guide
- Observed at `2026-08-28T02:10:59Z`; evidence excerpt: `15,000 free subscribers, 500 paid`; Lenny Rachitsky reported 15,000 free and 500 paid subscribers, weekly
  publishing, guest posts, an actionable niche, reader price validation, and two large posts producing half of
  growth. Transfer hypothesis: compare one deep evidence asset with the regular cadence. Source:
  https://on.substack.com/p/how-lenny-rachitsky-earned-65000
- Observed at `2026-08-28T02:10:59Z`; evidence excerpt: `Free subscribers: 73,500; Paid subscribers: 6,200`; Noah Smith reported 73,500 free and 6,200 paid subscribers while keeping
  most posts free. Transfer hypothesis: test whether a strong free post grows qualified subscribers before
  increasing the paywalled share. Source: https://on.substack.com/p/grow-series-16-noah-smith
- Observed at `2026-08-28T02:10:59Z`; evidence excerpt: `first 1,000 subscribers in about four and a half months`; Scott Hines reported the first 1,000 subscribers in about 4.5 months with
  a fixed three-times-weekly cadence, images in every post, repeatable formats, and active reader discussion.
  Transfer hypothesis: headline presence is tested independently before cadence. Source:
  https://on.substack.com/p/how-scott-hines-got-his-first-1000
- Observed at `2026-08-28T02:10:59Z`; evidence excerpt: `member reading time` and `external traffic bonus`; Medium reports that eligible earnings use member reading time, engagement,
  external/search/email traffic, member conversion, and read ratio. Transfer hypothesis: optimize promise
  fulfilment and qualified external discovery, then validate with official payout. Source:
  https://help.medium.com/hc/en-us/articles/360036691193-Medium-Partner-Program-earnings-calculation

The Writer tests one transferable mechanism at a time. It never combines five winner tactics in one article
and then claims to know which one worked.

## Daily money loop

1. Read current official platform terms and the latest received-money ledger.
2. Find current successful examples in the same language, niche, reader job, and revenue surface.
3. Capture a structured `WinnerObservation`; reject screenshots or claims without attributable evidence.
4. Ask the model to infer one mechanism and one falsifiable prediction.
5. Select a topic where the Writer has primary evidence or can run an honest experiment.
6. Write natively in each target language. A language version is not a literal translation.
7. Generate one article-specific headline image through the OpenAI Image API with
   `model=gpt-image-2-2026-04-21`. Record `x-request-id`, request model, prompt hash, response hash, file hash,
   dimensions, rights provenance, and alt text.
8. Create a useful free promise and a paid continuation that delivers a named outcome. Never hide the basic
   answer merely to manufacture a paywall.
9. Publish through the installed loop, then read back title, body, headline image, paywall, owner, and URL from
   the provider.
10. Attribute subscriber, purchase, editorial fee, refund, platform fee, and received payout to the exact
    article and experiment.
11. Wake a second time and prove no duplicate article, payment row, or notification.
12. Keep, revise, or reject the mechanism from evidence. Preserve losing experiments so they are not retried.

## Canonical prompts

### Winner researcher

```text
You are researching a writing business, not collecting inspirational stories.
Use current public sources and official platform records. Find creators serving the same reader job, language,
niche, and revenue surface as the proposed article. For each candidate, return the reader job, offer, free/paid
boundary, price, cadence, acquisition path, conversion mechanism, retention mechanism, public proof, source URL,
and every unknown. Separate observed facts from your inference. Do not copy prose or recommend a tactic merely
because the creator is famous. End with the single smallest mechanism we can test without changing another
variable.
```

### Mechanism adapter

```text
Given the winner observations, our own article history, and current platform contract, choose one mechanism to
adapt. Explain the causal hypothesis, why it may transfer to this reader, the strongest reason it may fail, the
one field that changes, the metric window, the stop condition, and the received-money success condition. Keep
the creator's expression and identity out of the output. If the evidence cannot distinguish mechanism from
audience advantage, mark the proposal UNKNOWN and request a smaller observation.
```

### Article builder

```text
Write for the stated reader job using our own evidence, experience, and voice. Lead with the useful result.
Make every important claim traceable to a primary source or an explicitly labelled experiment. Produce native
versions for each requested language rather than translating sentence by sentence. Include concrete steps,
numbers, failure boundaries, and what the reader can do next. Design one honest free promise and one paid
continuation with a named deliverable. Do not imitate source wording, structure blindly, or invent authority.
Provide a concise, article-specific gpt-image-2 headline prompt that communicates the subject without fabricated
metrics, logos, or long rendered text.
```

### Revenue reviewer

```text
Review this package as a skeptical paying reader. Decide whether the free section proves competence, whether the
paid section delivers a result unavailable from the free section, whether the CTA names one action, and whether
the price is supported by current comparable evidence. Check that every revenue claim is gross, net, pending,
available, or received with no category mixing. Return GO, REVISE, or NO-GO with the smallest correction. Views,
likes, drafts, and platform balances are not received revenue.
```

### Learning reviewer

```text
Compare the experiment prediction with official article, subscriber, purchase, fee, refund, and payout readback.
State what changed, what did not, what remains unknown, and whether the tested mechanism should be kept, revised,
or rejected. Do not attribute causality when multiple fields changed. Propose at most one next experiment.
```

## Scale gate

Start with one new source article per day. Increase to three slots only after seven consecutive terminal runs,
provider-native headline/readback on every destination, duplicate effect zero, and at least one received writing
payment. Each slot owns a unique run and topic. If quality, conversion, or expected net revenue per article falls,
return to the last profitable cadence.

The $10k monthly gate uses a complete calendar month and sums only unique net received payouts joined to writing
artifacts. Preserve original currency and convert for reporting with the ECB reference rate on the receipt date
through EUR to USD; use the preceding working day on non-working days. Store an FX receipt with source, rate date,
retrieval time, pair, rate, and values. Missing rates remain `unknown` and do not count. Subscriber projections,
platform balances, pending transfers, and Writer software sales stay separate unless the reporting question
explicitly asks for combined business revenue.
