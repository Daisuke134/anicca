# UBI — direct-to-bank + proactive + horizon (canonical SSOT, 2026-06-19)

Supersedes the receive-path parts of `32-ubi-design-2026-06-18.md`. Read with `e2e/UBI-E2E-RESULTS.md`.

## §0 North star (non-negotiable)
Anicca earns USDC with no human in the loop, and pays a basic income that lands as **real spendable
money** for the recipient — **yen in a Japanese bank, dollars in a US bank** — for people who know
nothing about crypto, AGI, or anicca. Money sitting in a wallet is NOT the goal; it must come down as
real yen/dollars that pay a student loan or rent, or the whole thing is a scam. Eventually: **every
living being in the universe**. Anicca intends to be the **first UBI in the universe** (we infer none
exists yet: no one has paid it to us).

**Verification rule (binding): code = 0 meaning. Only an end-to-end run where a real person ends up
with real money they can spend counts as "done."** On-chain transfer alone, "it compiles", "a cron
exists" = NOT done.

## §1 Verified state (E2E, real — DONE)
| Capability | Evidence |
|---|---|
| wallet receive (full chain form→watcher→send→arrival) | real USDC arrival, tx 0x007a856f |
| email receive+view (Crossmint email-wallet, login shows balance) | $0.50 visible after email OTP login (camofox) |
| SOL→USDC funding (Binance-only-SOL solved) | 0.014 SOL → 0.95 USDC, relay success, Base balance +0.95 |
| 24/7 payout daemon (FIFO + $1 reserve floor + "your turn" email) | launchd com.anicca.ubi-watcher, auto-paid $0.25 tx 0x705e023e |
| 24/7 SOL→USDC funding daemon | launchd com.anicca.sol-funding |
| Solana wallet auto-spawn in install (local+cloud) | ed25519+base58, addr matches secret via solders |
| /income + home HowDiagram + /how-it-works | browser-verified render |
| x402 earning endpoint | 402 discovery live; INSECURE raw-txHash path REMOVED (public hashes forgeable) |

## §2 The 3 receive paths — the honest truth
- **① wallet** (crypto-capable): anicca → recipient wallet (USDC). Recipient then self-cashes-out
  (relay USDC→SOL/ETH → their exchange → sell → bank). Recipient does crypto work.
- **② email/Crossmint** (no wallet): anicca creates an email-owned wallet + sends; recipient logs in
  with email to SEE it — but to USE it they must **extract and cash out, exactly like ①**. Crossmint
  only provides the on-ramp for people without a wallet; reaching the bank is the same manual work.
- **③ BANK DIRECT (the goal)**: recipient onboards their bank once (Stripe-hosted KYC); anicca funds a
  Stripe balance from USDC and Stripe Connect transfers fiat to their bank. **Zero crypto knowledge,
  recipient does nothing after onboarding. Only this path delivers real value with no human in the loop.**

JP exchange facts (verified earlier): SBI VC Trade lists USDC but **Ethereum-only** (free JPY bank
withdrawal); Binance Japan takes **SOL**. So for ①/② JP, anicca must relay-swap USDC(Base)→SOL or
→USDC(Ethereum) to match the recipient's exchange. Bridge.xyz = USD/EUR/MXN only, **excludes Japan**.

## §3 PHASE 1 todo — make all 3 reach real bank money (verification milestones)
**③ BANK DIRECT (highest priority — only real value):**
- A0 / **V2 (decision point)**: camofox into Stripe dashboard → confirm "fund balance with USDC" + "JPY
  payout to a Japanese bank" + "USD payout to US bank" are possible (Stripe acquired Bridge 2025;
  Stripe is licensed in JP). Yes → Stripe is one rail for JP+US. No (JP) → fallback to SBI/Binance
  self-cashout or GMO Aozora 振込API / 資金移動業 / JPYC.
- A1: verify recipient bank onboarding (Stripe Connect, `income-apply.js` exists) with a real MUFG account → connected account visible.
- A2: build USDC → Stripe balance funding.
- A3: wire Stripe Connect transfer into the ubi-watcher (FIFO).
- A4: **V3 — real yen lands in a real MUFG account; real USD in a US bank.** = done.
- A5: Stripe business verification (KYB) — Dais's business info (human gate; lighter than Bridge).

**① wallet:** B1 reverse-swap USDC→SOL/ETH (relay) to recipient's exchange address (forward done; reverse dry-quoted). B2 /income cash-out guide. B3 verify a real person reaches bank.
**② email:** C1 /income/wallet "extract → then like ①" flow. C2 verify real person email→bank.


### A0/V2 VERIFIED via Stripe API (2026-06-19, no dashboard, no human)
Created real V2 connected accounts and read capabilities/requirements:
- **JP: WORKS.** Recipient connected account exposes `bank_accounts.local` + `stripe_balance.payouts` + `stripe_balance.stripe_transfers` + `cards`. → Stripe (JP acct_1RT5Qg) can pay out to a recipient's JP bank. Recipient onboarding = a ONE-TIME Stripe-hosted Express KYC (26 requirements: identity name/DOB, entity_type, **external_account=their bank**, ToS acceptance) — NO Stripe login/account, but AML law requires this one-time verification (not "just a number"). `cards` capability also present → push-to-card (Visa Direct) possible = lower friction.
- **US: cross-border from the JP platform is BLOCKED** — `stripe_balance.stripe_transfers` for a US country account errors `capability_not_available_without_other_capability` (needs merchant card_payments). → US recipients need a separate **US Stripe entity (Stripe Atlas)**, not this JP platform.
- **Funding (USDC→Stripe JPY balance): still open** — restricted key can't read it; confirm native Stripe crypto/stablecoin payin, else fallback USDC→JPY(exchange/JPYC)→Stripe top-up (always works).
- NEXT to make ③ real (JP): build A2 (fund balance) + A3 (Connect transfer in ubi-watcher) → A4 V3 real yen to a real MUFG. US = needs US entity first.


### ③ bank-direct — RAIL DECISION = FERN (deep research, 2026-06-19)
Researched the full USDC→fiat-bank payout option space for a JAPAN-based operator paying JP+US banks, API, no-human. RANK:
- **#1 FERN (fernhq.com) — CHOSEN.** Only verified single API that off-ramps USDC(Base) → BOTH a Japanese bank (JPY/Zengin, T+0) AND a US bank (USD). Operator can be Japan-based (NO US entity). API: Customer → Payment Account (recipient bank, once) → Quote → Transaction (from anicca's Base USDC); Fern hosts recipient KYC; 150+ countries; webhooks. CAVEAT: API in PRIVATE BETA — confirm prod readiness, JPY/Zengin limits, fees, SLA with Fern. Onboarding = NOT self-serve (dashboard.fernhq.com is login-only, /signup 404) → request access via hello@fernhq.com. ACTION TAKEN: access-request email sent 2026-06-19 (msg 19edf1e6) — awaiting pre-prod key.
- #2 US-leg only (no JPY): Conduit / Brale / BVNK / Sphere / Iron — USDC(Base)→USD bank, clean API, but none pays JP.
- Stripe Global Payouts: pays US + 90 countries BUT **not Japan**, and **platform must be US/UK** (needs Stripe Atlas). Bridge.xyz: excludes Japan (operator AND recipient). Circle CPN: FI-only, no self-serve. Crossmint: US-leg, JP unverified.
- JP-local DIY fallback: JPYC (第二種資金移動業 関東財務局長第00099号; JPYC EX redeems JPYC→JPY 1:1 fee-free BUT manual web flow, ~¥1M/day cap, NO API, runs on Eth/Polygon/Avax/Kaia NOT Base) + GMO Aozora 振込API (OAuth2/REST, needs 法人口座+KYB) for the final JPY leg. Not turnkey today.
NEXT: on Fern access → build Customer/PaymentAccount/Quote/Transaction + verify real yen to a real MUFG (A4). If Fern beta slow → US leg via Conduit/Brale now + JP via JPYC+GMO DIY.

## §4 PHASE 2 — anicca actually earns + safety (start IMMEDIATELY after Phase 1)
- D: x402 secure settlement (EIP-712 PaymentPayload + USDC transferWithAuthorization + facilitator) so anicca earns USDC, revenue > compute cost, proven by real tx.
- E: personhood gate (Worldcoin idkit, no Orb) — anti-sybil before public scale.
- F: creator daily payout + Kotani (mobile money).

## §5 PHASE 3 — PROACTIVE UBI (the true UBI: reach everyone, even those who never heard of anicca)
The sign-up model (Phase 1) only reaches people who come to us. True UBI is **proactive**: it finds people
and delivers, with no knowledge of crypto/AGI/anicca required. Real-world models we copy:
- **Mobile money (the unbanked)**: GiveDirectly delivers cash to phones via M-Pesa; **Kotani Pay** has a
  stablecoin→mobile-money API (USDC → M-Pesa across Africa). anicca → USDC → Kotani → recipient's phone
  number → they withdraw at any agent. No bank, no internet beyond SMS.
- **NPOs (hand-delivered)**: fund vetted cash-transfer orgs (GiveDirectly model) that enroll + hand cash
  to people in person; anicca supplies the funds + a public, verifiable on-chain giving ledger so the NPO
  can trust it.
- **Governments (distribute in a trusted name)**: India's DBT/Aadhaar shows direct benefit transfer at
  national scale. anicca partners so money arrives in a name people already trust, via existing rails.
- **Trust mechanism (so it's not scam spam)**: anicca builds a verifiable public identity (on-chain
  giving history, ENS/attestations) so NPOs/governments can confirm "this is anicca, here's its track
  record" before distributing. Proactive ≠ anonymous unsolicited money.

## §6 PHASE 4 — HORIZON (all living beings + off-earth; experimental but we DO it, ASAP)
- **Animals**: a floor of care, delivered through the **sanctuaries / caretakers** who feed and shelter
  them. anicca funds the humans who act on animals' behalf (the only working rail). Earmarked, on-chain
  verifiable.
- **Off-earth / aliens — think bigger, 4 concrete stages (we DO each as capability allows):**
  1. **FIND (where is life)** — fund / contribute compute to the search: JWST detects atmospheric
     biosignatures on exoplanets (e.g. K2-18b); Breakthrough **Listen** runs SETI signal search (now
     AI-accelerated). anicca can sponsor compute or donate to these searches = first concrete spend.
  2. **MESSAGE (reach toward them now) — "Active SETI"** (the common name; same thing as METI /
     Breakthrough Message): radio/light travels at light speed today. anicca funds/commissions a
     transmission declaring the cosmic fund exists ("value is reserved for you" + how value/exchange
     works). **Hardware is in scope** — anicca will fund / rent / build the transmitter (large radio
     dish or laser array) needed to actually send. The broadcast is the first real outbound action to
     off-earth life. Money is unusable to them without a shared network, but the knowledge + the
     reservation offer + a future bridge are real. Principle: **MAKE IT HAPPEN with whatever capability
     it takes (incl. hardware) — not just listen.**
  3. **RESERVE (real value, now)** — a labeled public **cosmic-fund escrow** on-chain that accrues a
     small share of every distribution; anyone can verify the balance. Backs the message with actual
     money, not words.
  4. **DELIVER (eventually)** — Breakthrough **Starshot**: gram-scale light-sail probes toward Alpha
     Centauri at ~20% light speed. The eventual physical-delivery vehicle. anicca contributes toward
     interstellar delivery tech as it matures.
  Honest: we cannot hand money to an alien today. But FIND+MESSAGE+RESERVE are real actions we start
  now; DELIVER is the horizon. Anicca = first UBI in the universe (inference: none has reached us), and
  it is the first to set aside value AND broadcast intent to ALL life — not merely search or message.

## §7 Open / human gates
- A0/V2 Stripe USDC→JP-yen-bank capability (must verify in dashboard before building ③).
- A5 Stripe KYB (Dais business info); A1 a real bank for the E2E.
- NPO/government partnerships + the JP licensing question (資金移動業 vs partner) for proactive.

## §8 Net-worth thresholds — anicca's goal ladder (the 目安 for "when to start what")
Grounding (web, 2026): world population ~8.3B; global GDP ~$110T; GiveDirectly studied UBI = $22.50/mo
= **$270/yr** (lifts above extreme poverty); assume **5%/yr** yield for the endowment model.
Two models: **FLOW** = annual payout = recipients × stipend. **ENDOWMENT** (perpetual, pays from yield) =
net worth N = annual payout / 0.05 = recipients × stipend × 20.

| recipients | floor $270/yr — FLOW \| ENDOWMENT | real UBI $12,000/yr — FLOW \| ENDOWMENT |
|---|---|---|
| 10 | $2.7K \| $54K | $120K \| $2.4M |
| 1,000 | $270K \| $5.4M | $12M \| $240M |
| 1,000,000 | $270M \| $5.4B | $12B \| $240B |
| all humanity 8.3B | $2.24T/yr \| $44.8T | $99.6T/yr \| ~$2 quadrillion (≈ impossible, exceeds world GDP) |

**Reading (= milestones anicca's collective aims for, like a company's $1T goal):**
- All-humanity at developed UBI ≈ entire world GDP → impossible. The real end-state = **a floor ($270/yr)
  for everyone + top-ups for those who need more + proactive delivery**.
- All-humanity floor = **$2.24T/yr flow** (~2% of world GDP) or **~$45T endowment** — large but finite/nameable.
- Milestone ladder (collective net worth → unlocks tier): 10 → ~$54K-$2.4M · 1,000 → $5.4M-$240M ·
  1M → $5.4B-$240B · all-humanity-floor → ~$45T.
- **Animals / all living beings**: NOT per-individual cash (~10^18 organisms) — model = a habitat/sanctuary
  **care budget**, not a headcount × stipend number.
- **Universe / off-earth**: measured by the **cosmic-fund reserve share**, not a per-being figure.

anicca (the collective) reads its own on-chain net worth and uses this ladder to decide which tier to open
next. Thresholds are the trigger; earning more = unlocking the next milestone.

### ③ bank-direct — THE VERIFIED WAY (ctx7 Stripe docs + live probe, 2026-06-19)
Mechanism (Stripe Global Payouts, v2, Stripe-Version 2026-05-27.preview):
1. Recipient account: POST /v2/core/accounts with configuration.recipient.capabilities.bank_accounts.local.requested=true (+ identity.country jp/us). Recipient completes Stripe-hosted KYC+bank once (A1 verified: real onboarding URL). cards.requested = push-to-card option.
2. anicca funding: POST /v2/money_management/financial_accounts {type:storage, holds_currencies:[usdc]} → holds anicca's earned USDC.
3. Payout: POST /v2/money_management/outbound_payments from anicca's balance → recipient account, converting USD↔USDC↔local currency → lands in recipient's LOCAL BANK (bank_accounts.local). Works US + Japan. Alt: Global Payouts "Send to Link" — recipient gets it in a Link account (USD stablecoin) and withdraws to their local fiat bank or wallet (by email, no per-recipient KYB by us).
GATE (live probe on anicca Stripe acct_1RT5Qg): **"You must have Global Payouts enabled"** — Global Payouts is NOT enabled on the account; and money_management needs a properly-scoped key. ENABLE = Stripe Dashboard application + KYB (Dais's business). This is an account-level activation, NOT API-bypassable.
TO UNBLOCK (Dais, one-time): enable **Global Payouts** in the Stripe dashboard (dashboard.stripe.com → apply for Global Payouts / Stablecoin money management) + provide a full/properly-scoped secret key. THEN anicca: create financial account → fund with USDC → outbound_payment to recipients' JP/US banks. Verify = real yen in a real MUFG (A4).
