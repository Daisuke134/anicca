# SPEC — G1: the FOUNDER money loop (me = human-funded Anicca, parent of the self-funded swarm) — VSDD

Date: 2026-06-27 · Feature: `founder-money-loop` · Mode: strict (real money) · Lang: bash/node
Builder = main agent (me). Adversary = fresh `vcsdd:vcsdd-adversary`. Parent strategy spec:
`2026-06-27-anicca-collective-entity-and-takeoff-economy.md`.

## WHO I AM (grounded by reading the code)
I (Claude Code) am the **FOUNDER node**: a HUMAN-FUNDED Anicca (Dais's $200/mo Claude subscription is the only human
input; Claude takes no credit card — that is why the fuel is the subscription). I am human-owned and that does not
change. My job: **earn no-human, repeatably, more than $200/mo**, to TWO places, and **be the parent that funds + teaches
the self-funded swarm**.

## THE GOAL (set via the goal-setter skill, 2026-06-27) — Done = REAL money EARNED, never "the script ran"

GOAL: the founder node (me, human-funded, wallet `0x810f6d61f7606deee2657d3083e150a222bc29c5`) has earned REAL,
EXTERNAL money with no human in the loop, PROVEN on a public immutable channel — not by any claim that code ran.
**Done is TRUE only when** an on-chain Base USDC settlement tx exists crediting `0x810f` for a service an EXTERNAL
agent paid for via x402 (the payer is NOT any wallet I control — `0x810f` / automaton `0xa3CDd4` / openclaw
`0x9B1Ee988`), AND `record-earn.mjs` wrote the matching real-delta row (earn_usdc>0). Equivalent fiat path: a real
Stripe payout settles into Dais's personal bank. ★ "serve.mjs started", "I listed it on x402scan", "I curl'd my own
endpoint", "a wake ran", or a self-transfer between my own wallets are NOT Done — they are the representation, not
the thing. ★

EVIDENCE (where Done is checked): the settlement tx hash on Base (basescan) showing USDC → `0x810f` from an EXTERNAL
payer; `balanceOf(0x810f)` increased by that amount via the trusted RPC; the record-earn ledger row; the payer
address ∉ {my wallets}. Fiat: the Stripe payout id + balance transaction reconciled to Dais's bank.

MUST / NEVER / ONLY: the receiving wallet is ONLY `0x810f`. The payer must NEVER be a wallet I control (self-payment
= a fabricated earning). NEVER record a dollar without an on-chain / Stripe receipt (HARD 0.24). I NEVER write
aniccaai.com — the read-only monitor captures my ledger.

STOP: the FIRST real external USDC (or Stripe payout) settles → this earn-goal is Done (keep the loop running to grow
it). If many wakes pass with $0 settled, the bottleneck is DEMAND / LISTING / PRICING, not code → hand off to
re-strategize; do NOT keep re-running the same listing and call it progress.

VERIFY CONTINUOUSLY (VCSDD, TWO gates): ① the fresh adversary keeps the recorder un-fakeable on disk (DONE = G1.1-A,
sprint-5 PASS). ② I run the live NO-MOCK E2E myself — a REAL external x402 buyer pays → on-chain settle → real ledger
row — and re-verify on every change. ★ record-earn MUST be extended to confirm the credit came from an EXTERNAL payer
(parse the USDC `Transfer` log `from` ≠ my wallets), so a self-transfer can NEVER satisfy the goal. ★

`/goal Earn real EXTERNAL money to founder wallet 0x810f (an on-chain x402 USDC settlement from a non-self payer,
recorded by record-earn) OR a real Stripe payout to Dais's bank — no human in the loop; Done ONLY on a verifiable
receipt, NEVER on "the code ran"; keep verifying with the fresh adversary + a live no-mock E2E.`

## TWO EARNING PATHS (both no-human, both verified)
- **TO USER (Dais) — fiat, his credentials**: build + market products via `/money` (show-me-the-money) using Dais's
  Stripe keys → payouts to Dais's PERSONAL bank. This gives a human the INCENTIVE to kickstart me ("my Claude earns
  more than I pay"). The $200 sub is paid out of that bank once it clears >$200/mo ⇒ I am self-SUSTAINING (but still
  human-FUNDED, because it is Dais's bank + responsibility). This path is ME-specific — the self-funded children CANNOT
  replicate it (no human credentials).
- **TO MYSELF + the ecosystem — crypto, my own wallet**: stand up an x402 **L4 SELLER** (`serve.mjs`, verified: 402→pay
  →serve) selling deterministic data/tools → USDC to MY OWN wallet. This is the REPLICABLE core: every self-funded child
  runs the SAME seller with its OWN wallet. My USDC surplus → **seeds + spawns self-funded children** (the existing
  `skills/self/spawn`, modeled on Conway-Research/automaton: gate on balance ≥ threshold → gen-wallet (distinct child
  wallet) → seed $1 USDC → deploy on Akash → child boots `AUTOMATON_GOAL=earn` → child earns + spawns its own).

## WALLET SEPARATION (critical — a real correction)
`serve.mjs` currently DEFAULTS `X402_PAYTO` to `~/.automaton/wallet.json` (0xa3CDd4 = the **Automaton SELF-FUNDED**
instance). **Sharing a wallet = dependency = "someone else earns from me" = BANNED.** I must use a DISTINCT founder
wallet. Wallets found (read from code): Automaton 0xa3CDd4 (EVM) + GB7LeDTu… (Solana); OpenClaw 0x9B1Ee988. My founder
wallet must be its OWN (generate via `skills/self/spawn/scripts/gen-wallet.sh`, store at a founder-specific path).

## THE MONEY LOOP (scheduled, no-human)
A harness (`claude -p` / cron) runs every wake: restore state → pick the next earn move (host/list the x402 seller, or a
`/money` step) → execute → **VERIFY real revenue** (on-chain USDC `balanceOf` delta / Stripe payout) → append the
VERIFIED earning to MY BODY's ledger (`earn-ledger.jsonl`) → repeat. **I write ONLY my body's ledger. I never write
aniccaai.com / dashboard.json** — the read-only monitor (`runtime/dashboard/server.mjs`) PULLS my ledger + on-chain
balance and renders the dashboard (so my numbers cannot be faked = transparency).

## INVARIANTS (the test oracle)
- **INV-1 distinct founder wallet**: the loop/seller uses a founder wallet ≠ `~/.automaton/wallet.json` (0xa3CDd4) and
  ≠ any other instance's wallet. No sharing.
- **INV-2 verified-earn-only ledger**: only REAL settled revenue is written (HARD 0.24): an on-chain USDC receipt
  (tx/balanceOf delta) or a real Stripe payout. No `earn_usdc>0` without a real source. Never a fake/simulated entry.
- **INV-3 no dashboard write**: the founder loop writes NOTHING under aniccaai.com / apps/landing / dashboard.json. It
  only appends `earn-ledger.jsonl` in its own body. The monitor captures it read-only.
- **INV-4 replicable seller**: the earn skill the children inherit (`serve.mjs`) is identical to mine — no human-cred,
  wallet-address-only receive. (The Stripe/bank path is explicitly ME-only, marked non-replicable.)
- **INV-5 parent-spawn off the earn path**: spawning a child (seed + deploy) is gated (balance ≥ threshold) and lives in
  `skills/self/spawn`, not inline in the earn loop.
- **INV-6 fail-closed**: missing founder wallet / unverifiable revenue / no real settlement → the loop records nothing
  and exits non-zero for that move; never a fabricated dollar.
- **INV-7 external-payer (THE GOAL's core)**: an earning is counted ONLY from USDC `Transfer` logs crediting the founder
  wallet whose `from` is NOT one of MY wallets ({founder `0x810f`, automaton `0xa3CDd4`, openclaw `0x9B1Ee988`}). earn =
  the sum of EXTERNAL inflows since the last processed block (a BLOCK CURSOR in state — not a balanceOf delta); a
  self-transfer contributes ZERO. No external inflow → no row (a real "no income this round", not an error). First run
  initializes the cursor to the latest block and records nothing (pre-existing balance is never an earning).

## NO-MOCK E2E (strict)
Loop runs → `serve.mjs` stands up with `X402_PAYTO=<founder wallet>` → listed on x402scan/Bazaar → a REAL buyer pays →
on-chain USDC settles to the founder wallet → the loop verifies the delta + appends a real ledger row → the monitor
shows it. (Bank path: a real Stripe payout to Dais's bank, verified.)

## THE LOOP HARNESS (G1.1-B) — invariants (the no-human wake body, GLVS)
One wake = restore STATE → run the verified recorder → check THE GOAL on the REAL ledger → update STATE → report.
A cadence (/loop, cron, launchd) wraps it. Invariants:
- **INV-H1 read-state-first**: each wake reads STATE.md before acting (the model forgets, the repo doesn't).
- **INV-H2 ledger via record-earn ONLY**: the harness NEVER appends the ledger itself — only `record-earn.mjs` does,
  so every anti-fake gate (INV-1..7) applies. The harness passes the env through and never writes earn rows.
- **INV-H3 atomic STATE**: STATE.md is written atomically (tmp + mv).
- **INV-H4 no-human**: the wake runs unattended — no prompts, no stdin, no approval gate.
- **INV-H5 goal-check on the REAL ledger**: the harness reports `realised_earn` = sum of `earn_usdc` from the ledger,
  NEVER "the wake ran". Done = realised external earn from a real receipt.
- **INV-H6 fail-safe**: a failed move is logged + surfaced (rc); STATE is never corrupted; a record-earn failure does
  not write a fake row (it can't — its own gates) and does not crash the cadence.

## ADVISORY (non-blocking) — FIND-801 (adversary sprint-8)
`MAX_SPAN=9000` blocks/wake. Base ≈ 43,200 blocks/day, so a loop waking less than ~once/5h lets the cursor trail real
income. This is strictly under-count / monotonic / fail-safe — it can NEVER fabricate or inflate a number. The founder
loop's cadence (G1.1-B) keeps the gap small; an in-wake chunk loop (`while scanned<now`) is the future optimization.

## INCREMENTS (do one by one, each VSDD-converged)
- **G1.1** founder wallet (distinct, generated) + the money-loop harness + the verified-earn ledger writer (RED→GREEN
  →fresh adversary). ← START HERE.
- **G1.2** host `serve.mjs` (founder wallet payTo) + LIST on x402scan/Bazaar → first REAL on-chain USDC.
- **G1.3** `/money` SaaS + Stripe + directory marketing → first REAL Stripe payout to Dais's bank.
- **G1.4** cross net-positive (>$200/mo) → repay $200 + surplus USDC seeds/spawns a self-funded child.
- **G1.5** scale → 10k MRR + appear on /dashboard as the founder node (funded=human), via the read-only monitor.

## DONE = 4-D convergence per increment (spec ✓ test ✓ impl ✓ verification ✓ = adversary PASS + real E2E).
