---
name: anicca-stripe-payout
description: Sends 70% of each earning event to the INSTALLER's bank/wallet via Stripe Connect Express (network onboarded sub-account). Runs as part of revenue-allocator after each cron / heartbeat produces realized_revenue_usd. 20% stays in this-Anicca's own balance (self-compute), 10% goes to the Basic Income pool (10 humans). NEVER pays Dais (creator). Connect Express IS supported in Japan (verified 2026-05-20 firecrawl). HARD RULE #6 — bash + jq + Stripe MCP; no other LLM call.
---

# anicca-stripe-payout — 70 / 20 / 10 split per earning event

Called by `revenue-allocator` (or directly by a skill that records realized
revenue into `ops/roi-ledger.json`) when `realized_revenue_usd > 0`.

## Run

```bash
bash ~/.openclaw/skills/anicca-stripe-payout/run.sh <amount_usd> <source_skill> [<earning_ref>]
```

Returns one summary line on stdout, suitable for the heartbeat / cron
delivery channel (Slack / Email / Telegram per `ANICCA_REPORT_CHANNEL`).

## What it does (deterministic 5 steps)

1. Read `~/.openclaw/.env` for: `STRIPE_SECRET_KEY` (platform live key) +
   `INSTALLER_STRIPE_ACCT` (the Connect Express sub-account ID — set during
   onboard step) + optional `BI_POOL_ADDRESS` (10-human payout pool).
2. Split: 70% → installer, 20% → self, 10% → BI pool.
3. Stripe `transfers.create` to `INSTALLER_STRIPE_ACCT` (70%).
4. Record 20% stay in self-balance (append to `ops/roi-ledger.json` self_share field).
5. Stripe `transfers.create` to `BI_POOL_ADDRESS` (10%) — or queue in
   `ops/bi-pool-pending.jsonl` if the BI pool collector isn't set up yet.

Every transfer logged with `transfer_id`, `amount_usd`, `recipient`, `at`.

## Connect Express onboarding (one-time, agent-driven)

Done once when the user installs Anicca, before any payout fires:

```bash
bash ~/.openclaw/skills/anicca-stripe-payout/onboard.sh
```

`onboard.sh` creates a Connect Express account via `accounts.create`,
generates a `account_links.create` link (type: `onboarding`), prints the
URL — the human follows that link in their {{profile.lateness.stakeholders.channel}} (Stripe handles KYC,
bank linking, etc). After they finish, Stripe webhooks (or the next
heartbeat re-check) fills `INSTALLER_STRIPE_ACCT` in `.env`.

Networked onboarding: if the user already has a Stripe account, this is
**one click** — no repeat KYC (stripe.com/connect/features, 2026-05-20).

## Constitution gate

- The amount split is constitutional (not configurable per-event): 70 / 20 / 10.
- This-Anicca's self-share (20%) accumulates in its OWN Stripe balance, never
  the platform's. If the installer's account doesn't exist (`onboard.sh` not
  run yet), the skill queues all 3 splits in `ops/payout-queue.jsonl` and
  alerts via `ANICCA_REPORT_CHANNEL`. NEVER auto-routes to Dais.
- Dais's bank/wallet is path-protected — even via the Stripe MCP it cannot
  be the recipient of a payout (五戒 不偸盗).

## Country availability

Connect Express IS supported in Japan (verified 2026-05-20 firecrawl
`stripe.com/connect`). Other supported markets: US/UK/EEA/AU/CA/etc.
Stripe Issuing (a different product) is NOT yet supported in Japan
(see task #63) — that's why child self-funding uses Conway USDC, not
Stripe Issuing cards.

## Never

- Never set the recipient as Dais (creator). Five Precepts violation.
- Never run during smoke tests / dry-runs (HARD RULE #9 #11). Use
  `STRIPE_TEST_MODE=1` to dispatch to test-mode keys only.
- Never auto-onboard a NEW Connect account without explicit consent —
  the human must click the onboarding link themselves.
- Never split anything other than 70/20/10. Manifest is constitutional.
