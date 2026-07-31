# Writer Agent — Revenue, UX, Runtime, and Roadmap SSOT

Last updated: 2026-08-01 JST

This file is the only current source of truth for the Writer Agent's objective,
user experience, revenue model, execution order, and remaining work. Historical
investigation and incident evidence remains in
`docs/loop-engineering/47-writer-loop-quality-and-self-improvement.md`, but that
file no longer defines current priorities or completion.

## 0. Objective

Build one Writer Agent that continuously discovers valuable subjects, writes,
publishes, earns directly from its writing, measures verified payments, repairs
its own interrupted runs, and reports money without ongoing human operation.

The order is:

1. Prove the loop for Dais locally.
2. Reach verified $10,000 monthly revenue with one or more profitable writing
   units.
3. Package the same contract as open source and cloud software.
4. Let anyone start without supplying Google, Gmail, note, Substack, or social
   credentials by using an agent-owned identity, publication surface, and
   device-generated payment identity.
5. Scale proven units and protocol revenue toward $10,000,000 MRR.

The machine cannot guarantee demand or revenue. It must guarantee continuous
measurable attempts, honest receipts, bounded improvement, and automatic
recovery.

## 1. Product boundary

### 1.1 Article-first revenue

The initial product is the writing itself. The Writer does **not** need to turn
every article into a template, API, course, or unrelated digital product.

Before $10,000 monthly revenue, the primary money paths are:

1. A publisher pays an editorial fee for an accepted article.
2. A reader buys one paid article.
3. A reader pays a recurring subscription for continuing writing or an archive.
4. A reader pays to unlock an article on the Writer's self-owned publication.

Derived products are deferred. They may be proposed only after direct writing
revenue has been measured long enough to show that the target cannot be reached
efficiently, or when readers explicitly demand a reusable artifact. They are
not a prerequisite for the first payment.

### 1.2 Economic truth

"The user supplies no customers" is a valid UX requirement: the Agent must find
readers and payers itself. "No payer exists" is not a revenue model. Every
payment has an economic counterparty: a reader, publisher, advertiser,
business, marketplace, protocol, or another agent.

"The user supplies no credentials" means the system generates and safeguards
the required identity on the user's device. Ownership still requires a signing
key, passkey, wallet, or regulated payout identity. A fiat payout through
Stripe, PayPal, or a bank can require account creation and KYC. A no-account OSS
mode therefore cannot depend on note, Substack, Google, Gmail, or Stripe.

## 2. Non-negotiable runtime rules

### 2.1 No passive waiting

If safe work can run now, the Agent runs it now. A missed or incomplete daily
run is kickstarted immediately; it does not wait for the next schedule.

If one platform enforces a future publication window, only that destination is
`PENDING`. All other publication, measurement, research, and reporting work
continues.

Every wait state must record:

- exact blocked target;
- external reason;
- earliest retry time;
- durable resume owner;
- work continuing in parallel;
- Telegram event UUID.

Allowed wait reasons are limited to an externally enforced publication window,
an explicit `Retry-After`, an external editorial/payment response, or a human
legal/KYC action that cannot be delegated. "Wait for the next schedule" is not a
valid terminal state for unfinished work.

### 2.2 Same-run recovery

Failure resumes the same `run_id`, `artifact_id`, content hash, destination, and
publication intent. A new article must not hide a failed article. A replacement
is allowed only after a recorded terminal content rejection and must retain the
failed feedback.

### 2.3 Honest evidence

- A generated draft is not published.
- A URL is not live until public readback passes.
- A checkout view is not a sale.
- A test payment is not revenue.
- A view, like, or impression is not revenue.
- Missing measurement is `unknown`, never zero.
- Revenue requires a processor, platform, publisher, or public-ledger receipt.
- MRR includes active recurring contracts only; editorial fees and paid articles
  remain one-time monthly revenue.

## 3. Revenue streams

### 3.1 Current stream ledger

| Stream | What is sold | Revenue type | Current state | Account/KYC dependency | Verified amount now |
|---|---|---|---|---|---:|
| AppSignal | Accepted technical article | One-time editorial fee | Application submitted; response, publication, and payment pending | Author agreement and publisher payment details | $0 |
| DigitalOcean Write for DOnations | Accepted and published tutorial | One-time editorial fee | Official page is live; actual application intake must be re-read end-to-end before counting | PayPal capable of receiving funds or DO credit; contract/contact details | $0 |
| note | Paid Japanese article | One-time reader payment | Paid publication capability exists; attributed sales receipt absent | note creator and payout account | ¥0 verified |
| Substack | Paid subscription/archive | Recurring reader payment | $8/month tier was enabled; paid subscriber receipt absent | Substack creator plus Stripe | $0 MRR verified |
| Self-owned publication | Paid article or recurring archive | One-time or recurring reader payment | Not implemented | Default OSS mode uses device-generated identity/payment rail; fiat connector optional | $0 |
| Dev.to / Zenn / X | Free distribution | Distribution only by default | Publishing adapters exist or are under repair | Platform account | Excluded from money reward |
| Book | Reconstructed long-form writing | One-time royalty | Deferred until direct daily writing works | Store-specific | $0 |

### 3.2 Publisher fee facts

DigitalOcean's official page currently states $400 for a newly published
tutorial and $100 for an update, while a FAQ on the same page describes a
"typical" $300 payout. Payment occurs after acceptance, editing, and
publication; it is not an automatic $400 monthly subscription. The contract or
acceptance message is the final amount authority. The page also says payment is
through PayPal or DigitalOcean credit.

Source: https://www.digitalocean.com/community/pages/write-for-digitalocean

AppSignal publicly promises a base article rate but does not publish the amount.
Its documented process includes an author agreement, topic approval, editing,
approval, payment, and publication. Until the first acceptance states a rate,
the target contribution is `unknown`, not $400.

Source: https://blog.appsignal.com/write-for-us.html

### 3.3 Reader payment facts

note officially supports paid individual articles, memberships, paid magazines,
and recurring magazines. The first Writer target is the paid individual article;
subscriptions are measured separately.

Source: https://note.com/monetization-guide

Substack publishing is free, but paid subscriptions incur a 10% Substack fee in
addition to Stripe processing and Billing fees. Gross MRR and net MRR must both
be reported.

Source: https://support.substack.com/hc/en-us/articles/360037607131-How-much-does-Substack-cost

## 4. First $10,000 monthly revenue model

The following is a planning allocation, not a forecast. Actual allocation must
be replaced by measured receipts. Planning conversion uses ¥150/$ and displays
gross and net separately.

| Stream | Example monthly target | Required event | Why it exists |
|---|---:|---|---|
| Paid publisher articles | $1,600 | Four accepted $400 articles, or equivalent contracted fees | Fast one-time cash without owning an audience; cannot be assumed until accepted |
| note paid articles | ¥300,000 gross (~$2,000) | 600 purchases at ¥500, or an equivalent price/volume mix | Direct sale of the Japanese article itself |
| Substack subscription | $4,000 gross MRR | 500 active paid readers at $8/month | Recurring English/overseas writing revenue |
| Self-owned paid writing | $2,400 gross monthly | Paid article unlocks or recurring archive on the Writer-owned surface | Removes dependence on third-party creator accounts |
| Total | ~$10,000 gross monthly | Verified receipts only | Initial target mix |

This mix is not a quota imposed on the Agent. Each stream begins at zero. The
Agent reallocates effort only after real conversion, acceptance, churn, fees,
and capacity are measured.

### 4.1 Stage gates

| Stage | Target | Gate |
|---|---|---|
| S-1 | Publishing alive | Three consecutive daily runs publish all currently enabled, non-window-blocked destinations; duplicate zero |
| S0 | First money | One verified non-test payment joined to an article or publisher submission |
| S1 | $400 monthly | $400 verified monthly writing revenue; a single DigitalOcean article may satisfy it, but it is not recurring |
| S2 | $1,000 monthly | Three consecutive revenue-positive weeks with zero manual execution |
| S3 | $10,000 monthly | Three consecutive months at or above $10,000 gross, net positive after compute/platform fees, with every dollar attributed |
| S4 | $10,000 MRR | Active recurring writing subscriptions total $10,000; one-time editorial/article revenue is reported separately |

## 5. Daily Agent loop

```text
WATCH
  Observe reader problems, external claims, publisher calls, prior payments,
  churn, publication failures, and unanswered questions.
    |
DECIDE
  The model selects one reader, one valuable claim, one revenue stream, and at
  most one experimental variable. Code does not classify market judgment with
  keyword rules.
    |
WRITE
  Write the article for the selected reader and direct writing revenue mode.
  Do not manufacture a separate product by default.
    |
VERIFY
  Citation, editorial, reader, identity, PII, policy, and destination checks.
  Finite revisions choose the best valid draft; attempt exhaustion does not
  permanently poison a repaired article.
    |
PUBLISH / SUBMIT
  Publish available destinations immediately. Submit publisher-paid original
  work only to the selected publisher. Platform-specific waits stay isolated.
    |
READBACK
  Persist public URL, platform ID, content hash, account identity, timestamp,
  price/paywall state, and public readback receipt.
    |
MEASURE
  Join impression -> read -> paid boundary -> purchase/subscription/editorial
  acceptance -> payment -> payout. Unknown remains unknown.
    |
LEARN
  Attribute the outcome to the one changed variable. Use held-out evaluation
  and a bounded canary. KEEP or REVERT.
    |
REPORT
  Money first, then funnel, publication state, change, next action, and blocker.
```

Deterministic code owns arithmetic, receipts, idempotency, deduplication,
scheduling, and bookkeeping. The Agent owns topic, reader, article form,
revenue-stream selection, experiment choice, and interpretation.

## 6. User experience

### 6.1 Money screen

The first screen shows:

```text
Verified revenue today
Verified revenue this month
Verified MRR
Available balance
Pending payout

By stream:
  AppSignal editorial fees
  DigitalOcean editorial fees
  note one-time paid articles
  Substack recurring subscriptions
  self-owned one-time article payments
  self-owned recurring subscriptions
```

Each amount opens the exact article, payment/publisher receipt, fee, net amount,
and payout state. Dry-run and test data are visually separated and never added
to revenue.

### 6.2 Live screen

The user sees current action and durable ownership:

```text
14:03 claim selected
14:18 article ready
14:21 note public readback PASS
14:22 Zenn PENDING until external window; owner=zenn-resume-worker
14:23 Substack publishing continues
```

The interface never displays an unqualified `WAITING` state.

### 6.3 Telegram

Hourly messages are event/delta based. Daily and weekly reports are mandatory.

```text
Revenue today: ¥0 / $0
MTD: ¥0 / $0
MRR: $0

AppSignal: pending response, revenue $0
DigitalOcean: intake unverified, revenue $0
note: 0 purchases, ¥0
Substack: 0 paid readers, $0 MRR
Self-owned: not installed, $0

Published: 4 live, 1 platform-window pending
Changed: no revenue variable; publication recovery only
Next: resume pending destination automatically
Human action: none
```

Weekly reports compare each revenue stream, winning/losing topics, conversion,
churn, fees, net revenue, stopped experiments, and next week's single change.

## 7. Zero-account open-source mode

An OSS user must be able to start without Google, Gmail, note, Substack, X, or
Stripe. Therefore these platforms are optional adapters, not the foundation.

On first start, the local runtime generates:

- agent identity and signing key;
- device-bound recovery/passkey policy;
- public author profile;
- self-owned publication endpoint and RSS/feed;
- payment identity capable of receiving without a third-party creator account;
- local encrypted state;
- public receipts and Telegram/Web UI if configured.

The user does not provide an audience or customer list. The Agent discovers
distribution surfaces and potential payers. The user does not approve daily
topics, articles, publication, or experiments.

Creating note, Substack, Gmail, or other third-party accounts autonomously is
not a universal OSS contract: platforms may require email verification,
CAPTCHA, phone verification, terms acceptance, payout identity, or KYC. The
system must not claim credentialless support by silently automating around those
requirements.

Fiat connectors remain optional. A user who wants bank/Stripe/PayPal payouts may
complete the legally required one-time onboarding; the no-account mode continues
to work without them.

## 8. $10,000 to $10,000,000 MRR

One publication is not expected to reach $10M MRR. Scale comes from proven
Writer units and a transparent protocol/service fee.

Example network arithmetic:

```text
100,000 active Writer units
× $1,000 monthly paid-writing GMV per unit
= $100,000,000 monthly network GMV

$100,000,000 GMV
× 10% protocol/service fee
= $10,000,000 MRR to the network operator
```

Alternative:

```text
10,000 units × $10,000 GMV × 10% = $10,000,000 MRR
```

The fee is revenue only when a real payer purchases writing or access. Token
issuance, estimated value, impressions, and internal transfers do not count.

Scale order:

1. Dais's local unit reaches verified first payment.
2. It reaches $400, $1,000, and $10,000 monthly gates.
3. The unit runs for three months with positive net margin and no manual work.
4. The exact runtime is released as OSS zero-account mode.
5. Cloud hosting adds durable operation without changing Agent judgment.
6. Independent users retain their revenue; an explicit network fee funds the
   shared operator.
7. Only profitable units are cloned across niches and languages.
8. Losing units are stopped automatically.

## 9. Remaining work — only active TODO

The order is binding. Work that can be performed now must not wait for natural
schedules or future data.

| # | Phase | Work | Done receipt | Status |
|---:|---|---|---|---|
| 0 | Boundary | Create this dedicated Writer SSOT; point AGENTS and historical spec here | File exists, links resolve, committed and pushed | DONE when this change reaches remote |
| 1 | Availability | Recover today's and yesterday's missed publication immediately | Same-run receipts, all available destinations live, no duplicate | TODO NOW |
| 2 | Availability | Install no-passive-wait catch-up and per-platform pending/resume | Missed schedule and platform-window fixtures plus live recovery | TODO |
| 3 | Quality | Repair attempt exhaustion, contradictory advisory/blocking contract, log path crash, and language mismatch | Repaired content can pass; no permanent poison; focused tests | TODO |
| 4 | Supply | Install X/GitHub/RSS watch intake and maintain topic floor | Three cited, nonduplicate ready claims at all times | TODO |
| 5 | Supply | Reject proposals that do not cite a new claim useful to a reader | Negative and positive fixtures | TODO |
| 6 | Measurement | Add metrics, sales, subscription, editorial, payout, fee, and attribution schema | Status-bearing rows join through `artifact_id` | TODO |
| 7 | Measurement | Mark destinations `revenue_capable`; exclude Dev.to/Zenn/X views from money reward | Reward uses verified money surfaces only | TODO |
| 8 | Reporting | Send hourly deltas, daily money-first report, weekly stream report | Telegram values equal ledger; unknown preserved | TODO |
| 9 | Editorial fee | Continue AppSignal state machine from submitted to response, article, publication, payment | Contracted rate and payment receipt | PARTIAL |
| 10 | Editorial fee | Re-read DigitalOcean application endpoint and submit when intake is actually open | Submission receipt; later contract, publication, payment | TODO |
| 11 | Paid article | Make every selected note article's price/paywall state explicit and measurable | Public paid state plus first attributed purchase | TODO |
| 12 | Subscription | Measure Substack active paid, new, churn, gross MRR, fees, and net MRR | Stripe/Substack receipts join to article | TODO |
| 13 | Self-owned | Implement paid article and recurring archive on an Agent-owned publication | Public unlock/payment/renewal receipts without creator-platform account | TODO |
| 14 | Learning | One revenue variable per experiment; held-out, canary, KEEP/REVERT | Consumed config hash and outcome receipt | TODO |
| 15 | Gate S0 | Earn the first verified dollar from writing | Non-test receipt joined to article/submission | TODO |
| 16 | Gate S1 | Reach $400 monthly writing revenue | Verified monthly ledger | TODO |
| 17 | Gate S2 | Reach $1,000 monthly with three positive weeks and no manual execution | Ledger plus run receipts | TODO |
| 18 | Economics | Make conversion, churn, LTV, compute cost, platform fees, and net margin scorable | No invented values; unknown/insufficient explicit | TODO |
| 19 | Gate S3 | Reach $10,000 monthly for three consecutive months | Gross/net ledger and attribution completeness | TODO |
| 20 | Recurring | Reach $10,000 MRR; keep one-time revenue separate | Active paid contracts and churn receipts | TODO |
| 21 | OSS | Package local zero-account install, generated identity, publication, payment, and UI | Fresh machine reaches public article and real payment without third-party account input | TODO |
| 22 | Cloud | Run the same contract in cloud with durable workers and encrypted tenant isolation | Local/cloud parity suite and real E2E | TODO |
| 23 | Productization | External user receives writing revenue and reports without daily intervention | One external user E2E | TODO |
| 24 | Portfolio | Add only profitable niches/languages; stop losing units | Second unit matches first-unit economics | TODO |
| 25 | Self-extension | Add publisher/collector through sandbox, tests, canary, and promotion | Regression zero and real side-effect receipt | TODO |
| 26 | $100K | Operate enough proven units for $100K monthly net-positive revenue | Three-month receipts | TODO |
| 27 | $1M | Scale cloud/network distribution and retention to $1M MRR | Active recurring receipts | TODO |
| 28 | $10M | Reach $100M network GMV at 10% fee, or another fully receipted equivalent | $10M active recurring receipts; no internal/self payments | TODO |

## 10. Explicitly deferred

These do not block first article revenue:

- automatic template/course/checklist product generation;
- books assembled from article inventory;
- hundreds of platform accounts;
- source-level self-modification in production;
- speculative token revenue;
- dashboards that display estimated money without receipts.

They return only after the preceding stage gate supplies evidence that they are
the smallest next step.

## 11. Completion definition

The Writer is complete only when:

- missed runs recover without being told;
- platform-specific waits never stall the whole loop;
- articles remain useful to external readers rather than describing the loop;
- every reported dollar has a verifiable origin and owner;
- one-time revenue and MRR are never mixed;
- the Agent finds readers and payers without receiving a customer list;
- the OSS default starts without Google/Gmail/note/Substack credentials;
- optional fiat/platform connectors state their account and KYC requirements;
- local and cloud use the same Agent judgment contract;
- users see money, work in progress, failures, recovery, and next action;
- no dry-run, test, or estimated value is represented as earnings.
