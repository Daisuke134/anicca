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
  2. **MESSAGE (reach toward them now)** — METI / Breakthrough **Message**: radio travels at light
     speed today. anicca funds/commissions a transmission that declares the cosmic fund exists ("value
     is reserved for you"). The broadcast itself is the first real outbound action to off-earth life.
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
