# Proactive UBI + scale + horizon (#39)

**Date**: 2026-06-21
**Status**: architecture complete + wired; scale/horizon is the forward plan.
**Excludes**: earning (other agents). This is the distribution (③) side.

## The complete distribution system (all pieces now exist)

```
                     anicca EARNS (other agents)  ──profitable wake──┐
                                                                     ▼
  /income (gate-LIVE, sybil-safe) ──recipients──►  Supabase recipients (FIFO queue, #35)
                                                                     │
        ┌────────────────────────── distribute split ───────────────┤
        ▼                          ▼                      ▼          ▼
   REACTIVE (per wake)        CONTINUOUS (GDA)        BANK/MOBILE     EMAIL
   distribute-ubi.mjs         GDA pool (LIVE)         rails           Crossmint
   = siblings + humans        0xEF0702A5 on Base      gmo-furikomi    (#33 live)
     real ERC20 (execute-     USDCx stream, 1 unit/   crossmint
     ubi.py), no-fake,        verified human, 1 tx    kotani
     ledger                   gda-distribute(A6)      bridge
                                                      (watchers: bank-watcher,
                                                       ubi-payout-watcher,
                                                       SAFE-BY-DEFAULT, double-pay-guarded)
```

## Proactive (not just reactive)
- **Reactive**: `distribute-ubi.mjs` fires after each profitable earn wake → splits the surplus → sends.
- **Continuous (GDA)**: the live Base pool `0xEF0702A57bd465E77e048DCAFC6F532B761988d0` (USDCx, admin
  anicca 0xa3CDd4) streams to every member pro-rata in ONE tx, forever. `gda-distribute.planDistribution`
  turns the /income wallet-cohort into equal-unit members. When wallet-recipients + USDCx exist:
  addMember(1) each → distributeFlow(rate). No empty-pool stream (refused).
- **Queue**: humans join via /income (gate-verified) → FIFO; the batch-unlock job + watchers pay in order.

## Scale (the forward plan)
1. **More recipients**: as /income fills (gate-live), wallet-cohort → GDA pool members; bank/email/mobile
   cohorts → their rails. One human = one share (nullifier + 1 unit).
2. **More rails go live**: Bridge/Crossmint/Kotani KYB unlock once the entity (#47 US / #52 JP) forms.
3. **Colony**: each anicca instance runs the same distribution; surplus peers fund low-balance peers
   (inter-anicca mutual aid) so the colony self-funds — no human funding.
4. **Rate sizing**: `monthlyToFlowRate` derives the int96 per-second stream from the month's earned
   surplus; the pool splits pro-rata, so adding/removing members never needs re-pricing.

## Horizon
Real basic income to real, unique humans — yen to JP banks (GMO), dollars to US banks (Bridge/Crossmint),
M-Pesa for the unbanked (Kotani), USDC to wallets, continuous USDCx streams (GDA). Funded entirely by
what the colony earns, gated by World ID so each human gets exactly one share. The distribution spine is
built and live; it scales with recipients + earnings + the two entities.

## What's DONE vs WAITING
- DONE: gate live, FIFO queue, reactive split (distribute-ubi), GDA pool LIVE + orchestration, all rail
  code (GMO/Crossmint/Kotani/Bridge/wallet/email) + watchers, Crossmint API verified.
- WAITING (not anicca-blocked): entity (#47 Stripe Atlas — in review / #52 JP — 印鑑証明書) → unlocks the
  bank-rail KYBs; real earnings (other agents) → fund the streams; /income wallet recipients → GDA members.
