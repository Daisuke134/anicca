# 32a — UBI wireframes (actual screens, per path) — Dais 2026-06-18

Screen-by-screen UI for /income + home + each receive path. Each box = one viewport
(mobile-first). Companion to `32-ubi-design`. These are the SCREENS, not flow arrows.

## HOME (/en) — top CTA
```
┌──────────────────────────────────┐
│ Anicca                  EN | 日本語│
│                                  │
│  end the suffering of            │
│  all living beings.              │
│                                  │
│  An AI that earns its own        │
│  compute. The surplus goes       │
│  to people.                      │
│                                  │
│  ┌────────────────────────────┐  │
│  │   Receive basic income  →  │  │  ← PRIMARY
│  └────────────────────────────┘  │
│    Run one yourself (GitHub) →   │  ← secondary (text link)
│                                  │
│  ┌────────────────────────────┐  │
│  │ NET WORTH  $5   ALIVE   5  │  │  ← LedgerWidget (real)
│  │ EARNED/MO  $0   SELF-FND 100%│ │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

## /income — SCREEN A (default: Email selected) — apply ABOVE THE FOLD
```
┌──────────────────────────────────┐
│ Anicca                  EN | 日本語│
│                                  │
│  An AI that earns its own money  │
│  — and gives you a share.        │
│  No human keeps it alive, so it  │
│  doesn't run dry. Join the line. │
│                                  │
│  ┌────────────────────────────┐  │
│  │ Email                      │  │
│  │ [________________________] │  │
│  │                            │  │
│  │ How to receive:            │  │
│  │  (•) Email — simplest      │  │
│  │  ( ) Crypto wallet         │  │
│  │  ( ) Bank account          │  │
│  │  ( ) Card                  │  │
│  │                            │  │
│  │ ┌────────────────────────┐ │  │
│  │ │   Receive  →           │ │  │
│  │ └────────────────────────┘ │  │
│  │ Free. You never pay        │  │
│  │ Anicca anything.           │  │
│  └────────────────────────────┘  │
│  ▼ scroll                        │
│  How it works · Why · Roadmap    │
└──────────────────────────────────┘
```

## /income — SCREEN A variants (the form when each option is picked)
```
WALLET picked → address field appears:        BANK picked → country appears:
┌────────────────────────────┐                ┌────────────────────────────┐
│ How to receive:            │                │ How to receive:            │
│  ( ) Email                 │                │  ( ) Email  ( ) Wallet     │
│  (•) Crypto wallet         │                │  (•) Bank account          │
│  ( ) Bank  ( ) Card        │                │ Country [ Japan        ▾ ] │
│ Your USDC wallet (Base):   │                │ ┌────────────────────────┐ │
│ [0x____________________]   │                │ │  Receive  →            │ │
│ ┌────────────────────────┐ │                │ └────────────────────────┘ │
│ │  Receive  →            │ │                └────────────────────────────┘
│ └────────────────────────┘ │                (Card = same as Bank)
└────────────────────────────┘
```

## /income — SCREEN B (success, inline — page does NOT navigate away)
```
EMAIL / BANK / CARD success:                   WALLET success (instant):
┌──────────────────────────────────┐           ┌──────────────────────────────────┐
│  ✓ You're in line.               │           │  ✓ Sent. It's in your wallet.    │
│  As Anicca earns, people come    │           │                                  │
│  off the waitlist IN ORDER —     │           │  ┌────────────────────────────┐  │
│  a queue, not a lottery. When    │           │  │  View on Basescan  →       │  │
│  your turn comes you'll get an   │           │  └────────────────────────────┘  │
│  email: "From today, money       │           │                                  │
│  reaches you."                   │           │  (check your wallet app too)     │
└──────────────────────────────────┘           └──────────────────────────────────┘
```

## /income — below the fold (same page, scroll)
```
┌──────────────────────────────────┐
│  How it works                    │
│  1. Sign up with email (30s).    │
│  2. Join the line. As Anicca     │
│     earns, your turn comes — in  │
│     order, not a lottery.        │
│  3. "From today, money reaches   │
│     you." It arrives on its own. │
│  No fixed amount — a real share  │
│  of what it earned.              │
│ ──────────────────────────────── │
│  Why this one doesn't run dry    │
│  No subscription, no donor, no   │
│  tax. It earns on-chain and      │
│  gives the surplus. You never    │
│  pay Anicca. It earns. It gives. │
│ ──────────────────────────────── │
│  Roadmap                         │
│  ┌──────┐ ┌──────┐ ┌──────────┐  │
│  │ NOW  │ │ NEXT │ │ HORIZON  │  │
│  │sign  │ │reach │ │every     │  │
│  │up →  │ │non-  │ │living    │  │
│  │your  │ │signup│ │being:    │  │
│  │turn  │ │via   │ │animals→  │  │
│  │→ get │ │phone/│ │aliens    │  │
│  │paid  │ │NPO/  │ │(cosmic   │  │
│  │any   │ │gov't │ │fund,     │  │
│  │country│ │      │ │rail-when-│  │
│  │      │ │      │ │it-exists)│  │
│  └──────┘ └──────┘ └──────────┘  │
└──────────────────────────────────┘
```

## External screens the user lands on
```
Crossmint claim email (EMAIL path)            Basescan (WALLET path)
┌──────────────────────────────┐              ┌──────────────────────────────┐
│ From: Anicca                 │              │ basescan.org                 │
│ Subj: Your turn came         │              │ Transaction   ✓ Success      │
│                              │              │ From 0xa3CDd4…  (Anicca)     │
│ You're off the waitlist.     │              │ To   0x…        (you)        │
│ $X is waiting for you.       │              │ Token  + $X USDC             │
│ ┌──────────────────────────┐ │              └──────────────────────────────┘
│ │  Claim your money  →     │ │
│ └──────────────────────────┘ │              Stripe Connect (BANK/CARD path)
└──────────────────────────────┘              ┌──────────────────────────────┐
                                               │ connect.stripe.com  🔒       │
/income/onboarded (after Stripe)               │ Verify identity  [ … ]       │
┌──────────────────────────────┐              │ Bank account     [ … ]       │
│ ✓ You're set.                │              │ ┌──────────────────────────┐ │
│ You're in line. When your    │              │ │  Submit  →               │ │
│ turn comes, money lands in   │              │ └──────────────────────────┘ │
│ your bank, your currency.    │              └──────────────────────────────┘
│ We'll email you.             │                → returns to /income/onboarded
└──────────────────────────────┘
```

## Creator (Dais) — NOT /income; the install/CLI screen
```
┌──────────────────────────────────┐
│ $ bash install.sh                │
│ ✓ wallet created: 0x9f…          │
│ ? where should earnings go?      │
│   payout address: [0x________]   │
│ ✓ Anicca is running.             │
│   free model $0 · fund the wallet│
│   to unlock frontier + earn more.│
│ → every day: it earns, pays you, │
│   emails you a summary.          │
└──────────────────────────────────┘
```
